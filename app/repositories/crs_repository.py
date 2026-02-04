"""CRS repository for database operations."""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.repositories.base_repository import BaseRepository
from app.models.crs import CRSDocument, CRSStatus
from app.models.session_model import SessionModel
from app.models.message import Message
from app.models.audit import CRSAuditLog
from app.models.comment import Comment


class CRSRepository(BaseRepository[CRSDocument]):
    """Repository for CRS document operations."""

    def __init__(self, db: Session):
        """
        Initialize CRSRepository.

        Args:
            db: Database session
        """
        super().__init__(CRSDocument, db)

    def get_by_session(self, session_id: int) -> Optional[CRSDocument]:
        """
        Get CRS document by session ID.

        Args:
            session_id: Session ID

        Returns:
            CRS document or None if not found
        """
        return (
            self.db.query(CRSDocument)
            .filter(CRSDocument.session_id == session_id)
            .first()
        )

    def get_latest_by_project(self, project_id: int) -> Optional[CRSDocument]:
        """
        Get latest CRS document for a project.

        Args:
            project_id: Project ID

        Returns:
            Latest CRS document or None if not found
        """
        return (
            self.db.query(CRSDocument)
            .filter(CRSDocument.project_id == project_id)
            .order_by(desc(CRSDocument.version))
            .first()
        )

    def get_by_project_and_version(
        self, project_id: int, version: int
    ) -> Optional[CRSDocument]:
        """
        Get CRS document by project and version.

        Args:
            project_id: Project ID
            version: CRS version

        Returns:
            CRS document or None if not found
        """
        return (
            self.db.query(CRSDocument)
            .filter(CRSDocument.project_id == project_id, CRSDocument.version == version)
            .first()
        )

    def get_project_crs_list(
        self, project_id: int, status: Optional[CRSStatus] = None
    ) -> List[CRSDocument]:
        """
        Get all CRS documents for a project.

        Args:
            project_id: Project ID
            status: Optional status filter

        Returns:
            List of CRS documents
        """
        query = self.db.query(CRSDocument).filter(CRSDocument.project_id == project_id)
        if status:
            query = query.filter(CRSDocument.status == status)
        return query.order_by(desc(CRSDocument.version)).all()

    def get_project_crs_status_counts(self, project_id: int) -> Dict[str, int]:
        """
        Get count of CRS documents by status for a project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary mapping status to count
        """
        result = (
            self.db.query(CRSDocument.status, func.count(CRSDocument.id))
            .filter(CRSDocument.project_id == project_id)
            .group_by(CRSDocument.status)
            .all()
        )
        return {status: count for status, count in result}

    def count_versions(self, project_id: int) -> int:
        """
        Count number of distinct versions for a project.

        Args:
            project_id: Project ID

        Returns:
            Number of versions
        """
        return (
            self.db.query(func.count(func.distinct(CRSDocument.version)))
            .filter(CRSDocument.project_id == project_id)
            .scalar()
        )

    def get_latest_approved(self, project_id: int) -> Optional[CRSDocument]:
        """
        Get latest approved CRS document for a project.

        Args:
            project_id: Project ID

        Returns:
            Latest approved CRS document or None if not found
        """
        return (
            self.db.query(CRSDocument)
            .filter(
                CRSDocument.project_id == project_id,
                CRSDocument.status == CRSStatus.APPROVED,
            )
            .order_by(desc(CRSDocument.version))
            .first()
        )


class SessionRepository(BaseRepository[SessionModel]):
    """Repository for chat session operations."""

    def __init__(self, db: Session):
        """
        Initialize SessionRepository.

        Args:
            db: Database session
        """
        super().__init__(SessionModel, db)

    def get_project_sessions(
        self, project_id: int, status: Optional[str] = None
    ) -> List[SessionModel]:
        """
        Get all sessions for a project.

        Args:
            project_id: Project ID
            status: Optional status filter

        Returns:
            List of sessions
        """
        query = self.db.query(SessionModel).filter(
            SessionModel.project_id == project_id
        )
        if status:
            query = query.filter(SessionModel.status == status)
        return query.all()

    def get_sessions_with_message_count(
        self, project_id: int, status: Optional[str] = None
    ) -> List[tuple[SessionModel, int]]:
        """
        Get sessions with message count for a project.

        Args:
            project_id: Project ID
            status: Optional status filter

        Returns:
            List of tuples (session, message_count)
        """
        query = (
            self.db.query(SessionModel, func.count(Message.id).label("message_count"))
            .outerjoin(Message, Message.session_id == SessionModel.id)
            .filter(SessionModel.project_id == project_id)
            .group_by(SessionModel.id)
        )
        if status:
            query = query.filter(SessionModel.status == status)
        return query.all()

    def count_by_status(self, project_id: int) -> Dict[str, int]:
        """
        Get count of sessions by status for a project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary mapping status to count
        """
        result = (
            self.db.query(SessionModel.status, func.count(SessionModel.id))
            .filter(SessionModel.project_id == project_id)
            .group_by(SessionModel.status)
            .all()
        )
        return {status: count for status, count in result}

    def count_total(self, project_id: int) -> int:
        """
        Count total sessions for a project.

        Args:
            project_id: Project ID

        Returns:
            Number of sessions
        """
        return (
            self.db.query(func.count(SessionModel.id))
            .filter(SessionModel.project_id == project_id)
            .scalar()
        )


class MessageRepository(BaseRepository[Message]):
    """Repository for message operations."""

    def __init__(self, db: Session):
        """
        Initialize MessageRepository.

        Args:
            db: Database session
        """
        super().__init__(Message, db)

    def get_session_messages(
        self, session_id: int, limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get all messages for a session.

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages

        Returns:
            List of messages
        """
        query = self.db.query(Message).filter(Message.session_id == session_id)
        if limit:
            query = query.limit(limit)
        return query.all()

    def count_session_messages(self, session_id: int) -> int:
        """
        Count messages in a session.

        Args:
            session_id: Session ID

        Returns:
            Number of messages
        """
        return (
            self.db.query(func.count(Message.id))
            .filter(Message.session_id == session_id)
            .scalar()
        )

    def delete_session_messages(self, session_id: int) -> None:
        """
        Delete all messages for a session.

        Args:
            session_id: Session ID
        """
        self.db.query(Message).filter(Message.session_id == session_id).delete()
        self.db.flush()


class CRSAuditLogRepository(BaseRepository[CRSAuditLog]):
    """Repository for CRS audit log operations."""

    def __init__(self, db: Session):
        """
        Initialize CRSAuditLogRepository.

        Args:
            db: Database session
        """
        super().__init__(CRSAuditLog, db)

    def get_crs_logs(
        self, crs_id: int, action: Optional[str] = None
    ) -> List[CRSAuditLog]:
        """
        Get audit logs for a CRS document.

        Args:
            crs_id: CRS document ID
            action: Optional action filter

        Returns:
            List of audit logs
        """
        query = self.db.query(CRSAuditLog).filter(CRSAuditLog.crs_id == crs_id)
        if action:
            query = query.filter(CRSAuditLog.action == action)
        return query.order_by(desc(CRSAuditLog.timestamp)).all()


class CommentRepository(BaseRepository[Comment]):
    """Repository for comment operations."""

    def __init__(self, db: Session):
        """
        Initialize CommentRepository.

        Args:
            db: Database session
        """
        super().__init__(Comment, db)

    def get_crs_comments(
        self, crs_id: int, skip: int = 0, limit: int = 100
    ) -> List[Comment]:
        """
        Get all comments for a CRS document.

        Args:
            crs_id: CRS document ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of comments ordered by creation time (newest first)
        """
        return (
            self.db.query(Comment)
            .filter(Comment.crs_id == crs_id)
            .order_by(desc(Comment.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_crs_id(self, crs_id: int) -> int:
        """
        Count comments for a specific CRS document.

        Args:
            crs_id: CRS document ID

        Returns:
            Number of comments
        """
        return self.db.query(Comment).filter(Comment.crs_id == crs_id).count()
