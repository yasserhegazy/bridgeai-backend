"""
CRS Workflow Module.
Handles CRS review queue, status updates, and approval workflows.
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.audit import CRSAuditLog
from app.models.crs import CRSDocument, CRSStatus
from app.models.project import Project
from app.models.team import TeamMember
from app.models.user import User
from app.services.permission_service import PermissionService
from app.services.crs_service import update_crs_status
from app.services.notification_service import (
    notify_crs_approved,
    notify_crs_rejected,
    notify_crs_status_changed,
)
from ..crs.schemas import CRSOut, CRSStatusUpdate


router = APIRouter()


@router.get("/review", response_model=List[CRSOut])
def read_review_queue(
    team_id: Optional[int] = Query(None, description="Filter by specific team (defaults to all teams where user is BA)"),
    status: Optional[str] = Query(None, description="Filter by CRS status (e.g., under_review, approved, rejected)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch CRS documents in the review queue for the Business Analyst.

    This endpoint returns CRS documents from projects in teams where the current user is a BA.
    Excludes draft documents - BAs should only see submitted CRS.
    """
    # Get team IDs based on filter
    if team_id:
        # Verify user is a BA in this specific team
        PermissionService.verify_ba_access(db, team_id, current_user.id)
        team_ids = [team_id]
    else:
        # Get all team IDs where BA is a member
        team_ids = PermissionService.get_user_team_ids(db, current_user.id)

    # Build query to get CRS documents from projects in BA's teams
    query = (
        db.query(CRSDocument)
        .join(Project, CRSDocument.project_id == Project.id)
        .filter(Project.team_id.in_(team_ids))
        # Exclude draft documents - BAs should only see submitted CRS
        .filter(CRSDocument.status != CRSStatus.draft)
    )

    # Apply status filter if provided
    if status:
        try:
            status_enum = CRSStatus(status)
            # Prevent filtering by draft status
            if status_enum == CRSStatus.draft:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Business Analysts cannot access draft CRS documents",
                )
            query = query.filter(CRSDocument.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {[s.value for s in CRSStatus]}",
            )

    # Order by most recent first
    crs_documents = query.order_by(CRSDocument.created_at.desc()).all()

    # Convert to response format
    result = []
    for crs in crs_documents:
        try:
            summary_points = (
                json.loads(crs.summary_points) if crs.summary_points else []
            )
        except Exception:
            summary_points = []

        result.append(
            CRSOut(
                id=crs.id,
                project_id=crs.project_id,
                status=crs.status.value,
                pattern=crs.pattern.value,
                version=crs.version,
                edit_version=crs.edit_version,
                content=crs.content,
                summary_points=summary_points,
                field_sources=None,
                created_by=crs.created_by,
                approved_by=crs.approved_by,
                rejection_reason=crs.rejection_reason,
                reviewed_at=crs.reviewed_at,
                created_at=crs.created_at,
            )
        )

    return result


@router.get("/my-requests", response_model=List[CRSOut])
def list_my_crs_requests(
    team_id: Optional[int] = Query(None, description="Filter by team"),
    project_id: Optional[int] = Query(None, description="Filter by specific project"),
    status: Optional[str] = Query(None, description="Filter by CRS status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all CRS documents created by the current user (client view).

    This endpoint allows clients to track the progress of their submitted CRS.
    Excludes draft documents - only shows submitted requests (under_review, approved, rejected).
    """
    # Build query to get CRS documents created by current user
    query = (
        db.query(CRSDocument)
        .join(Project, CRSDocument.project_id == Project.id)
        .filter(CRSDocument.created_by == current_user.id)
        # Exclude draft documents - clients should only see submitted CRS
        .filter(CRSDocument.status != CRSStatus.draft)
    )

    # Apply team filter if provided
    if team_id:
        # Verify user is member of this team
        PermissionService.verify_team_membership(db, team_id, current_user.id)
        query = query.filter(Project.team_id == team_id)

    # Apply project filter if provided
    if project_id:
        # Verify user has access to this project
        project = PermissionService.verify_project_access(db, project_id, current_user.id)
        query = query.filter(CRSDocument.project_id == project_id)

    # Apply status filter if provided
    if status:
        try:
            status_enum = CRSStatus(status)
            # Prevent filtering by draft status
            if status_enum == CRSStatus.draft:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Draft CRS documents are not shown in request tracking",
                )
            query = query.filter(CRSDocument.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {[s.value for s in CRSStatus]}",
            )

    # Order by most recent first
    crs_documents = query.order_by(CRSDocument.created_at.desc()).all()

    # Convert to response format
    result = []
    for crs in crs_documents:
        try:
            summary_points = (
                json.loads(crs.summary_points) if crs.summary_points else []
            )
        except Exception:
            summary_points = []

        try:
            field_sources_data = (
                json.loads(crs.field_sources) if crs.field_sources else None
            )
        except Exception:
            field_sources_data = None

        result.append(
            CRSOut(
                id=crs.id,
                project_id=crs.project_id,
                status=crs.status.value,
                pattern=crs.pattern if hasattr(crs, 'pattern') and crs.pattern else "babok",
                version=crs.version,
                edit_version=crs.edit_version if hasattr(crs, 'edit_version') and crs.edit_version is not None else 1,
                content=crs.content,
                summary_points=summary_points,
                field_sources=field_sources_data,
                created_by=crs.created_by,
                approved_by=crs.approved_by,
                rejection_reason=crs.rejection_reason,
                reviewed_at=crs.reviewed_at,
                created_at=crs.created_at,
            )
        )

    return result


@router.put("/{crs_id}/status", response_model=CRSOut)
def update_crs_status_endpoint(
    crs_id: int,
    payload: CRSStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the status of a CRS document (approval workflow).

    Status transitions:
    - draft -> under_review (Client submits for review)
    - under_review -> approved/rejected (BA reviews)
    - rejected -> draft (Client revises)
    """
    # Validate status value
    try:
        new_status = CRSStatus(payload.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {[s.value for s in CRSStatus]}",
        )

    # Validate rejection reason is provided when rejecting
    if new_status == CRSStatus.rejected and not payload.rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection reason is required when rejecting a CRS",
        )

    # Get CRS and verify access
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="CRS document not found"
        )

    project = PermissionService.verify_project_access(db, crs.project_id, current_user.id)

    # Only BAs or team admins can approve or reject CRS
    if new_status in [CRSStatus.approved, CRSStatus.rejected]:
        PermissionService.verify_crs_approval_authority(db, crs.project_id, current_user)

    # Store old status for notification
    old_status = crs.status.value

    # Update status using service function
    updated_crs = update_crs_status(
        db,
        crs_id=crs_id,
        new_status=new_status,
        approved_by=current_user.id if new_status == CRSStatus.approved else None,
        rejection_reason=(
            payload.rejection_reason if new_status == CRSStatus.rejected else None
        ),
    )

    # Notify team members
    team_members = (
        db.query(TeamMember).filter(TeamMember.team_id == project.team_id).all()
    )
    notify_users = [tm.user_id for tm in team_members if tm.user_id != current_user.id]

    if new_status == CRSStatus.approved:
        notify_crs_approved(
            db,
            updated_crs,
            project,
            current_user,
            notify_users,
            send_email_notification=True,
        )
    elif new_status == CRSStatus.rejected:
        notify_crs_rejected(
            db,
            updated_crs,
            project,
            current_user,
            notify_users,
            send_email_notification=True,
        )
    else:
        notify_crs_status_changed(
            db,
            updated_crs,
            project,
            old_status,
            new_status.value,
            notify_users,
            send_email_notification=True,
        )

    # Create audit log for status change
    audit_entry = CRSAuditLog(
        crs_id=crs_id,
        changed_by=current_user.id,
        action="status_updated",
        old_status=old_status,
        new_status=new_status.value,
        summary=f"CRS status changed from {old_status} to {new_status.value}",
    )
    db.add(audit_entry)
    db.commit()

    try:
        summary_points = (
            json.loads(updated_crs.summary_points) if updated_crs.summary_points else []
        )
    except Exception:
        summary_points = []

    try:
        field_sources_data = (
            json.loads(updated_crs.field_sources) if updated_crs.field_sources else None
        )
    except Exception:
        field_sources_data = None

    return CRSOut(
        id=updated_crs.id,
        project_id=updated_crs.project_id,
        status=updated_crs.status.value,
        pattern=updated_crs.pattern.value if updated_crs.pattern else "babok",
        version=updated_crs.version,
        edit_version=updated_crs.edit_version,
        content=updated_crs.content,
        summary_points=summary_points,
        field_sources=field_sources_data,
        created_by=updated_crs.created_by,
        approved_by=updated_crs.approved_by,
        rejection_reason=updated_crs.rejection_reason,
        reviewed_at=updated_crs.reviewed_at,
        created_at=updated_crs.created_at,
    )
