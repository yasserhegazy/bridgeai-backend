"""
CRS Comments API endpoints.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.projects import get_project_or_404, verify_team_membership
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.comment import Comment
from app.models.crs import CRSDocument
from app.models.user import User
from app.services.notification_service import notify_crs_comment_added

router = APIRouter()


class CommentCreate(BaseModel):
    crs_id: int
    content: str


class CommentOut(BaseModel):
    id: int
    crs_id: int
    author_id: int
    author_name: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True


@router.post("/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a comment on a CRS document."""
    # Verify CRS exists
    crs = db.query(CRSDocument).filter(CRSDocument.id == payload.crs_id).first()
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="CRS document not found"
        )

    # Verify access
    project = get_project_or_404(db, crs.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    # Create comment
    comment = Comment(
        crs_id=payload.crs_id, author_id=current_user.id, content=payload.content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Notify team members
    from app.models.team import TeamMember

    team_members = (
        db.query(TeamMember).filter(TeamMember.team_id == project.team_id).all()
    )
    notify_users = [tm.user_id for tm in team_members]

    notify_crs_comment_added(
        db, crs, project, current_user, notify_users, send_email_notification=True
    )

    return CommentOut(
        id=comment.id,
        crs_id=comment.crs_id,
        author_id=comment.author_id,
        author_name=current_user.full_name,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("/", response_model=List[CommentOut])
def get_comments(
    crs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all comments for a CRS document."""
    # Verify CRS exists
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="CRS document not found"
        )

    # Verify access
    project = get_project_or_404(db, crs.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    # Get comments
    comments = (
        db.query(Comment)
        .filter(Comment.crs_id == crs_id)
        .order_by(Comment.created_at.desc())
        .all()
    )

    result = []
    for comment in comments:
        author = db.query(User).filter(User.id == comment.author_id).first()
        result.append(
            CommentOut(
                id=comment.id,
                crs_id=comment.crs_id,
                author_id=comment.author_id,
                author_name=author.full_name if author else "Unknown",
                content=comment.content,
                created_at=comment.created_at,
            )
        )

    return result
