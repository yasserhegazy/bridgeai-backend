"""
Tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class TestUserRegistration:
    """Test user registration functionality."""

    def test_register_client_user(self, client: TestClient, db: Session):
        """Test successful registration of a client user."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newclient@test.com",
                "password": "SecurePassword123!",
                "full_name": "New Client",
                "role": "client"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newclient@test.com"
        assert data["full_name"] == "New Client"
        assert data["role"] == "client"
        assert "id" in data
        assert "password" not in data
        
        # Verify user is in database
        user = db.query(User).filter(User.email == "newclient@test.com").first()
        assert user is not None
        assert user.role == UserRole.client

    def test_register_ba_user(self, client: TestClient, db: Session):
        """Test successful registration of a BA user."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newba@test.com",
                "password": "SecurePassword123!",
                "full_name": "New BA",
                "role": "ba"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "ba"
        
        # Verify user is in database
        user = db.query(User).filter(User.email == "newba@test.com").first()
        assert user is not None
        assert user.role == UserRole.ba

    def test_register_duplicate_email(self, client: TestClient, test_client_user: User):
        """Test that registering with duplicate email fails."""
        response = client.post(
            "/auth/register",
            json={
                "email": test_client_user.email,
                "password": "AnotherPassword123!",
                "full_name": "Duplicate User",
                "role": "client"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_missing_fields(self, client: TestClient):
        """Test that registration fails with missing required fields."""
        response = client.post(
            "/auth/register",
            json={
                "email": "incomplete@test.com",
                "password": "Password123!"
                # missing full_name and role
            }
        )
        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """Test user login functionality."""

    def test_login_success(self, client: TestClient, test_client_user: User):
        """Test successful login with valid credentials."""
        response = client.post(
            "/auth/token",
            data={"username": test_client_user.email, "password": "TestPassword123!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "client"

    def test_login_ba_user(self, client: TestClient, test_ba_user: User):
        """Test successful login for BA user."""
        response = client.post(
            "/auth/token",
            data={"username": test_ba_user.email, "password": "TestPassword123!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "ba"

    def test_login_invalid_email(self, client: TestClient):
        """Test login fails with non-existent email."""
        response = client.post(
            "/auth/token",
            data={"username": "nonexistent@test.com", "password": "Password123!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    def test_login_wrong_password(self, client: TestClient, test_client_user: User):
        """Test login fails with incorrect password."""
        response = client.post(
            "/auth/token",
            data={"username": test_client_user.email, "password": "WrongPassword123!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()


class TestGetCurrentUser:
    """Test getting current user information."""

    def test_get_me_authenticated(self, client: TestClient, client_auth_headers: dict, test_client_user: User):
        """Test getting current user info with valid token."""
        response = client.get("/auth/me", headers=client_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_client_user.id
        assert data["email"] == test_client_user.email
        assert data["full_name"] == test_client_user.full_name
        assert data["role"] == "client"

    def test_get_me_unauthenticated(self, client: TestClient):
        """Test getting current user info without authentication fails."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        """Test getting current user info with invalid token fails."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


class TestGetUserById:
    """Test getting user by ID."""

    def test_get_user_by_id_success(
        self, 
        client: TestClient, 
        client_auth_headers: dict, 
        test_ba_user: User
    ):
        """Test getting another user's info by ID."""
        response = client.get(
            f"/auth/users/{test_ba_user.id}",
            headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_ba_user.id
        assert data["email"] == test_ba_user.email
        assert data["full_name"] == test_ba_user.full_name

    def test_get_user_by_id_not_found(self, client: TestClient, client_auth_headers: dict):
        """Test getting non-existent user returns 404."""
        response = client.get(
            "/auth/users/99999",
            headers=client_auth_headers
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_user_by_id_unauthenticated(self, client: TestClient, test_ba_user: User):
        """Test getting user by ID without authentication fails."""
        response = client.get(f"/auth/users/{test_ba_user.id}")
        assert response.status_code == 401
