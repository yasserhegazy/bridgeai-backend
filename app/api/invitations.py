from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.team import Team, TeamMember, TeamRole
from app.models.invitation import Invitation
from app.models.notification import Notification, NotificationType
from app.schemas.invitation import (
    InvitationCreate,
    InvitationOut,
    InvitationPublicOut,
    InvitationResponse,
    InvitationAcceptResponse
)
from app.utils.invitation import (
    create_invitation,
    send_invitation_email_to_console,
    build_invitation_link
)


router = APIRouter()

# Get limiter from core
from app.core.rate_limit import limiter


@router.get("/{token}", response_model=InvitationPublicOut)
@limiter.limit("10/minute")
def get_invitation(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """
    Get invitation details by token.
    This endpoint is public (no auth required) to show invite details.
    """
    invitation = db.query(Invitation).options(
        joinedload(Invitation.team),
        joinedload(Invitation.inviter)
    ).filter(Invitation.token == token).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check if expired
    if invitation.is_expired():
        invitation.status = 'expired'
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has expired"
        )
    
    # Check if not pending
    if invitation.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This invitation is {invitation.status}"
        )
    
    # Build response with sender and team info
    return InvitationPublicOut(
        email=invitation.email,
        role=invitation.role,
        team_id=invitation.team_id,
        team_name=invitation.team.name if invitation.team else None,
        status=invitation.status,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        invited_by_name=invitation.inviter.full_name if invitation.inviter else None,
        invited_by_email=invitation.inviter.email if invitation.inviter else None
    )


@router.post("/{token}/accept", response_model=InvitationAcceptResponse)
@limiter.limit("5/minute")
def accept_invitation(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept a team invitation.
    User must be authenticated and their email must match the invitation.
    """
    # Get invitation
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Validate invitation
    if not invitation.is_valid():
        if invitation.is_expired():
            invitation.status = 'expired'
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has expired"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This invitation is {invitation.status}"
        )
    
    # Check if user's email matches invitation
    if current_user.email.lower() != invitation.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address"
        )
    
    # Check if user is already a member
    existing_member = db.query(TeamMember).filter(
        TeamMember.team_id == invitation.team_id,
        TeamMember.user_id == current_user.id
    ).first()
    
    if existing_member:
        if existing_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already a member of this team"
            )
        else:
            # Reactivate the member
            existing_member.is_active = True
            existing_member.role = TeamRole[invitation.role]
            invitation.status = 'accepted'
            
            # Notify team owner/admin about accepted invitation
            team_owner = db.query(TeamMember).filter(
                TeamMember.team_id == invitation.team_id,
                TeamMember.role == TeamRole.owner,
                TeamMember.is_active == True
            ).first()
            
            if team_owner:
                notification = Notification(
                    user_id=team_owner.user_id,
                    type=NotificationType.TEAM_INVITATION,
                    reference_id=invitation.team_id,
                    title="Invitation Accepted",
                    message=f"{current_user.full_name} ({current_user.email}) has accepted the invitation to join the team as {invitation.role}.",
                    is_read=False
                )
                db.add(notification)
            
            db.commit()
            
            return InvitationAcceptResponse(
                message="Invitation accepted and membership reactivated",
                team_id=invitation.team_id,
                role=invitation.role
            )
    
    # Create new team membership
    new_member = TeamMember(
        team_id=invitation.team_id,
        user_id=current_user.id,
        role=TeamRole[invitation.role],
        is_active=True
    )
    
    db.add(new_member)
    
    # Update invitation status
    invitation.status = 'accepted'
    
    # Notify team owner/admin about accepted invitation
    team_owner = db.query(TeamMember).filter(
        TeamMember.team_id == invitation.team_id,
        TeamMember.role == TeamRole.owner,
        TeamMember.is_active == True
    ).first()
    
    if team_owner:
        notification = Notification(
            user_id=team_owner.user_id,
            type=NotificationType.TEAM_INVITATION,
            reference_id=invitation.team_id,
            title="New Team Member",
            message=f"{current_user.full_name} ({current_user.email}) has joined the team as {invitation.role}.",
            is_read=False
        )
        db.add(notification)
    
    db.commit()
    
    return InvitationAcceptResponse(
        message="Invitation accepted successfully",
        team_id=invitation.team_id,
        role=invitation.role
    )
