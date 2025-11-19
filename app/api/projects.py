from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional
from app.db.session import get_db
from app.schemas.project import (
    ProjectCreate, 
    ProjectOut, 
    ProjectUpdate,
    ProjectApprovalRequest, 
    ProjectRejectionRequest
)
from app.models.project import Project, ProjectStatus
from app.models.team import Team, TeamMember, TeamRole
from app.models.user import User, UserRole
from app.models.notification import Notification, NotificationType
from app.core.security import get_current_user


router = APIRouter()


# ==================== Helper Functions ====================

def get_team_or_404(db: Session, team_id: int) -> Team:
    """Get team by ID or raise 404."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    return team


def get_project_or_404(db: Session, project_id: int) -> Project:
    """Get project by ID or raise 404."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


def verify_team_membership(
    db: Session, 
    team_id: int, 
    user_id: int,
    required_roles: Optional[list[TeamRole]] = None
) -> TeamMember:
    """
    Verify user is an active member of the team.
    Optionally check for specific roles.
    """
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
        TeamMember.is_active == True
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this team"
        )
    
    if required_roles and team_member.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of these roles: {', '.join([r.value for r in required_roles])}"
        )
    
    return team_member


def check_duplicate_project_name(db: Session, name: str, team_id: int, exclude_id: Optional[int] = None):
    """Check if project name already exists in team."""
    query = db.query(Project).filter(
        Project.name == name,
        Project.team_id == team_id
    )
    
    if exclude_id:
        query = query.filter(Project.id != exclude_id)
    
    existing = query.first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A project with this name already exists in this team"
        )


def verify_ba_role(user: User):
    """Verify user is a Business Analyst."""
    if user.role != UserRole.ba:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Business Analysts can perform this action"
        )


def get_user_team_ids(db: Session, user_id: int) -> list[int]:
    """Get all team IDs user is a member of."""
    team_ids = db.query(TeamMember.team_id).filter(
        TeamMember.user_id == user_id,
        TeamMember.is_active == True
    ).all()
    return [t[0] for t in team_ids]


# ==================== Endpoints ====================

@router.post("/", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new project with role-based approval workflow:
    - BA: Creates project directly (auto-approved)
    - Client: Creates project request (pending BA approval)
    """
    # Validate team exists
    get_team_or_404(db, payload.team_id)
    
    # Verify user is team member
    verify_team_membership(db, payload.team_id, current_user.id)
    
    # Check for duplicate name
    check_duplicate_project_name(db, payload.name, payload.team_id)
    
    # Determine initial status based on user role
    if current_user.role == UserRole.ba:
        # BA creates approved project
        status_value = 'approved'
        approved_by = current_user.id
        approved_at = func.now()
    else:
        # Client creates pending request
        status_value = 'pending'
        approved_by = None
        approved_at = None
    
    # Create project
    project = Project(
        name=payload.name, 
        description=payload.description, 
        team_id=payload.team_id,
        created_by=current_user.id,
        status=status_value,
        approved_by=approved_by,
        approved_at=approved_at
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get project details. Only team members can view."""
    project = get_project_or_404(db, project_id)
    
    # Verify user is team member
    verify_team_membership(db, project.team_id, current_user.id)
    
    return project


@router.get("/", response_model=list[ProjectOut])
def list_projects(
    team_id: Optional[int] = None,
    status: Optional[ProjectStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List projects. 
    - BA: Can see all projects in their teams
    - Client: Can see approved projects + their own pending requests
    """
    query = db.query(Project)
    
    # Filter by specific team or all user's teams
    if team_id:
        verify_team_membership(db, team_id, current_user.id)
        query = query.filter(Project.team_id == team_id)
    else:
        team_ids = get_user_team_ids(db, current_user.id)
        query = query.filter(Project.team_id.in_(team_ids))
    
    # Role-based filtering
    if current_user.role == UserRole.client:
        # Clients see: approved projects OR their own requests
        query = query.filter(
            (Project.status == 'approved') | 
            (Project.created_by == current_user.id)
        )
    
    # Filter by status if specified
    if status:
        query = query.filter(Project.status == status.value)
    
    return query.all()


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update project details (name, description).
    Only the creator or BAs can update.
    """
    # Get project
    project = get_project_or_404(db, project_id)
    
    # Verify user is team member
    verify_team_membership(db, project.team_id, current_user.id)
    
    # Authorization: Only creator or BA can update
    if current_user.id != project.created_by and current_user.role != UserRole.ba:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project creator or Business Analysts can update this project"
        )
    
    # Check duplicate name if name is being changed
    if payload.name and payload.name != project.name:
        check_duplicate_project_name(db, payload.name, project.team_id, exclude_id=project_id)
    
    # Update fields
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.status is not None:
        # Only BAs can change status via this endpoint
        if current_user.role != UserRole.ba:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Business Analysts can change project status"
            )
        project.status = payload.status.value
    
    db.commit()
    db.refresh(project)
    
    return project


@router.put("/{project_id}/approve", response_model=ProjectOut)
def approve_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a pending project request. Only BAs can approve."""
    # Verify BA role
    verify_ba_role(current_user)
    
    # Get project
    project = get_project_or_404(db, project_id)
    
    # Verify BA is team member
    verify_team_membership(db, project.team_id, current_user.id)
    
    # Verify project is pending
    if project.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve project with status: {project.status}"
        )
    
    # Approve the project
    project.status = 'approved'
    project.approved_by = current_user.id
    project.approved_at = func.now()
    project.rejection_reason = None
    
    # Create notification for project creator
    notification = Notification(
        user_id=project.created_by,
        type=NotificationType.PROJECT_APPROVAL,
        reference_id=project.id,
        title="Project Approved",
        message=f"Your project '{project.name}' has been approved by {current_user.full_name}.",
        is_read=False
    )
    db.add(notification)
    
    db.commit()
    db.refresh(project)
    
    return project


@router.put("/{project_id}/reject", response_model=ProjectOut)
def reject_project(
    project_id: int,
    payload: ProjectRejectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a pending project request. Only BAs can reject."""
    # Verify BA role
    verify_ba_role(current_user)
    
    # Get project
    project = get_project_or_404(db, project_id)
    
    # Verify BA is team member
    verify_team_membership(db, project.team_id, current_user.id)
    
    # Verify project is pending
    if project.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject project with status: {project.status}"
        )
    
    # Reject the project
    project.status = 'rejected'
    project.rejection_reason = payload.rejection_reason
    project.approved_by = None
    project.approved_at = None
    
    # Create notification for project creator
    notification = Notification(
        user_id=project.created_by,
        type=NotificationType.PROJECT_APPROVAL,
        reference_id=project.id,
        title="Project Rejected",
        message=f"Your project '{project.name}' was rejected by {current_user.full_name}. Reason: {payload.rejection_reason}",
        is_read=False
    )
    db.add(notification)
    
    db.commit()
    db.refresh(project)
    
    return project