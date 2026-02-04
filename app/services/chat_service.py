"""
Chat Service Module.
Handles all business logic for chat session operations.
Following architectural rules: stateless, no direct db.session access, uses repositories.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.session_model import SessionModel, SessionStatus
from app.models.user import User
from app.schemas.chat import CRSPatternEnum
from app.services.permission_service import PermissionService
from app.repositories import SessionRepository, MessageRepository


class ChatService:
    """Service for managing chat session operations."""

    @staticmethod
    def get_project_chats(
        db: Session, project_id: int, current_user: User
    ) -> List[Dict[str, Any]]:
        """
        Get all chat sessions for a specific project with message counts.
        Only team members can access project chats.
        """
        # Verify project access
        PermissionService.verify_project_access(db, project_id, current_user.id)

        # Get sessions with message counts
        session_repo = SessionRepository(db)
        sessions = session_repo.get_user_sessions_with_count(
            current_user.id, project_id
        )

        # Format response
        result = []
        for session, message_count in sessions:
            result.append({
                "id": session.id,
                "project_id": session.project_id,
                "user_id": session.user_id,
                "crs_document_id": session.crs_document_id,
                "crs_pattern": session.crs_pattern,
                "name": session.name,
                "status": session.status,
                "started_at": session.started_at,
                "ended_at": session.ended_at,
                "message_count": message_count or 0,
            })

        return result

    @staticmethod
    def create_chat_session(
        db: Session,
        project_id: int,
        name: str,
        crs_pattern: Optional[CRSPatternEnum],
        crs_document_id: Optional[int],
        current_user: User,
    ) -> SessionModel:
        """
        Create a new chat session for a project.
        Only team members can create sessions.
        """
        # Verify project access
        PermissionService.verify_project_access(db, project_id, current_user.id)

        # Create session
        session_repo = SessionRepository(db)
        new_session = session_repo.create(
            SessionModel(
                project_id=project_id,
                user_id=current_user.id,
                crs_document_id=crs_document_id,
                crs_pattern=crs_pattern.value if crs_pattern else "babok",
                name=name,
                status=SessionStatus.active,
            )
        )

        return new_session

    @staticmethod
    def get_chat_session(
        db: Session, session_id: int, current_user: User
    ) -> SessionModel:
        """
        Get a specific chat session.
        Only the session owner can view it.
        """
        session_repo = SessionRepository(db)
        session = session_repo.get_by_user_and_id(current_user.id, session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found or access denied",
            )

        return session

    @staticmethod
    def update_chat_session(
        db: Session,
        session_id: int,
        current_user: User,
        name: Optional[str] = None,
        status_update: Optional[SessionStatus] = None,
        crs_document_id: Optional[int] = None,
    ) -> SessionModel:
        """
        Update a chat session.
        Only the session owner can update it.
        """
        session_repo = SessionRepository(db)
        session = session_repo.get_by_user_and_id(current_user.id, session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found or access denied",
            )

        # Update fields
        if name is not None:
            session.name = name
        if status_update is not None:
            session = session_repo.update_status(session_id, status_update)
        if crs_document_id is not None:
            session = session_repo.update_crs_document(session_id, crs_document_id)

        # If only name changed, update the session
        if name is not None and status_update is None and crs_document_id is None:
            session = session_repo.update(session)

        return session

    @staticmethod
    def delete_chat_session(
        db: Session, session_id: int, current_user: User
    ) -> Dict[str, str]:
        """
        Delete a chat session and all its messages.
        Only the session owner can delete it.
        """
        session_repo = SessionRepository(db)
        session = session_repo.get_by_user_and_id(current_user.id, session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found or access denied",
            )

        # Delete all messages first
        message_repo = MessageRepository(db)
        message_repo.delete_by_session(session_id)

        # Delete session
        session_repo.delete(session)

        return {"message": "Chat session deleted successfully"}

    @staticmethod
    def get_session_messages(
        db: Session,
        session_id: int,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> List:
        """
        Get messages for a chat session.
        Only the session owner can access messages.
        """
        # Verify session access
        session_repo = SessionRepository(db)
        session = session_repo.get_by_user_and_id(current_user.id, session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found or access denied",
            )

        # Get messages
        message_repo = MessageRepository(db)
        messages = message_repo.get_by_session(
            session_id, skip=skip, limit=limit, order_desc=False
        )

        return messages
