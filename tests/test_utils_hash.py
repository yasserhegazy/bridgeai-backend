"""
Unit tests for password hashing utilities.
"""

import pytest

from app.utils.hash import hash_password, truncate_password, verify_password


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_truncate_long_password(self):
        """Test truncating password exceeding bcrypt limit."""
        long_password = "a" * 100
        truncated = truncate_password(long_password)

        assert len(truncated.encode("utf-8")) <= 72

    def test_hash_long_password(self):
        """Test hashing long password."""
        long_password = "a" * 100
        hashed = hash_password(long_password)

        assert verify_password(long_password, hashed) is True
