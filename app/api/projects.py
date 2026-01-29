from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.notification import Notification, NotificationType
from app.models.project import Project, ProjectStatus
from app.models.session_model import SessionModel
from app.models.message import Message
from app.models.crs import CRSDocument
from app.models.ai_memory_index import AIMemoryIndex
from app.models.team import Team, TeamMember, TeamRole
from app.models.user import User, UserRole
from app.schemas.project import (
    ProjectApprovalRequest,
    ProjectCreate,
    ProjectDashboardStatsOut,
    ProjectOut,
    ProjectRejectionRequest,
    ProjectUpdate,
    SessionSimpleOut,
    LatestCRSOut,
)

router = APIRouter()


# ==================== Helper Functions ====================


def get_team_or_404(db: Session, team_id: int) -> Team:
    """Get team by ID or raise 404."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    return team


def get_project_or_404(db: Session, project_id: int) -> Project:
    """Get project by ID or raise 404."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return project


def verify_team_membership(
    db: Session,
    team_id: int,
    user_id: int,
    required_roles: Optional[list[TeamRole]] = None,
) -> TeamMember:
    """
    Verify user is an active member of the team.
    Optionally check for specific roles.
    """
    team_member = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.is_active == True,
        )
        .first()
    )

    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this team",
        )

    if required_roles and team_member.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of these roles: {', '.join([r.value for r in required_roles])}",
        )

    return team_member


def check_duplicate_project_name(
    db: Session, name: str, team_id: int, exclude_id: Optional[int] = None
):
    """Check if project name already exists in team."""
    query = db.query(Project).filter(Project.name == name, Project.team_id == team_id)

    if exclude_id:
        query = query.filter(Project.id != exclude_id)

    existing = query.first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A project with this name already exists in this team",
        )


def verify_ba_role(user: User):
    """Verify user is a Business Analyst."""
    if user.role != UserRole.ba:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Business Analysts can perform this action",
        )


def get_user_team_ids(db: Session, user_id: int) -> list[int]:
    """Get all team IDs user is a member of."""
    team_ids = (
        db.query(TeamMember.team_id)
        .filter(TeamMember.user_id == user_id, TeamMember.is_active == True)
        .all()
    )
    return [t[0] for t in team_ids]


# ==================== Endpoints ====================


@router.get("/pending", response_model=list[ProjectOut])
def list_pending_projects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    List all pending project requests for BA review.
    Only Business Analysts can access this endpoint.
    Returns pending projects from all teams the BA is a member of.
    """
    # Verify BA role
    verify_ba_role(current_user)

    # Get all team IDs where BA is a member
    team_ids = get_user_team_ids(db, current_user.id)

    # Query pending projects with eager loading to prevent N+1 queries
    from sqlalchemy.orm import joinedload

    pending_projects = (
        db.query(Project)
        .options(
            joinedload(Project.creator),  # Eager load creator to avoid N+1
            joinedload(Project.team),  # Eager load team to avoid N+1
        )
        .filter(Project.team_id.in_(team_ids), Project.status == "pending")
        .order_by(Project.created_at.desc())
        .all()
    )

    # Enrich with creator information
    result = []
    for project in pending_projects:
        project_dict = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "team_id": project.team_id,
            "created_by": project.created_by,
            "created_by_name": project.creator.full_name if project.creator else None,
            "created_by_email": project.creator.email if project.creator else None,
            "status": project.status,
            "approved_by": project.approved_by,
            "approved_at": project.approved_at,
            "rejection_reason": project.rejection_reason,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        }
        result.append(project_dict)

    return result


@router.post("/", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        status_value = "approved"
        approved_by = current_user.id
        approved_at = func.now()
    else:
        # Client creates pending request
        status_value = "pending"
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
        approved_at=approved_at,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # If client creates pending project, notify BAs in the team
    if status_value == "pending":
        # Get all BA members of the team
        ba_members = (
            db.query(TeamMember)
            .join(User)
            .filter(
                TeamMember.team_id == payload.team_id,
                TeamMember.is_active == True,
                User.role == UserRole.ba,
            )
            .all()
        )

        # Create notification for each BA
        for ba_member in ba_members:
            notification = Notification(
                user_id=ba_member.user_id,
                type=NotificationType.PROJECT_APPROVAL,
                reference_id=project.id,
                title="New Project Request",
                message=f"{current_user.full_name} has requested approval for project '{project.name}'.",
                is_read=False,
            )
            db.add(notification)

        db.commit()

    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
            (Project.status == "approved") | (Project.created_by == current_user.id)
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
    current_user: User = Depends(get_current_user),
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
            detail="Only the project creator or Business Analysts can update this project",
        )

    # Check duplicate name if name is being changed
    if payload.name and payload.name != project.name:
        check_duplicate_project_name(
            db, payload.name, project.team_id, exclude_id=project_id
        )

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
                detail="Only Business Analysts can change project status",
            )
        project.status = payload.status.value

    db.commit()
    db.refresh(project)

    return project


@router.put("/{project_id}/approve", response_model=ProjectOut)
def approve_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a pending project request. Only BAs can approve."""
    # Verify BA role
    verify_ba_role(current_user)

    # Get project
    project = get_project_or_404(db, project_id)

    # Verify BA is team member
    verify_team_membership(db, project.team_id, current_user.id)

    # Verify project is pending
    if project.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve project with status: {project.status}",
        )

    # Approve the project
    project.status = "approved"
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
        is_read=False,
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
    current_user: User = Depends(get_current_user),
):
    """Reject a pending project request. Only BAs can reject."""
    # Verify BA role
    verify_ba_role(current_user)

    # Get project
    project = get_project_or_404(db, project_id)

    # Verify BA is team member
    verify_team_membership(db, project.team_id, current_user.id)

    # Verify project is pending
    if project.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject project with status: {project.status}",
        )

    # Reject the project
    project.status = "rejected"
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
        is_read=False,
    )
    db.add(notification)

    db.commit()
    db.refresh(project)

    return project


@router.get("/{project_id}/dashboard/stats", response_model=ProjectDashboardStatsOut)
def get_project_dashboard_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get aggregated statistics for project dashboard.
    
    Returns:
    - Chat counts by status with total messages
    - CRS counts by status with latest CRS info
    - Document counts from memory
    - Top 5 recent chats
    """
    # Get project and verify access
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)
    
    # Calculate chat statistics
    chat_stats_query = (
        db.query(SessionModel.status, func.count(SessionModel.id))
        .filter(SessionModel.project_id == project_id)
        .group_by(SessionModel.status)
        .all()
    )
    
    chat_by_status = {
        status.value if hasattr(status, 'value') else str(status): count 
        for status, count in chat_stats_query
    }
    chat_total = sum(chat_by_status.values())
    
    # Calculate total messages across all chats
    # Get session IDs for this project, then count messages
    session_ids = (
        db.query(SessionModel.id)
        .filter(SessionModel.project_id == project_id)
        .subquery()
    )
    total_messages = (
        db.query(func.count(Message.id))
        .filter(Message.session_id.in_(session_ids))
        .scalar() or 0
    )
    
    # Calculate CRS statistics
    crs_stats_query = (
        db.query(CRSDocument.status, func.count(CRSDocument.id))
        .filter(CRSDocument.project_id == project_id)
        .group_by(CRSDocument.status)
        .all()
    )
    
    crs_by_status = {
        status.value if hasattr(status, 'value') else str(status): count 
        for status, count in crs_stats_query
    }
    crs_total = sum(crs_by_status.values())
    
    # Get latest CRS
    latest_crs = (
        db.query(CRSDocument)
        .filter(CRSDocument.project_id == project_id)
        .order_by(CRSDocument.created_at.desc())
        .first()
    )
    
    latest_crs_data = None
    if latest_crs:
        latest_crs_data = LatestCRSOut(
            id=latest_crs.id,
            version=latest_crs.version,
            status=latest_crs.status.value if hasattr(latest_crs.status, 'value') else str(latest_crs.status),
            pattern=latest_crs.pattern.value if hasattr(latest_crs.pattern, 'value') else str(latest_crs.pattern),
            created_at=latest_crs.created_at
        )
    
    # Get version count
    version_count = (
        db.query(func.count(func.distinct(CRSDocument.version)))
        .filter(CRSDocument.project_id == project_id)
        .scalar() or 0
    )
    
    # Calculate document statistics from AI memory index
    document_count = (
        db.query(func.count(AIMemoryIndex.id))
        .filter(AIMemoryIndex.project_id == project_id)
        .scalar() or 0
    )
    
    # Get top 5 recent chats with message count
    recent_chats_query = (
        db.query(
            SessionModel.id,
            SessionModel.name,
            SessionModel.status,
            SessionModel.started_at,
            SessionModel.ended_at,
            func.count(Message.id).label('message_count')
        )
        .outerjoin(Message, Message.session_id == SessionModel.id)
        .filter(SessionModel.project_id == project_id)
        .group_by(SessionModel.id)
        .order_by(SessionModel.started_at.desc())
        .limit(5)
        .all()
    )
    
    recent_chats = [
        SessionSimpleOut(
            id=chat.id,
            name=chat.name,
            status=chat.status.value if hasattr(chat.status, 'value') else str(chat.status),
            started_at=chat.started_at,
            ended_at=chat.ended_at,
            message_count=chat.message_count or 0
        )
        for chat in recent_chats_query
    ]
    
    return ProjectDashboardStatsOut(
        chats={
            "total": chat_total,
            "by_status": chat_by_status,
            "total_messages": total_messages
        },
        crs={
            "total": crs_total,
            "by_status": crs_by_status,
            "latest": latest_crs_data,
            "version_count": version_count
        },
        documents={
            "total": document_count
        },
        recent_chats=recent_chats
    )
