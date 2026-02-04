"""
CRS CRUD Operations Module.
Handles basic Create, Read operations for CRS documents.
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.crs import CRSDocument
from app.models.user import User
from app.services.permission_service import PermissionService
from app.services.crs_service import (
    get_crs_by_id,
    get_latest_crs,
    persist_crs_document,
)
from app.services.notification_service import notify_crs_created
from app.schemas.crs import CRSCreate, CRSOut


router = APIRouter()


@router.post("/", response_model=CRSOut, status_code=status.HTTP_201_CREATED)
def create_crs(
    crs_in: CRSCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new CRS document.

    A CRS can be created in either:
    - Complete state: all required fields filled (status=draft)
    - Partial state: minimum 40% complete (status=draft, allow_partial=True)

    If session_id is provided, the CRS will be linked to that session.
    """
    from app.models.session_model import SessionModel

    project = PermissionService.verify_project_access(db, crs_in.project_id, current_user.id)

    # Validate partial CRS: If allow_partial is True, we need to check completeness
    if crs_in.allow_partial:
        completeness = crs_in.completeness_percentage or 0
        if completeness < 40:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Partial CRS must be at least 40% complete. Current: {completeness}%",
            )

    # Persist the CRS document
    crs = persist_crs_document(
        db=db,
        project_id=crs_in.project_id,
        content=crs_in.content,
        summary_points=crs_in.summary_points,  # Pass as list, service will JSON-encode it
        pattern=crs_in.pattern.value if crs_in.pattern else "babok",
        created_by=current_user.id,
    )

    # If session_id is provided, link the CRS to the session
    if crs_in.session_id:
        session = (
            db.query(SessionModel)
            .filter(SessionModel.id == crs_in.session_id)
            .first()
        )
        if session:
            session.crs_document_id = crs.id
            db.commit()

    # Notify team members about the new CRS
    from app.models.team import TeamMember
    
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

    # Parse summary_points and field_sources for response
    try:
        summary_points_list = json.loads(crs.summary_points) if crs.summary_points else []
    except Exception:
        summary_points_list = []

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
        summary_points=summary_points_list,
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
    project = PermissionService.verify_project_access(db, project_id, current_user.id)

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
    project = PermissionService.verify_project_access(db, session.project_id, current_user.id)

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

    project = PermissionService.verify_project_access(db, crs.project_id, current_user.id)

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
