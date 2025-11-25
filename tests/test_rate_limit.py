"""
Tests for rate limiting on authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestLoginRateLimit:
    """Test rate limiting on login endpoint."""

    def test_login_rate_limit(self, client: TestClient):
        """
        Test that login endpoint is rate limited to 5 requests per minute.
        """
        # Make 5 allowed requests
        for i in range(5):
            response = client.post(
                "/auth/token",
                data={"username": f"test{i}@example.com", "password": "password123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            # We expect 401 because credentials are wrong, but NOT 429 yet
            assert response.status_code != 429

        # Make 6th request - should be rate limited
        response = client.post(
            "/auth/token",
            data={"username": "test@example.com", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 429
        data = response.json()
        assert "detail" in data
        assert "too many requests" in data["detail"].lower() or "rate limit" in data["detail"].lower()


class TestRegisterRateLimit:
    """Test rate limiting on register endpoint."""

    def test_register_rate_limit(self, client: TestClient):
        """
        Test that register endpoint is rate limited to 3 requests per hour.
        """
        # Make 3 allowed requests
        for i in range(3):
            response = client.post(
                "/auth/register",
                json={
                    "email": f"ratelimit{i}@example.com",
                    "password": "Password123!",
                    "full_name": "Test User",
                    "role": "client"
                }
            )
            # We expect 200 (success) or 400 (duplicate email), but NOT 429
            assert response.status_code != 429

        # Make 4th request - should be rate limited
        response = client.post(
            "/auth/register",
            json={
                "email": "test_limit@example.com",
                "password": "Password123!",
                "full_name": "Test User",
                "role": "client"
            }
        )
        
        assert response.status_code == 429
        data = response.json()
        assert "detail" in data
        assert "too many requests" in data["detail"].lower() or "rate limit" in data["detail"].lower()


class TestGetMeRateLimit:
    """Test rate limiting on /auth/me endpoint."""

    def test_get_me_rate_limit(self, client: TestClient, client_auth_headers: dict):
        """
        Test that /auth/me endpoint is rate limited to 30 requests per minute.
        """
        # Make 30 allowed requests
        for i in range(30):
            response = client.get("/auth/me", headers=client_auth_headers)
            assert response.status_code == 200

        # Make 31st request - should be rate limited
        response = client.get("/auth/me", headers=client_auth_headers)
        assert response.status_code == 429
        data = response.json()
        assert "detail" in data
        assert "too many requests" in data["detail"].lower() or "rate limit" in data["detail"].lower()


class TestInvitationRateLimit:
    """Test rate limiting on invitation endpoint."""

    def test_invite_rate_limit(self, client: TestClient, client_auth_headers: dict):
        """
        Test that invite endpoint is rate limited to 10 requests per hour.
        """
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Rate Limit Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Make 10 allowed requests
        for i in range(10):
            response = client.post(
                f"/api/teams/{team_id}/invite",
                json={"email": f"invite{i}@example.com", "role": "member"},
                headers=client_auth_headers
            )
            # Should succeed or fail with 400 (duplicate), but NOT 429
            assert response.status_code != 429
        
        # Make 11th request - should be rate limited
        response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "overlimit@example.com", "role": "member"},
            headers=client_auth_headers
        )
        assert response.status_code == 429
        data = response.json()
        assert "detail" in data
        assert "too many requests" in data["detail"].lower() or "rate limit" in data["detail"].lower()
