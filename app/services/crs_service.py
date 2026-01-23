"""
CRS persistence and indexing helpers.
"""

import json
import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.crs import CRSDocument, CRSStatus
from app.ai.memory_service import create_memory

logger = logging.getLogger(__name__)


def persist_crs_document(
    db: Session,
    *,
    project_id: int,
    created_by: int,
    content: str,
    summary_points: Optional[List[str]] = None,
    field_sources: Optional[dict] = None,
    store_embedding: bool = True,
    force_draft: bool = False,
    initial_status: Optional[CRSStatus] = None
) -> CRSDocument:
    """
    Persist a CRS document and optionally store it in the semantic memory index.
    Embedding storage is optional to allow tests to run without Chroma.
    
    Auto-increments the version number based on existing CRS documents for the project.
    initial_status: Optional status to set (defaults to DRAFT)
    """
    summary_payload = summary_points or []
    summary_as_text = json.dumps(summary_payload)
    
    field_sources_text = json.dumps(field_sources) if field_sources else None

    # Calculate the next version number for this project
    latest = get_latest_crs(db, project_id=project_id)
    next_version = (latest.version + 1) if latest else 1

    # Determine initial status
    status = initial_status if initial_status is not None else CRSStatus.draft

    crs = CRSDocument(
        project_id=project_id,
        created_by=created_by,
        content=content,
        summary_points=summary_as_text,
        field_sources=field_sources_text,
        version=next_version,
        edit_version=1,  # Initialize optimistic locking version
        status=status,
    )

    db.add(crs)
    db.commit()
    db.refresh(crs)

    if store_embedding:
        try:
            create_memory(
                db=db,
                project_id=project_id,
                text=content,
                source_type="crs",
                source_id=crs.id,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to store CRS embedding for id=%s: %s", crs.id, exc)

    return crs


def get_latest_crs(db: Session, *, project_id: int) -> Optional[CRSDocument]:
    """Return the most recent CRS for a project (highest version number)."""
    return (
        db.query(CRSDocument)
        .filter(CRSDocument.project_id == project_id)
        .order_by(CRSDocument.version.desc())
        .first()
    )


def get_crs_versions(db: Session, *, project_id: int) -> List[CRSDocument]:
    """
    Return all CRS versions for a project, ordered by version descending.
    
    Args:
        db: Database session
        project_id: Project ID to fetch CRS versions for
        
    Returns:
        List of CRSDocument objects ordered by version (newest first)
    """
    return (
        db.query(CRSDocument)
        .filter(CRSDocument.project_id == project_id)
        .order_by(CRSDocument.version.desc())
        .all()
    )


def update_crs_status(
    db: Session,
    *,
    crs_id: int,
    new_status: CRSStatus,
    approved_by: Optional[int] = None,
    rejection_reason: Optional[str] = None,
    expected_version: Optional[int] = None,
) -> CRSDocument:
    """
    Update the status of a CRS document with optimistic locking support.
    
    Args:
        db: Database session
        crs_id: ID of the CRS document to update
        new_status: New status to set
        approved_by: User ID of the approver (set when status is 'approved')
        rejection_reason: Reason for rejection (set when status is 'rejected')
        expected_version: Expected edit_version for optimistic locking (optional)
        
    Returns:
        Updated CRSDocument object
        
    Raises:
        ValueError: If CRS not found or version mismatch (optimistic locking conflict)
    """
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise ValueError(f"CRS document with id={crs_id} not found")
    
    # Optimistic locking check
    if expected_version is not None and crs.edit_version != expected_version:
        raise ValueError(
            f"CRS document was modified by another user. "
            f"Expected version {expected_version}, but current version is {crs.edit_version}. "
            f"Please refresh and try again."
        )

    crs.status = new_status
    crs.reviewed_at = datetime.utcnow()
    crs.edit_version += 1  # Increment version for next update
    
    if approved_by is not None:
        crs.approved_by = approved_by
    
    if rejection_reason is not None:
        crs.rejection_reason = rejection_reason

    db.commit()
    db.refresh(crs)
    return crs


def get_crs_by_id(db: Session, *, crs_id: int) -> Optional[CRSDocument]:
    """
    Fetch a CRS document by its ID.
    """
    return db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()


async def generate_preview_crs(db: Session, *, session_id: int, user_id: int) -> dict:
    """
    Generate a preview CRS from the current conversation state without persisting it.
    
    This allows users to see their progress even when the CRS is incomplete.
    Uses the template filler in non-strict mode to generate partial CRS.
    
    Args:
        db: Database session
        session_id: Chat session ID
        user_id: User ID making the request
        
    Returns:
        dict: CRS preview data with completeness metadata
        
    Raises:
        ValueError: If session not found or user doesn't have access
    """
    from app.models.session_model import SessionModel
    from app.models.message import Message, SenderType
    from app.ai.nodes.template_filler.llm_template_filler import LLMTemplateFiller
    
    # Get session and verify access
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise ValueError(f"Session with id={session_id} not found")
    
    if session.user_id != user_id:
        raise ValueError("User does not have access to this session")
    
    # Get conversation history
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.timestamp.asc())
        .all()
    )
    
    if not messages:
        raise ValueError("No messages found in session")
    
    # Format conversation history
    conversation_history = []
    for msg in messages:
        role = "user" if msg.sender_type == SenderType.client else "assistant"
        conversation_history.append({
            "role": role,
            "content": msg.content
        })
    
    # Get the last user message
    last_user_message = next(
        (msg.content for msg in reversed(messages) if msg.sender_type == SenderType.client),
        ""
    )
    
    # Initialize template filler
    template_filler = LLMTemplateFiller()
    
    # Generate CRS with non-strict mode (allows partial completion)
    result = template_filler.fill_template(
        user_input=last_user_message,
        conversation_history=conversation_history,
        extracted_fields={}
    )
    
    # Check if any content exists (non-strict completeness)
    from app.ai.nodes.template_filler.llm_template_filler import CRSTemplate
    import json
    
    template_dict = result.get("crs_template", {})
    template = CRSTemplate(**template_dict)
    has_content = template_filler._check_completeness(template, strict_mode=False)
    
    if not has_content:
        raise ValueError("No CRS content available yet. Please provide more information.")
    
    return {
        "content": result["crs_content"],
        "summary_points": result["summary_points"],
        "overall_summary": result["overall_summary"],
        "is_complete": result["is_complete"],
        "completeness_percentage": result["completeness_percentage"],
        "missing_required_fields": result["missing_required_fields"],
        "missing_optional_fields": result["missing_optional_fields"],
        "filled_optional_count": result["filled_optional_count"],
        "weak_fields": result.get("weak_fields", []),
        "field_sources": result.get("field_sources", {}),
        "project_id": session.project_id,
        "session_id": session_id
    }
