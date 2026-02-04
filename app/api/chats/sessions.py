"""
Chat Sessions Module.
Handles CRUD operations for chat sessions.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.session_model import SessionStatus
from app.models.user import User
from app.schemas.chat import SessionCreate, SessionListOut, SessionOut, SessionUpdate
from app.services.permission_service import PermissionService
from app.services.chat_service import ChatService


router = APIRouter()


@router.get("/{project_id}/chats", response_model=List[SessionListOut])
def get_project_chats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all chat sessions for a specific project."""
    sessions = ChatService.get_project_chats(
        db=db, project_id=project_id, current_user=current_user
    )
    return [SessionListOut(**session) for session in sessions]


@router.post(
    "/{project_id}/chats",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_project_chat(
    project_id: int,
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session for a project."""
    new_session = ChatService.create_chat_session(
        db=db,
        project_id=project_id,
        name=session_data.name,
        crs_pattern=session_data.crs_pattern,
        crs_document_id=session_data.crs_document_id,
        current_user=current_user,
    )

    return SessionOut(
        id=new_session.id,
        project_id=new_session.project_id,
        user_id=new_session.user_id,
        crs_document_id=new_session.crs_document_id,
        crs_pattern=new_session.crs_pattern,
        name=new_session.name,
        status=new_session.status,
        started_at=new_session.started_at,
        ended_at=new_session.ended_at,
        messages=[],
    )


@router.get("/{project_id}/chats/{chat_id}", response_model=SessionOut)
def get_project_chat(
    project_id: int,
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific chat session by its ID with all messages."""
    session = ChatService.get_chat_session(
        db=db, session_id=chat_id, current_user=current_user
    )

    if session.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found in this project",
        )

    return session


@router.put("/{project_id}/chats/{chat_id}", response_model=SessionOut)
def update_project_chat(
    project_id: int,
    chat_id: int,
    session_update: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a chat session status."""
    PermissionService.verify_project_access(db, project_id, current_user.id)

    session = ChatService.update_chat_session(
        db=db,
        session_id=chat_id,
        current_user=current_user,
        name=session_update.name,
        status_update=session_update.status,
    )

    if session.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found in this project",
        )

    return session


@router.delete("/{project_id}/chats/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_chat(
    project_id: int,
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session and all its messages."""
    PermissionService.verify_project_access(db, project_id, current_user.id)

    ChatService.delete_chat_session(
        db=db, session_id=chat_id, current_user=current_user
    )

    return None
