"""Notification repository for database operations."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.repositories.base_repository import BaseRepository
from app.models.notification import Notification


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification model operations."""

    def __init__(self, db: Session):
        """
        Initialize NotificationRepository.

        Args:
            db: Database session
        """
        super().__init__(Notification, db)

    def get_user_notifications(
        self, user_id: int, is_read: Optional[bool] = None
    ) -> List[Notification]:
        """
        Get all notifications for a user.

        Args:
            user_id: User ID
            is_read: Optional filter by read status

        Returns:
            List of notifications
        """
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        return query.order_by(Notification.created_at.desc()).all()

    def mark_all_as_read(self, user_id: int) -> None:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID
        """
        self.db.query(Notification).filter(
            Notification.user_id == user_id, Notification.is_read == False
        ).update({"is_read": True})
        self.db.flush()

    def delete_user_notifications(
        self, user_id: int, notification_type: Optional[str] = None
    ) -> None:
        """
        Delete notifications for a user.

        Args:
            user_id: User ID
            notification_type: Optional notification type filter
        """
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        if notification_type:
            query = query.filter(Notification.type == notification_type)
        query.delete()
        self.db.flush()

    def delete_by_reference(
        self, user_id: int, reference_type: str, reference_id: int
    ) -> None:
        """
        Delete notifications by reference.

        Args:
            user_id: User ID
            reference_type: Reference type (e.g., 'team_invitation')
            reference_id: Reference ID
        """
        self.db.query(Notification).filter(
            and_(
                Notification.user_id == user_id,
                Notification.type == reference_type,
                Notification.reference_id == reference_id,
            )
        ).delete()
        self.db.flush()
