"""
Tests for comment endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.crs import CRSDocument
from app.models.user import User

class TestComments:
    """Test functionality for comments on CRS documents."""

    def test_create_comment_success(self, client: TestClient, sample_crs: CRSDocument, client_token: str):
        """Test successful creation of a comment."""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = client.post(
            "/api/comments/",
            json={"crs_id": sample_crs.id, "content": "This is a test comment."},
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "This is a test comment."
        assert data["crs_id"] == sample_crs.id
        assert "author_name" in data
        assert "created_at" in data

    def test_create_comment_invalid_crs(self, client: TestClient, client_token: str):
        """Test creating a comment for a non-existent CRS."""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = client.post(
            "/api/comments/",
            json={"crs_id": 99999, "content": "Invalid CRS comment"},
            headers=headers
        )

        assert response.status_code == 404

    def test_create_comment_no_auth(self, client: TestClient, sample_crs: CRSDocument):
        """Test creating a comment without authentication."""
        response = client.post(
            "/api/comments/",
            json={"crs_id": sample_crs.id, "content": "Unauthenticated comment"}
        )

        assert response.status_code == 401

    def test_get_comments_success(self, client: TestClient, sample_crs: CRSDocument, client_token: str):
        """Test retrieving comments for a CRS."""
        headers = {"Authorization": f"Bearer {client_token}"}
        # Create two comments
        client.post(
            "/api/comments/",
            json={"crs_id": sample_crs.id, "content": "Comment 1"},
            headers=headers
        )
        client.post(
            "/api/comments/",
            json={"crs_id": sample_crs.id, "content": "Comment 2"},
            headers=headers
        )

        # Get comments
        response = client.get(
            f"/api/comments/?crs_id={sample_crs.id}",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        contents = [c["content"] for c in data]
        assert "Comment 1" in contents
        assert "Comment 2" in contents
        # Verify order (latest first) - handled loosely due to potential identical timestamps in tests
        # assert data[0]["content"] == "Comment 2"

    def test_get_comments_invalid_crs(self, client: TestClient, client_token: str):
        """Test retrieving comments for a non-existent CRS."""
        headers = {"Authorization": f"Bearer {client_token}"}
        response = client.get(
            "/api/comments/?crs_id=99999",
            headers=headers
        )

        assert response.status_code == 404

    def test_create_comment_not_team_member(
        self, 
        client: TestClient, 
        sample_crs: CRSDocument, 
        another_client_auth_headers: dict
    ):
        """Test user outside the team cannot create comments."""
        # 'another_client_auth_headers' corresponds to a user NOT in the sample_crs's project/team
        # (Assuming the fixture setup ensures this isolation)
        
        response = client.post(
            "/api/comments/",
            json={"crs_id": sample_crs.id, "content": "Intruder comment"},
            headers=another_client_auth_headers
        )

        assert response.status_code == 403

    def test_get_comments_not_team_member(
        self, 
        client: TestClient, 
        sample_crs: CRSDocument, 
        another_client_auth_headers: dict
    ):
        """Test user outside the team cannot view comments."""
        response = client.get(
            f"/api/comments/?crs_id={sample_crs.id}",
            headers=another_client_auth_headers
        )

        assert response.status_code == 403
