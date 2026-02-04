"""
Project Service Module.
Handles all business logic for project operations including CRUD, approval workflow, and dashboard statistics.
Following architectural rules: stateless, no direct db.session access, uses repositories.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func
from fastapi import HTTPException, status

from app.models.project import Project, ProjectStatus
from app.models.user import User, UserRole
from app.models.team import TeamMember
from app.models.session_model import SessionModel
from app.models.crs import CRSDocument
from app.models.ai_memory_index import AIMemoryIndex
from app.services.permission_service import PermissionService
from app.services import notification_service


class ProjectService:
    """Service for managing project operations."""

    @staticmethod
    def list_pending_projects(db: Session, current_user: User) -> List[Dict[str, Any]]:
        """
        List all pending project requests for BA review.
        Only Business Analysts can access this.
        Returns pending projects from all teams the BA is a member of.
        """
        # Verify BA role
        PermissionService.verify_ba_role(current_user)

        # Get all team IDs where BA is a member
        team_ids = PermissionService.get_user_team_ids(db, current_user.id)

        # Query pending projects with eager loading to prevent N+1 queries
        pending_projects = (
            db.query(Project)
            .options(
                joinedload(Project.creator),
                joinedload(Project.team),
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

    @staticmethod
    def create_project(
        db: Session, name: str, description: str, team_id: int, current_user: User
    ) -> Project:
        """
        Create a new project with role-based approval workflow:
        - BA: Creates project directly (auto-approved)
        - Client: Creates project request (pending BA approval)
        """
        # Validate team exists
        PermissionService.get_team_or_404(db, team_id)

        # Verify user is team member
        PermissionService.verify_team_membership(db, team_id, current_user.id)

        # Check for duplicate name
        PermissionService.check_duplicate_project_name(db, name, team_id)

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
            name=name,
            description=description,
            team_id=team_id,
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
            ProjectService._notify_bas_of_pending_project(db, project, current_user)

        return project

    @staticmethod
    def _notify_bas_of_pending_project(db: Session, project: Project, creator: User):
        """Notify all BAs in the team about a new pending project."""
        # Get all BA members of the team
        ba_members = (
            db.query(TeamMember)
            .join(User)
            .filter(
                TeamMember.team_id == project.team_id,
                TeamMember.is_active == True,
                User.role == UserRole.ba,
            )
            .all()
        )

        # Create notifications for all BAs
        ba_user_ids = [ba_member.user_id for ba_member in ba_members]
        notification_service.notify_project_approval_requested(
            db=db,
            project_id=project.id,
            project_name=project.name,
            requester_name=creator.full_name,
            ba_user_ids=ba_user_ids,
            commit=True,
        )

    @staticmethod
    def get_project(db: Session, project_id: int, current_user: User) -> Project:
        """Get project details. Only team members can view."""
        project = PermissionService.verify_project_access(db, project_id, current_user.id)
        return project

    @staticmethod
    def list_projects(
        db: Session,
        current_user: User,
        team_id: Optional[int] = None,
        status_filter: Optional[ProjectStatus] = None,
    ) -> List[Project]:
        """
        List projects.
        - BA: Can see all projects in their teams
        - Client: Can see approved projects + their own pending requests
        """
        query = db.query(Project)

        # Filter by specific team or all user's teams
        if team_id:
            PermissionService.verify_team_membership(db, team_id, current_user.id)
            query = query.filter(Project.team_id == team_id)
        else:
            team_ids = PermissionService.get_user_team_ids(db, current_user.id)
            query = query.filter(Project.team_id.in_(team_ids))

        # Role-based filtering
        if current_user.role == UserRole.client:
            # Clients see: approved projects OR their own requests
            query = query.filter(
                (Project.status == "approved") | (Project.created_by == current_user.id)
            )

        # Filter by status if specified
        if status_filter:
            query = query.filter(Project.status == status_filter.value)

        return query.all()

    @staticmethod
    def update_project(
        db: Session,
        project_id: int,
        current_user: User,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status_update: Optional[ProjectStatus] = None,
    ) -> Project:
        """
        Update project details (name, description).
        Only the creator or BAs can update.
        """
        # Get project and verify ownership
        project = PermissionService.verify_project_ownership(
            db, project_id, current_user, allow_ba=True
        )

        # Check duplicate name if name is being changed
        if name and name != project.name:
            PermissionService.check_duplicate_project_name(
                db, name, project.team_id, exclude_id=project_id
            )

        # Update fields
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if status_update is not None:
            # Only BAs can change status via this endpoint
            if current_user.role != UserRole.ba:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Business Analysts can change project status",
                )
            project.status = status_update.value

        db.commit()
        db.refresh(project)

        return project

    @staticmethod
    def approve_project(db: Session, project_id: int, current_user: User) -> Project:
        """Approve a pending project request. Only BAs can approve."""
        # Verify BA role
        PermissionService.verify_ba_role(current_user)

        # Get project
        project = PermissionService.get_project_or_404(db, project_id)

        # Verify BA is team member
        PermissionService.verify_team_membership(db, project.team_id, current_user.id)

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
        notification_service.notify_project_approved(
            db=db,
            project_id=project.id,
            project_name=project.name,
            approver_name=current_user.full_name,
            creator_user_id=project.created_by,
            commit=False,
        )

        db.commit()
        db.refresh(project)

        return project

    @staticmethod
    def reject_project(
        db: Session, project_id: int, current_user: User, rejection_reason: str
    ) -> Project:
        """Reject a pending project request. Only BAs can reject."""
        # Verify BA role
        PermissionService.verify_ba_role(current_user)

        # Get project
        project = PermissionService.get_project_or_404(db, project_id)

        # Verify BA is team member
        PermissionService.verify_team_membership(db, project.team_id, current_user.id)

        # Verify project is pending
        if project.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject project with status: {project.status}",
            )

        # Reject the project
        project.status = "rejected"
        project.rejection_reason = rejection_reason
        project.approved_by = None
        project.approved_at = None

        # Create notification for project creator
        notification_service.notify_project_rejected(
            db=db,
            project_id=project.id,
            project_name=project.name,
            rejector_name=current_user.full_name,
            rejection_reason=rejection_reason,
            creator_user_id=project.created_by,
            commit=False,
        )

        db.commit()
        db.refresh(project)

        return project

    @staticmethod
    def get_dashboard_stats(db: Session, project_id: int, current_user: User) -> Dict[str, Any]:
        """
        Get aggregated statistics for project dashboard.
        
        Returns:
        - Chat counts by status with total messages
        - CRS counts by status with latest CRS info
        - Document counts from memory
        - Top 5 recent chats
        """
        # Get project and verify access
        project = PermissionService.verify_project_access(db, project_id, current_user.id)

        # Calculate chat statistics
        chat_stats_query = (
            db.query(SessionModel.status, func.count(SessionModel.id))
            .filter(SessionModel.project_id == project_id)
            .group_by(SessionModel.status)
            .all()
        )

        chat_by_status = {
            status.value if hasattr(status, "value") else str(status): count
            for status, count in chat_stats_query
        }
        chat_total = sum(chat_by_status.values())

        # Calculate total messages across all chats
        total_messages = (
            db.query(func.count(SessionModel.id))
            .filter(SessionModel.project_id == project_id)
            .scalar()
            or 0
        )

        # Calculate CRS statistics
        crs_stats_query = (
            db.query(CRSDocument.status, func.count(CRSDocument.id))
            .filter(CRSDocument.project_id == project_id)
            .group_by(CRSDocument.status)
            .all()
        )

        crs_by_status = {
            status.value if hasattr(status, "value") else str(status): count
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
            latest_crs_data = {
                "id": latest_crs.id,
                "version": latest_crs.version,
                "status": (
                    latest_crs.status.value
                    if hasattr(latest_crs.status, "value")
                    else str(latest_crs.status)
                ),
                "pattern": (
                    latest_crs.pattern.value
                    if hasattr(latest_crs.pattern, "value")
                    else str(latest_crs.pattern)
                ),
                "created_at": latest_crs.created_at,
            }

        # Get version count
        version_count = (
            db.query(func.count(func.distinct(CRSDocument.version)))
            .filter(CRSDocument.project_id == project_id)
            .scalar()
            or 0
        )

        # Calculate document statistics from AI memory index
        document_count = (
            db.query(func.count(AIMemoryIndex.id))
            .filter(AIMemoryIndex.project_id == project_id)
            .scalar()
            or 0
        )

        # Get top 5 recent chats with message count
        recent_chats_query = (
            db.query(
                SessionModel.id,
                SessionModel.name,
                SessionModel.status,
                SessionModel.started_at,
                SessionModel.ended_at,
                func.count(SessionModel.id).label("message_count"),
            )
            .filter(SessionModel.project_id == project_id)
            .group_by(SessionModel.id)
            .order_by(SessionModel.started_at.desc())
            .limit(5)
            .all()
        )

        recent_chats = [
            {
                "id": chat.id,
                "name": chat.name,
                "status": (
                    chat.status.value if hasattr(chat.status, "value") else str(chat.status)
                ),
                "started_at": chat.started_at,
                "ended_at": chat.ended_at,
                "message_count": chat.message_count or 0,
            }
            for chat in recent_chats_query
        ]

        return {
            "chats": {
                "total": chat_total,
                "by_status": chat_by_status,
                "total_messages": total_messages,
            },
            "crs": {
                "total": crs_total,
                "by_status": crs_by_status,
                "latest": latest_crs_data,
                "version_count": version_count,
            },
            "documents": {"total": document_count},
            "recent_chats": recent_chats,
        }
