"""
CRS Versioning Module.
Handles CRS version history, draft generation, preview, and content updates.
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.audit import CRSAuditLog
from app.models.crs import CRSDocument
from app.models.session_model import SessionModel
from app.models.team import TeamMember
from app.models.user import User
from app.services.permission_service import PermissionService
from app.services.crs_service import (
    generate_preview_crs,
    get_crs_by_id,
    get_crs_versions,
    persist_crs_document,
    update_crs_content,
)
from app.services.notification_service import notify_crs_created
from app.schemas.crs import CRSOut, CRSPreviewOut, CRSContentUpdate


router = APIRouter()


@router.get("/versions", response_model=List[CRSOut])
def read_crs_versions(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch all CRS versions for a project, ordered by version descending (newest first).
    """
    project = PermissionService.verify_project_access(db, project_id, current_user.id)

    versions = get_crs_versions(db, project_id=project_id)
    result = []
    for crs in versions:
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
    # Get the session and verify access
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user has access to this session's project
    project = PermissionService.verify_project_access(db, session.project_id, current_user.id)

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
            pattern=crs.pattern.value,
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
        - Missing/weak fields

    Use this during active conversations to check progress before finalizing.
    """
    # Get the session and verify access
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user has access to this session's project
    project = PermissionService.verify_project_access(db, session.project_id, current_user.id)

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


@router.put("/{crs_id}/content", response_model=CRSOut)
def update_crs_content_endpoint(
    crs_id: int,
    payload: CRSContentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the content of a CRS document.
    
    This endpoint is used for the in-place editor.
    Performs optimistic locking if expected_version is provided.
    """
    # Get CRS and verify access
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="CRS document not found"
        )

    project = PermissionService.verify_project_access(db, crs.project_id, current_user.id)

    # Allow updates only if not in finalized state (approved)
    PermissionService.verify_crs_editable(crs)

    try:
        updated_crs = update_crs_content(
            db,
            crs_id=crs_id,
            content=payload.content,
            field_sources=payload.field_sources,
            expected_version=payload.edit_version,
        )
        
        # Create audit log for content update
        audit_entry = CRSAuditLog(
            crs_id=crs.id,
            changed_by=current_user.id,
            action="content_update",
            new_content=payload.content,
            summary=f"CRS content updated by {current_user.email}",
        )
        db.add(audit_entry)
        db.commit()
        
        # Helper to parse fields for response
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

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
