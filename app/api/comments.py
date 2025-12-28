"""
Comments API endpoints for CRS feedback (SPEC-004.3).

Allows Business Analysts to add comments, suggestions, and clarifications
on CRS documents. Clients can view these comments to understand feedback.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.crs import CRSDocument
from app.models.comment import Comment
from app.core.security import get_current_user, require_ba
from app.services.comment_service import (
    create_comment,
    get_comments_by_crs,
    get_comment_by_id,
    update_comment,
    delete_comment,
    get_comments_count_by_crs
)

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class CommentCreate(BaseModel):
    """Schema for creating a new comment."""
    crs_id: int = Field(..., description="ID of the CRS document to comment on")
    content: str = Field(..., min_length=1, max_length=5000, description="Comment content")


class CommentUpdate(BaseModel):
    """Schema for updating an existing comment."""
    content: str = Field(..., min_length=1, max_length=5000, description="Updated comment content")


class CommentAuthor(BaseModel):
    """Schema for comment author information."""
    model_config = {"from_attributes": True}
    
    id: int
    full_name: str
    email: str
    role: str


class CommentOut(BaseModel):
    """Schema for comment output."""
    model_config = {"from_attributes": True}
    
    id: int
    crs_id: int
    author_id: int
    content: str
    created_at: datetime
    author: Optional[CommentAuthor] = None


class CommentListResponse(BaseModel):
    """Schema for paginated comment list response."""
    comments: List[CommentOut]
    total: int
    skip: int
    limit: int


# ============================================================================
# Helper Functions
# ============================================================================

def verify_crs_access(db: Session, crs_id: int, user: User) -> CRSDocument:
    """
    Verify that the user has access to the CRS document.
    
    Args:
        db: Database session
        crs_id: ID of the CRS document
        user: Current user
        
    Returns:
        CRSDocument if access is granted
        
    Raises:
        HTTPException: If CRS not found or access denied
    """
    from app.models.project import Project
    from app.models.team import TeamMember
    from app.models.crs import CRSStatus

    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CRS document with id={crs_id} not found"
        )
    
    # Global restriction: No one can access comments for DRAFT CRS documents
    # Comments are for feedback on submitted/reviewed documents only.
    if crs.status == CRSStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Comments are not available for draft CRS documents"
        )
    
    # Check if user is the creator (always allow creator, regardless of role)
    if crs.created_by == user.id:
        return crs

    # For both Clients and BAs, check project/team membership
    from app.models.project import Project
    from app.models.team import TeamMember
    from app.models.crs import CRSStatus
    
    project = db.query(Project).filter(Project.id == crs.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if user is a member of the project's team
    # This covers both BAs assigned to the project and Client team members
    is_team_member = db.query(TeamMember).filter(
        TeamMember.team_id == project.team_id,
        TeamMember.user_id == user.id
    ).first()
    
    # If not a team member and not the project creator either, deny access
    if not is_team_member and project.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this CRS document"
        )
    
    return crs


def verify_comment_ownership(comment: Comment, user: User):
    """
    Verify that the user owns the comment (for update/delete operations).
    
    Args:
        comment: Comment object
        user: Current user
        
    Raises:
        HTTPException: If user doesn't own the comment
    """
    if comment.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own comments"
        )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment_endpoint(
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new comment on a CRS document.
    
    **SPEC-004.3**: BA can add comments and suggestions needing clarification.
    
    - **BAs** can comment on any CRS document
    - **Clients** can comment on CRS documents for their projects
    """
    # Verify access to the CRS document
    verify_crs_access(db, payload.crs_id, current_user)
    
    try:
        comment = create_comment(
            db,
            crs_id=payload.crs_id,
            author_id=current_user.id,
            content=payload.content
        )
        
        # Load author relationship for response
        db.refresh(comment)
        author = db.query(User).filter(User.id == comment.author_id).first()
        
        # Build response with author info
        response = CommentOut.model_validate(comment)
        if author:
            response.author = CommentAuthor(
                id=author.id,
                full_name=author.full_name,
                email=author.email,
                role=author.role.value
            )
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/crs/{crs_id}/comments", response_model=CommentListResponse)
def get_crs_comments(
    crs_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all comments for a specific CRS document.
    
    **SPEC-004.3**: Clients can access comments to understand BA feedback.
    
    Returns comments ordered by creation time (newest first).
    """
    # Verify access to the CRS document
    verify_crs_access(db, crs_id, current_user)
    
    comments = get_comments_by_crs(db, crs_id=crs_id, skip=skip, limit=limit)
    total = get_comments_count_by_crs(db, crs_id=crs_id)
    
    # Enrich comments with author information
    enriched_comments = []
    for comment in comments:
        author = db.query(User).filter(User.id == comment.author_id).first()
        comment_out = CommentOut.model_validate(comment)
        if author:
            comment_out.author = CommentAuthor(
                id=author.id,
                full_name=author.full_name,
                email=author.email,
                role=author.role.value
            )
        enriched_comments.append(comment_out)
    
    return CommentListResponse(
        comments=enriched_comments,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/comments/{comment_id}", response_model=CommentOut)
def get_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a specific comment by ID.
    """
    comment = get_comment_by_id(db, comment_id=comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id={comment_id} not found"
        )
    
    # Verify access to the CRS document
    verify_crs_access(db, comment.crs_id, current_user)
    
    # Load author information
    author = db.query(User).filter(User.id == comment.author_id).first()
    comment_out = CommentOut.model_validate(comment)
    if author:
        comment_out.author = CommentAuthor(
            id=author.id,
            full_name=author.full_name,
            email=author.email,
            role=author.role.value
        )
    
    return comment_out


@router.put("/comments/{comment_id}", response_model=CommentOut)
def update_comment_endpoint(
    comment_id: int,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing comment.
    
    Users can only update their own comments.
    """
    comment = get_comment_by_id(db, comment_id=comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id={comment_id} not found"
        )
    
    # Verify ownership
    verify_comment_ownership(comment, current_user)
    
    # Verify access to the CRS document
    verify_crs_access(db, comment.crs_id, current_user)
    
    try:
        updated_comment = update_comment(
            db,
            comment_id=comment_id,
            content=payload.content
        )
        
        # Load author information
        author = db.query(User).filter(User.id == updated_comment.author_id).first()
        comment_out = CommentOut.model_validate(updated_comment)
        if author:
            comment_out.author = CommentAuthor(
                id=author.id,
                full_name=author.full_name,
                email=author.email,
                role=author.role.value
            )
        
        return comment_out
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment_endpoint(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a comment.
    
    Users can only delete their own comments.
    """
    comment = get_comment_by_id(db, comment_id=comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id={comment_id} not found"
        )
    
    # Verify ownership
    verify_comment_ownership(comment, current_user)
    
    # Verify access to the CRS document
    verify_crs_access(db, comment.crs_id, current_user)
    
    success = delete_comment(db, comment_id=comment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment"
        )
    
    return None
