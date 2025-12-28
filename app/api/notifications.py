from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from app.db.session import get_db
from app.api.auth import get_current_user
from app.models import User, Notification
from app.models.project import Project
from app.models.team import Team
from app.models.invitation import Invitation
from app.models.notification import NotificationType
from app.schemas.notification import NotificationResponse, NotificationList, NotificationMarkRead

router = APIRouter()


def enrich_notification(notification: Notification, db: Session) -> dict:
    """Add metadata to notification based on type"""
    notification_dict = {
        "id": notification.id,
        "user_id": notification.user_id,
        "type": notification.type.lower() if isinstance(notification.type, str) else notification.type.value.lower(),
        "reference_id": notification.reference_id,
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
        "metadata": notification.meta_data or None
    }
    
    if notification.type == NotificationType.PROJECT_APPROVAL:
        # Get project details
        project = db.query(Project).filter(Project.id == notification.reference_id).first()
        if project:
            notification_dict["metadata"] = {
                "project_id": project.id,
                "project_name": project.name,
                "project_status": project.status,
                "project_description": project.description
            }
    
    elif notification.type == NotificationType.TEAM_INVITATION:
        # Check if reference_id is team_id or invitation_id by checking the message
        if "invited you" in notification.message.lower():
            # This is an invitation received notification - reference_id is team_id
            team = db.query(Team).filter(Team.id == notification.reference_id).first()
            # Try to find the pending invitation for this user and team
            user = db.query(User).filter(User.id == notification.user_id).first()
            invitation = None
            if user and team:
                invitation = db.query(Invitation).filter(
                    Invitation.team_id == team.id,
                    Invitation.email == user.email,
                    Invitation.status == 'pending'
                ).first()
            
            if team:
                notification_dict["metadata"] = {
                    "team_id": team.id,
                    "team_name": team.name,
                    "invitation_token": invitation.token if invitation else None,
                    "invitation_role": invitation.role if invitation else None,
                    "action_type": "invitation_received"
                }
        else:
            # This is an acceptance notification - reference_id is team_id
            team = db.query(Team).filter(Team.id == notification.reference_id).first()
            if team:
                notification_dict["metadata"] = {
                    "team_id": team.id,
                    "team_name": team.name,
                    "action_type": "invitation_accepted"
                }
    
    # CRS notifications already have metadata stored, just return it
    
    return notification_dict


@router.get("/", response_model=NotificationList)
def get_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get notifications for the current user with enriched metadata.
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    # Get counts
    total_count = query.count()
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    # Get paginated notifications
    notifications = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()
    
    # Enrich notifications with metadata
    enriched_notifications = [enrich_notification(n, db) for n in notifications]
    
    return NotificationList(
        notifications=enriched_notifications,
        unread_count=unread_count,
        total_count=total_count
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a specific notification as read.
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    
    # Return enriched notification with metadata
    return enrich_notification(notification, db)


@router.patch("/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark all notifications as read for the current user.
    """
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({Notification.is_read: True})
    
    db.commit()
    
    return {"message": "All notifications marked as read"}


@router.post("/{notification_id}/accept-invitation")
def accept_invitation_from_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept a team invitation directly from a notification.
    """
    from app.models.team import TeamMember, TeamRole
    
    # Get the notification
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
        Notification.type == NotificationType.TEAM_INVITATION
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Find the pending invitation
    invitation = db.query(Invitation).filter(
        Invitation.team_id == notification.reference_id,
        Invitation.email == current_user.email,
        Invitation.status == 'pending'
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=400, detail="No pending invitation found")
    
    # Check if already a member
    existing_member = db.query(TeamMember).filter(
        TeamMember.team_id == invitation.team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if existing_member:
        raise HTTPException(status_code=400, detail="You are already a member of this team")
    
    # Create team membership
    new_member = TeamMember(
        team_id=invitation.team_id,
        user_id=current_user.id,
        role=TeamRole[invitation.role],
        is_active=True
    )
    
    db.add(new_member)
    
    # Update invitation status
    invitation.status = 'accepted'
    
    # Mark notification as read
    notification.is_read = True
    
    # Notify team owner
    team_owner = db.query(TeamMember).filter(
        TeamMember.team_id == invitation.team_id,
        TeamMember.role == TeamRole.owner,
        TeamMember.is_active == True
    ).first()
    
    if team_owner and team_owner.user_id != current_user.id:
        owner_notification = Notification(
            user_id=team_owner.user_id,
            type=NotificationType.TEAM_INVITATION,
            reference_id=invitation.team_id,
            title="New Team Member",
            message=f"{current_user.full_name} ({current_user.email}) has joined the team as {invitation.role}.",
            is_read=False
        )
        db.add(owner_notification)
    
    db.commit()
    
    return {
        "message": "Invitation accepted successfully",
        "team_id": invitation.team_id,
        "role": invitation.role
    }


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific notification.
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted successfully"}
