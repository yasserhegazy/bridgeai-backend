"""Repository for chat session operations."""

from typing import List, Optional
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.session_model import SessionModel
from app.models.message import Message
from app.repositories.base_repository import BaseRepository


class SessionRepository(BaseRepository[SessionModel]):
    """Repository for SessionModel database operations."""

    def __init__(self, db: Session):
        """Initialize SessionRepository."""
        super().__init__(SessionModel, db)

    def get_user_sessions_with_count(
        self,
        user_id: int,
        project_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[tuple]:
        """
        Get user sessions with message count.

        Args:
            user_id: User ID
            project_id: Optional project filter
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of (SessionModel, message_count) tuples
        """
        query = (
            self.db.query(
                SessionModel,
                func.count(Message.id).label("message_count")
            )
            .outerjoin(Message, SessionModel.id == Message.session_id)
            .filter(SessionModel.user_id == user_id)
        )

        if project_id:
            query = query.filter(SessionModel.project_id == project_id)

        query = query.group_by(SessionModel.id).order_by(SessionModel.started_at.desc())

        return query.offset(skip).limit(limit).all()

    def get_by_user_and_id(self, user_id: int, session_id: int) -> Optional[SessionModel]:
        """
        Get session by user ID and session ID.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            SessionModel or None
        """
        return (
            self.db.query(SessionModel)
            .filter(
                and_(
                    SessionModel.id == session_id,
                    SessionModel.user_id == user_id
                )
            )
            .first()
        )

    def get_by_project(self, project_id: int) -> List[SessionModel]:
        """
        Get all sessions for a project.

        Args:
            project_id: Project ID

        Returns:
            List of sessions
        """
        return (
            self.db.query(SessionModel)
            .filter(SessionModel.project_id == project_id)
            .all()
        )

    def update_status(self, session_id: int, status: str) -> Optional[SessionModel]:
        """
        Update session status.

        Args:
            session_id: Session ID
            status: New status

        Returns:
            Updated session or None
        """
        session = self.get_by_id(session_id)
        if session:
            session.status = status
            self.db.commit()
            self.db.refresh(session)
        return session

    def update_crs_document(self, session_id: int, crs_document_id: int) -> Optional[SessionModel]:
        """
        Link CRS document to session.

        Args:
            session_id: Session ID
            crs_document_id: CRS document ID

        Returns:
            Updated session or None
        """
        session = self.get_by_id(session_id)
        if session:
            session.crs_document_id = crs_document_id
            self.db.commit()
            self.db.refresh(session)
        return session
