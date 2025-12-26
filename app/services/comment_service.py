"""
Comment service for CRS feedback management.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.comment import Comment
from app.models.crs import CRSDocument
from app.models.user import User

logger = logging.getLogger(__name__)


def create_comment(
    db: Session,
    *,
    crs_id: int,
    author_id: int,
    content: str
) -> Comment:
    """
    Create a new comment on a CRS document.
    
    Args:
        db: Database session
        crs_id: ID of the CRS document to comment on
        author_id: ID of the user creating the comment
        content: Comment text content
        
    Returns:
        Created Comment object
        
    Raises:
        ValueError: If CRS document not found
    """
    # Verify CRS document exists
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise ValueError(f"CRS document with id={crs_id} not found")
    
    comment = Comment(
        crs_id=crs_id,
        author_id=author_id,
        content=content
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    logger.info(f"Comment {comment.id} created on CRS {crs_id} by user {author_id}")
    
    return comment


def get_comments_by_crs(
    db: Session,
    *,
    crs_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Comment]:
    """
    Retrieve all comments for a specific CRS document.
    
    Args:
        db: Database session
        crs_id: ID of the CRS document
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        
    Returns:
        List of Comment objects ordered by creation time (newest first)
    """
    return (
        db.query(Comment)
        .filter(Comment.crs_id == crs_id)
        .order_by(desc(Comment.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_comment_by_id(
    db: Session,
    *,
    comment_id: int
) -> Optional[Comment]:
    """
    Retrieve a specific comment by ID.
    
    Args:
        db: Database session
        comment_id: ID of the comment
        
    Returns:
        Comment object or None if not found
    """
    return db.query(Comment).filter(Comment.id == comment_id).first()


def update_comment(
    db: Session,
    *,
    comment_id: int,
    content: str
) -> Comment:
    """
    Update the content of an existing comment.
    
    Args:
        db: Database session
        comment_id: ID of the comment to update
        content: New comment content
        
    Returns:
        Updated Comment object
        
    Raises:
        ValueError: If comment not found
    """
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise ValueError(f"Comment with id={comment_id} not found")
    
    comment.content = content
    db.commit()
    db.refresh(comment)
    
    logger.info(f"Comment {comment_id} updated")
    
    return comment


def delete_comment(
    db: Session,
    *,
    comment_id: int
) -> bool:
    """
    Delete a comment.
    
    Args:
        db: Database session
        comment_id: ID of the comment to delete
        
    Returns:
        True if deleted, False if not found
    """
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        return False
    
    db.delete(comment)
    db.commit()
    
    logger.info(f"Comment {comment_id} deleted")
    
    return True


def get_comments_count_by_crs(
    db: Session,
    *,
    crs_id: int
) -> int:
    """
    Get the total count of comments for a CRS document.
    
    Args:
        db: Database session
        crs_id: ID of the CRS document
        
    Returns:
        Total number of comments
    """
    return db.query(Comment).filter(Comment.crs_id == crs_id).count()
