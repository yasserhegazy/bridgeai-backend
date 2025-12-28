"""
CRS persistence and indexing helpers.
"""

import json
import logging
from typing import List, Optional

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
    store_embedding: bool = True
) -> CRSDocument:
    """
    Persist a CRS document and optionally store it in the semantic memory index.
    Embedding storage is optional to allow tests to run without Chroma.
    
    Auto-increments the version number based on existing CRS documents for the project.
    """
    summary_payload = summary_points or []
    summary_as_text = json.dumps(summary_payload)

    # Calculate the next version number for this project
    latest = get_latest_crs(db, project_id=project_id)
    next_version = (latest.version + 1) if latest else 1

    crs = CRSDocument(
        project_id=project_id,
        created_by=created_by,
        content=content,
        summary_points=summary_as_text,
        version=next_version,
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
) -> CRSDocument:
    """
    Update the status of a CRS document.
    
    Args:
        db: Database session
        crs_id: ID of the CRS document to update
        new_status: New status to set
        approved_by: User ID of the approver (set when status is 'approved')
        
    Returns:
        Updated CRSDocument object
    """
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise ValueError(f"CRS document with id={crs_id} not found")

    crs.status = new_status
    if approved_by is not None:
        crs.approved_by = approved_by

    db.commit()
    db.refresh(crs)
    return crs


def get_crs_by_id(db: Session, *, crs_id: int) -> Optional[CRSDocument]:
    """
    Fetch a CRS document by its ID.
    """
    return db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
