"""
Unit tests for core security module.
Tests JWT token creation, verification, and role-based access control.
"""
import pytest
from datetime import timedelta
from jose import jwt, JWTError
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    verify_token,
    require_role
)
from app.core.config import settings
from app.models.user import User, UserRole


class TestCreateAccessToken:
    """Test JWT token creation."""

    def test_create_token_basic(self):
        """Test creating a basic access token."""
        data = {"sub": "123"}
        token = create_access_token(data)
        
        assert token is not None
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "123"
        assert "exp" in payload

    def test_create_token_with_role(self):
        """Test creating token with user role."""
        data = {"sub": "123", "role": UserRole.ba}
        token = create_access_token(data)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["role"] == "ba"

    def test_create_token_custom_expiry(self):
        """Test creating token with custom expiration."""
        data = {"sub": "123"}
        token = create_access_token(data, expires_delta=timedelta(minutes=30))
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload


class TestDecodeAccessToken:
    """Test JWT token decoding."""

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        data = {"sub": "123", "email": "test@test.com"}
        token = create_access_token(data)
        
        payload = decode_access_token(token)
        assert payload["sub"] == "123"
        assert payload["email"] == "test@test.com"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token raises error."""
        with pytest.raises(JWTError):
            decode_access_token("invalid_token")

    def test_decode_expired_token(self):
        """Test decoding an expired token raises error."""
        data = {"sub": "123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        with pytest.raises(JWTError):
            decode_access_token(token)


class TestVerifyToken:
    """Test token verification with database lookup."""

    def test_verify_valid_token(self, db: Session, test_client_user: User):
        """Test verifying a valid token returns user."""
        data = {"sub": str(test_client_user.id)}
        token = create_access_token(data)
        
        user = verify_token(token, db)
        assert user.id == test_client_user.id
        assert user.email == test_client_user.email

    def test_verify_token_user_not_found(self, db: Session):
        """Test verifying token for non-existent user raises error."""
        data = {"sub": "99999"}
        token = create_access_token(data)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, db)
        assert exc_info.value.status_code == 401

    def test_verify_token_no_subject(self, db: Session):
        """Test verifying token without subject raises error."""
        data = {"email": "test@test.com"}
        token = create_access_token(data)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, db)
        assert exc_info.value.status_code == 401

    def test_verify_invalid_token(self, db: Session):
        """Test verifying invalid token raises error."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid_token", db)
        assert exc_info.value.status_code == 401


class TestRequireRole:
    """Test role-based access control."""

    def test_require_role_allowed(self, test_ba_user: User):
        """Test role checker allows user with correct role."""
        checker = require_role([UserRole.ba])
        result = checker(current_user=test_ba_user)
        assert result.id == test_ba_user.id

    def test_require_role_denied(self, test_client_user: User):
        """Test role checker denies user with wrong role."""
        checker = require_role([UserRole.ba])
        
        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=test_client_user)
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    def test_require_multiple_roles(self, test_ba_user: User, test_client_user: User):
        """Test role checker with multiple allowed roles."""
        checker = require_role([UserRole.ba, UserRole.client])
        
        # Both should be allowed
        result1 = checker(current_user=test_ba_user)
        assert result1.id == test_ba_user.id
        
        result2 = checker(current_user=test_client_user)
        assert result2.id == test_client_user.id
