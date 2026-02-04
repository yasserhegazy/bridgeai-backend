"""OTP repository for database operations."""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.repositories.base_repository import BaseRepository
from app.models.user_otp import UserOTP


class OTPRepository(BaseRepository[UserOTP]):
    """Repository for OTP model operations."""

    def __init__(self, db: Session):
        """
        Initialize OTPRepository.

        Args:
            db: Database session
        """
        super().__init__(UserOTP, db)

    def get_by_email(self, email: str) -> Optional[UserOTP]:
        """
        Get OTP by email.

        Args:
            email: User email

        Returns:
            OTP or None if not found
        """
        return self.db.query(UserOTP).filter(UserOTP.email == email).first()

    def get_by_email_and_otp(self, email: str, otp: str) -> Optional[UserOTP]:
        """
        Get OTP by email and OTP code.

        Args:
            email: User email
            otp: OTP code

        Returns:
            OTP or None if not found
        """
        return (
            self.db.query(UserOTP)
            .filter(UserOTP.email == email, UserOTP.otp == otp)
            .first()
        )

    def delete_by_email(self, email: str) -> None:
        """
        Delete all OTP entries for an email.

        Args:
            email: User email
        """
        self.db.query(UserOTP).filter(UserOTP.email == email).delete()
        self.db.flush()

    def is_valid(self, otp_record: UserOTP) -> bool:
        """
        Check if OTP is still valid (not expired).

        Args:
            otp_record: OTP record to check

        Returns:
            True if valid, False if expired
        """
        return otp_record.expires_at > datetime.utcnow()
