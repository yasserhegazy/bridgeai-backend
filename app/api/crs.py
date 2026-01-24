import io
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.projects import (
    get_project_or_404,
    get_user_team_ids,
    verify_ba_role,
    verify_team_membership,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.audit import CRSAuditLog
from app.models.crs import CRSDocument, CRSStatus
from app.models.project import Project
from app.models.user import User
from app.schemas.export import ExportFormat
from app.services.crs_service import (
    generate_preview_crs,
    get_crs_by_id,
    get_crs_versions,
    get_latest_crs,
    persist_crs_document,
    update_crs_status,
)
from app.services.export_service import (
    crs_to_csv_data,
    crs_to_professional_html,
    export_markdown_bytes,
    generate_csv_bytes,
    html_to_pdf_bytes,
)
from app.services.notification_service import (
    notify_crs_approved,
    notify_crs_created,
    notify_crs_rejected,
    notify_crs_status_changed,
)


router = APIRouter()


class CRSCreate(BaseModel):
    project_id: int
    content: str
    summary_points: List[str] = Field(default_factory=list)
    allow_partial: bool = Field(
        default=False, description="Allow creation with incomplete data (draft status)"
    )
    completeness_percentage: Optional[int] = Field(
        None, description="Completeness percentage for partial CRS"
    )
    session_id: Optional[int] = Field(None, description="Session ID to link the CRS to")
    pattern: Optional[str] = Field(
        None, description="CRS Pattern (babok, ieee_830, iso_iec_ieee_29148, agile_user_stories)"
    )


class CRSStatusUpdate(BaseModel):
    """Schema for updating CRS status (approval workflow)."""

    status: str = Field(
        ..., description="New status: draft, under_review, approved, rejected"
    )
    rejection_reason: Optional[str] = Field(
        None, description="Reason for rejection (required when rejecting)"
    )


class CRSOut(BaseModel):
    id: int
    project_id: int
    status: str
    pattern: str
    version: int
    edit_version: int
    content: str
    summary_points: List[str]
    field_sources: Optional[dict] = None
    created_by: Optional[int] = None
    approved_by: Optional[int] = None
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True


class AuditLogOut(BaseModel):
    id: int
    crs_id: int
    changed_by: int
    changed_at: datetime
    action: str
    old_status: Optional[str]
    new_status: Optional[str]
    old_content: Optional[str]
    new_content: Optional[str]
    summary: Optional[str]

    class Config:
        orm_mode = True


class CRSPreviewOut(BaseModel):
    """Schema for CRS preview response (not persisted)."""

    content: str
    summary_points: List[str]
    overall_summary: str
    is_complete: bool
    completeness_percentage: int
    missing_required_fields: List[str]
    missing_optional_fields: List[str]
    filled_optional_count: int
    weak_fields: List[str] = Field(default_factory=list)
    field_sources: dict = Field(default_factory=dict)
    project_id: int
    session_id: int


@router.post("/", response_model=CRSOut, status_code=status.HTTP_201_CREATED)
def create_crs(
    payload: CRSCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create and persist a CRS document for a project.
    """
    project = get_project_or_404(db, payload.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    # Validate minimum threshold for partial CRS
    if payload.allow_partial:
        if (
            payload.completeness_percentage is None
            or payload.completeness_percentage < 40
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create partial CRS below 40% completion. Please provide more information.",
            )
        # Force draft status for partial CRS
        initial_status = CRSStatus.draft
    else:
        initial_status = CRSStatus.draft

    crs = persist_crs_document(
        db,
        project_id=payload.project_id,
        created_by=current_user.id,
        content=payload.content,
        summary_points=payload.summary_points,
        field_sources=getattr(payload, "field_sources", None),
        initial_status=initial_status,
        pattern=payload.pattern,
    )

    # Link CRS to session if provided
    if payload.session_id:
        from app.models.session_model import SessionModel

        session = (
            db.query(SessionModel).filter(SessionModel.id == payload.session_id).first()
        )
        if session and session.project_id == payload.project_id:
            session.crs_document_id = crs.id
            db.commit()

    # Notify team members - optimized single query
    from app.models.team import TeamMember

    # Single query to get all active team member IDs except current user
    notify_user_ids = (
        db.query(TeamMember.user_id)
        .filter(
            TeamMember.team_id == project.team_id,
            TeamMember.is_active == True,
            TeamMember.user_id != current_user.id,
        )
        .all()
    )
    notify_users = [uid[0] for uid in notify_user_ids]

    notify_crs_created(db, crs, project, notify_users, send_email_notification=True)

    # Create audit log for creation
    audit_entry = CRSAuditLog(
        crs_id=crs.id,
        changed_by=current_user.id,
        action="created",
        new_status=crs.status.value,
        new_content=crs.content,
        summary=f"CRS document created ({'partial draft' if payload.allow_partial else 'full draft'})",
    )
    db.add(audit_entry)
    db.commit()

    # Parse field_sources if available
    try:
        field_sources_data = (
            json.loads(crs.field_sources) if crs.field_sources else None
        )
    except Exception:
        field_sources_data = None

    return CRSOut(
        id=crs.id,
        project_id=crs.project_id,
        status=crs.status.value,
        pattern=crs.pattern.value if crs.pattern else "babok",
        version=crs.version,
        edit_version=crs.edit_version,
        content=crs.content,
        summary_points=payload.summary_points,
        field_sources=field_sources_data,
        created_by=crs.created_by,
        approved_by=crs.approved_by,
        rejection_reason=crs.rejection_reason,
        reviewed_at=crs.reviewed_at,
        created_at=crs.created_at,
    )


@router.get("/latest", response_model=Optional[CRSOut])
def read_latest_crs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch the most recent CRS for a project.
    """
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    crs = get_latest_crs(db, project_id=project_id)
    if not crs:
        return None

    try:
        summary_points = json.loads(crs.summary_points) if crs.summary_points else []
    except Exception:
        summary_points = []

    try:
        field_sources_data = (
            json.loads(crs.field_sources) if crs.field_sources else None
        )
    except Exception:
        field_sources_data = None

    return CRSOut(
        id=crs.id,
        project_id=crs.project_id,
        status=crs.status.value,
        pattern=crs.pattern.value if crs.pattern else "babok",
        version=crs.version,
        edit_version=crs.edit_version,
        content=crs.content,
        summary_points=summary_points,
        field_sources=field_sources_data,
        created_by=crs.created_by,
        approved_by=crs.approved_by,
        rejection_reason=crs.rejection_reason,
        reviewed_at=crs.reviewed_at,
        created_at=crs.created_at,
    )


@router.get("/session/{session_id}", response_model=Optional[CRSOut])
def read_crs_for_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch the CRS document linked to a specific chat session.
    This allows each chat to have its own independent CRS.
    """
    from app.models.session_model import SessionModel

    # Get the session and verify access
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user has access to this session's project
    project = get_project_or_404(db, session.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    # If session has a linked CRS, return it
    if session.crs_document_id:
        crs = (
            db.query(CRSDocument)
            .filter(CRSDocument.id == session.crs_document_id)
            .first()
        )
        if crs:
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

            return CRSOut(
                id=crs.id,
                project_id=crs.project_id,
                status=crs.status.value,
                pattern=crs.pattern.value if crs.pattern else "babok",
                version=crs.version,
                edit_version=crs.edit_version,
                content=crs.content,
                summary_points=summary_points,
                field_sources=field_sources_data,
                created_by=crs.created_by,
                approved_by=crs.approved_by,
                rejection_reason=crs.rejection_reason,
                reviewed_at=crs.reviewed_at,
                created_at=crs.created_at,
            )

    # No CRS linked to this session
    return None


@router.post(
    "/sessions/{session_id}/generate-draft",
    response_model=CRSOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_draft_crs_from_session(
    session_id: int,
    pattern: Optional[str] = Query(None, description="CRS Pattern (babok, ieee_830, iso_iec_ieee_29148)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate and persist a draft CRS from current conversation state, even if incomplete.

    This endpoint allows users to generate a draft CRS document that can be refined later,
    without requiring all fields to be complete.

    Unlike the automatic generation, this creates a draft status CRS immediately.
    """
    from app.models.session_model import SessionModel

    # Get the session and verify access
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user has access to this session's project
    project = get_project_or_404(db, session.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    try:
         # Generate preview first
        preview_data = await generate_preview_crs(
            db=db, session_id=session_id, user_id=current_user.id, pattern=pattern
        )

        # Persist as draft CRS (force_draft=True bypasses completeness check)
        crs = persist_crs_document(
            db=db,
            project_id=session.project_id,
            created_by=current_user.id,
            content=preview_data["content"],
            summary_points=preview_data["summary_points"],
            field_sources=preview_data.get("field_sources", {}),
            force_draft=True,
        )

        # Link CRS to session
        session.crs_document_id = crs.id
        db.commit()
        db.refresh(session)

        # Notify team members
        from app.models.team import TeamMember
        from app.services.notification_service import notify_crs_created

        notify_user_ids = (
            db.query(TeamMember.user_id)
            .filter(
                TeamMember.team_id == project.team_id,
                TeamMember.is_active == True,
                TeamMember.user_id != current_user.id,
            )
            .all()
        )
        notify_users = [uid[0] for uid in notify_user_ids]

        notify_crs_created(db, crs, project, notify_users, send_email_notification=True)

        try:
            field_sources_data = (
                json.loads(crs.field_sources) if crs.field_sources else None
            )
        except Exception:
            field_sources_data = None

        return CRSOut(
            id=crs.id,
            project_id=crs.project_id,
            status=crs.status.value,
            version=crs.version,
            edit_version=crs.edit_version,
            content=crs.content,
            summary_points=preview_data["summary_points"],
            field_sources=field_sources_data,
            created_by=crs.created_by,
            approved_by=crs.approved_by,
            rejection_reason=crs.rejection_reason,
            reviewed_at=crs.reviewed_at,
            created_at=crs.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate draft CRS: {str(e)}",
        )


@router.get("/sessions/{session_id}/preview", response_model=CRSPreviewOut)
async def preview_crs_for_session(
    session_id: int,
    pattern: Optional[str] = Query(None, description="CRS Pattern (babok, ieee_830, iso_iec_ieee_29148)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a preview CRS from the current conversation state without persisting it.

    This endpoint allows users to see their CRS progress even when incomplete,
    providing visibility into what information has been gathered so far.

    Returns:
        - CRS content (JSON)
        - Summary points
        - Completeness percentage
        - Missing required and optional fields

    Use this during active conversations to check progress before finalizing.
    """
    from app.models.session_model import SessionModel

    # Get the session and verify access
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user has access to this session's project
    project = get_project_or_404(db, session.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    try:
        preview_data = await generate_preview_crs(
            db=db, session_id=session_id, user_id=current_user.id, pattern=pattern
        )
        return CRSPreviewOut(**preview_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate CRS preview: {str(e)}",
        )


@router.get("/review", response_model=List[CRSOut])
def list_crs_for_review(
    team_id: Optional[int] = Query(None, description="Filter by specific team"),
    status: Optional[str] = Query(
        None, description="Filter by status: draft, under_review, approved, rejected"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all CRS documents for BA review.
    Only Business Analysts can access this endpoint.
    Optionally filter by team and/or status.
    """
    # Verify BA role
    verify_ba_role(current_user)

    # Determine which teams to query
    if team_id:
        # Verify BA is member of the specific team
        verify_team_membership(db, team_id, current_user.id)
        team_ids = [team_id]
    else:
        # Get all team IDs where BA is a member
        team_ids = get_user_team_ids(db, current_user.id)

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
                version=crs.version,
                content=crs.content,
                summary_points=summary_points,
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
        verify_team_membership(db, team_id, current_user.id)
        query = query.filter(Project.team_id == team_id)

    # Apply project filter if provided
    if project_id:
        # Verify user has access to this project
        project = get_project_or_404(db, project_id)
        verify_team_membership(db, project.team_id, current_user.id)
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

        result.append(
            CRSOut(
                id=crs.id,
                project_id=crs.project_id,
                status=crs.status.value,
                version=crs.version,
                content=crs.content,
                summary_points=summary_points,
                created_by=crs.created_by,
                approved_by=crs.approved_by,
                rejection_reason=crs.rejection_reason,
                reviewed_at=crs.reviewed_at,
                created_at=crs.created_at,
            )
        )

    return result


@router.get("/versions", response_model=List[CRSOut])
def read_crs_versions(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch all CRS versions for a project, ordered by version descending (newest first).
    """
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    versions = get_crs_versions(db, project_id=project_id)
    result = []
    for crs in versions:
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
                version=crs.version,
                content=crs.content,
                summary_points=summary_points,
                created_by=crs.created_by,
                approved_by=crs.approved_by,
                rejection_reason=crs.rejection_reason,
                reviewed_at=crs.reviewed_at,
                created_at=crs.created_at,
            )
        )
    return result


@router.get("/{crs_id}", response_model=CRSOut)
def read_crs(
    crs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch a specific CRS document version by its unique ID.
    """
    crs = get_crs_by_id(db, crs_id=crs_id)
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="CRS document not found"
        )

    project = get_project_or_404(db, crs.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    try:
        summary_points = json.loads(crs.summary_points) if crs.summary_points else []
    except Exception:
        summary_points = []

    try:
        field_sources_data = (
            json.loads(crs.field_sources) if crs.field_sources else None
        )
    except Exception:
        field_sources_data = None

    return CRSOut(
        id=crs.id,
        project_id=crs.project_id,
        status=crs.status.value,
        pattern=crs.pattern.value if crs.pattern else "babok",
        version=crs.version,
        edit_version=crs.edit_version,
        content=crs.content,
        summary_points=summary_points,
        field_sources=field_sources_data,
        created_by=crs.created_by,
        approved_by=crs.approved_by,
        rejection_reason=crs.rejection_reason,
        reviewed_at=crs.reviewed_at,
        created_at=crs.created_at,
    )


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

    project = get_project_or_404(db, crs.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

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
    from app.models.team import TeamMember

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


@router.get("/{crs_id}/audit", response_model=List[AuditLogOut])
def get_crs_audit_logs(
    crs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return audit log entries for a CRS document."""
    # Verify access to CRS
    crs = get_crs_by_id(db, crs_id=crs_id)
    if not crs:
        raise HTTPException(status_code=404, detail="CRS document not found")
    project = get_project_or_404(db, crs.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    logs = (
        db.query(CRSAuditLog)
        .filter(CRSAuditLog.crs_id == crs_id)
        .order_by(CRSAuditLog.changed_at.desc())
        .all()
    )

    return [
        {
            "id": log.id,
            "crs_id": log.crs_id,
            "changed_by": log.changed_by,
            "changed_at": log.changed_at,
            "action": log.action,
            "old_status": log.old_status,
            "new_status": log.new_status,
            "old_content": log.old_content,
            "new_content": log.new_content,
            "summary": log.summary,
        }
        for log in logs
    ]


@router.post("/{crs_id}/export")
def export_crs(
    crs_id: int,
    format: ExportFormat = Query(ExportFormat.pdf),
    requirements_only: bool = Query(
        False, description="If true, export only requirements (CSV only)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export a CRS document as PDF or Markdown with professional formatting.

    PDF exports include a professional corporate document header and styling.
    """
    # Get CRS document
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="CRS document not found"
        )

    # Verify access
    project = get_project_or_404(db, crs.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    filename = f"crs-v{crs.version}.{format.value}"

    # If CRS content is JSON, convert to markdown
    import json

    def crs_json_to_markdown(crs_json):
        md = []
        md.append(f"# {crs_json.get('project_title', 'CRS Document')}")
        md.append("\n---\n")
        if crs_json.get("project_description"):
            md.append(f"**Description:** {crs_json['project_description']}\n")
        if crs_json.get("project_objectives"):
            md.append(
                "## Objectives\n"
                + "\n".join(f"- {o}" for o in crs_json["project_objectives"])
                + "\n"
            )
        if crs_json.get("target_users"):
            md.append(f"**Target Users:** {', '.join(crs_json['target_users'])}\n")
        if crs_json.get("stakeholders"):
            md.append(f"**Stakeholders:** {', '.join(crs_json['stakeholders'])}\n")
        md.append("\n---\n")
        if crs_json.get("functional_requirements"):
            md.append("## Functional Requirements\n")
            for fr in crs_json["functional_requirements"]:
                md.append(
                    f"- **{fr['id']} {fr['title']}** ({fr['priority']}): {fr['description']}"
                )
        md.append("\n---\n")
        if crs_json.get("performance_requirements"):
            md.append(
                "## Performance Requirements\n"
                + "\n".join(f"- {p}" for p in crs_json["performance_requirements"])
                + "\n"
            )
        if crs_json.get("security_requirements"):
            md.append(
                "## Security Requirements\n"
                + "\n".join(f"- {s}" for s in crs_json["security_requirements"])
                + "\n"
            )
        if crs_json.get("scalability_requirements"):
            md.append(
                "## Scalability Requirements\n"
                + "\n".join(f"- {s}" for s in crs_json["scalability_requirements"])
                + "\n"
            )
        md.append("\n---\n")
        if crs_json.get("technology_stack"):
            md.append("## Technology Stack\n")
            for k, v in crs_json["technology_stack"].items():
                md.append(f"- **{k.capitalize()}**: {', '.join(v)}")
        if crs_json.get("integrations"):
            md.append(f"**Integrations:** {', '.join(crs_json['integrations'])}\n")
        if crs_json.get("budget_constraints"):
            md.append(f"**Budget:** {crs_json['budget_constraints']}\n")
        if crs_json.get("timeline_constraints"):
            md.append(f"**Timeline:** {crs_json['timeline_constraints']}\n")
        if crs_json.get("technical_constraints"):
            md.append(
                f"**Technical Constraints:** {', '.join(crs_json['technical_constraints'])}\n"
            )
        md.append("\n---\n")
        if crs_json.get("success_metrics"):
            md.append(
                "## Success Metrics\n"
                + "\n".join(f"- {m}" for m in crs_json["success_metrics"])
                + "\n"
            )
        if crs_json.get("acceptance_criteria"):
            md.append(
                "## Acceptance Criteria\n"
                + "\n".join(f"- {a}" for a in crs_json["acceptance_criteria"])
                + "\n"
            )
        if crs_json.get("assumptions"):
            md.append(f"**Assumptions:** {', '.join(crs_json['assumptions'])}\n")
        if crs_json.get("risks"):
            md.append(f"**Risks:** {', '.join(crs_json['risks'])}\n")
        if crs_json.get("out_of_scope"):
            md.append(f"**Out of Scope:** {', '.join(crs_json['out_of_scope'])}\n")
        md.append("\n---\n")
        return "\n".join(md)

    content = crs.content or ""
    try:
        crs_json = json.loads(content)
        markdown_content = crs_json_to_markdown(crs_json)
    except Exception:
        markdown_content = content

    if format == ExportFormat.markdown:
        data = export_markdown_bytes(markdown_content)
        media_type = "text/markdown"
    elif format == ExportFormat.pdf:
        from app.services.export_service import markdown_to_html

        html = markdown_to_html(markdown_content)
        try:
            data = html_to_pdf_bytes(html)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        media_type = "application/pdf"
    elif format == ExportFormat.csv:
        # Ensure we have JSON content
        try:
            crs_json_for_csv = json.loads(content)
        except json.JSONDecodeError:
            # Fallback if content is not JSON (legacy or plain text)
            crs_json_for_csv = {
                "project_title": "CRS Export",
                "project_description": content,
            }

        csv_rows = crs_to_csv_data(
            crs_json_for_csv,
            doc_id=crs.id,
            doc_version=crs.version,
            created_by=str(crs.created_by),
            created_date=crs.created_at.isoformat() if crs.created_at else "",
            requirements_only=requirements_only,
        )
        data = generate_csv_bytes(csv_rows)
        media_type = "text/csv"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
