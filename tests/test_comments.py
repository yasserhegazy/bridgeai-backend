"""
Tests for comment endpoints (SPEC-004.3).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.project import Project
from app.models.crs import CRSDocument, CRSStatus
from app.models.comment import Comment
from app.models.team import Team, TeamMember


class TestCommentEndpoints:
    """Test suite for comment API endpoints."""
    
    def test_create_comment_as_ba(
        self,
        client: TestClient,
        db: Session,
        ba_user: User,
        ba_token: str,
        sample_project: Project,
        sample_crs: CRSDocument
    ):
        """Test BA can create a comment on any CRS document."""
        payload = {
            "crs_id": sample_crs.id,
            "content": "Please clarify the authentication requirements in section 2.3"
        }
        
        response = client.post(
            "/api/comments",
            json=payload,
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["crs_id"] == sample_crs.id
        assert data["content"] == payload["content"]
        assert data["author_id"] == ba_user.id
        assert "created_at" in data
        assert data["author"]["role"] == "ba"
        assert data["author"]["full_name"] == ba_user.full_name
        
        # Verify in database
        comment = db.query(Comment).filter(Comment.id == data["id"]).first()
        assert comment is not None
        assert comment.content == payload["content"]
    
    def test_create_comment_as_client_on_own_project(
        self,
        client: TestClient,
        db: Session,
        client_user: User,
        client_token: str,
        sample_project: Project,
        sample_crs: CRSDocument
    ):
        """Test client can create a comment on their own project's CRS."""
        payload = {
            "crs_id": sample_crs.id,
            "content": "Thank you for the feedback. I will update section 2.3."
        }
        
        response = client.post(
            "/api/comments",
            json=payload,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["crs_id"] == sample_crs.id
        assert data["content"] == payload["content"]
        assert data["author"]["role"] == "client"
    
    def test_create_comment_on_nonexistent_crs(
        self,
        client: TestClient,
        ba_token: str
    ):
        """Test creating a comment on a non-existent CRS returns 404."""
        payload = {
            "crs_id": 99999,
            "content": "This should fail"
        }
        
        response = client.post(
            "/api/comments",
            json=payload,
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 404
    
    def test_create_comment_unauthorized(
        self,
        client: TestClient,
        sample_crs: CRSDocument
    ):
        """Test creating a comment without authentication fails."""
        payload = {
            "crs_id": sample_crs.id,
            "content": "Unauthorized comment"
        }
        
        response = client.post("/api/comments", json=payload)
        assert response.status_code == 401
    
    def test_get_crs_comments(
        self,
        client: TestClient,
        db: Session,
        ba_user: User,
        client_user: User,
        ba_token: str,
        sample_crs: CRSDocument
    ):
        """Test retrieving all comments for a CRS document."""
        from datetime import datetime, timedelta, timezone
        
        # Create multiple comments
        # BA comment created 1 minute ago
        comment1 = Comment(
            crs_id=sample_crs.id,
            author_id=ba_user.id,
            content="First comment from BA",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=1)
        )
        # Client comment created now
        comment2 = Comment(
            crs_id=sample_crs.id,
            author_id=client_user.id,
            content="Response from client",
            created_at=datetime.now(timezone.utc)
        )
        db.add_all([comment1, comment2])
        db.commit()
        
        response = client.get(
            f"/api/crs/{sample_crs.id}/comments",
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["comments"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 100
        
        # Verify comments are ordered by created_at descending (newest first)
        comments = data["comments"]
        assert comments[0]["content"] == "Response from client"
        assert comments[1]["content"] == "First comment from BA"
        
        # Verify author information is included
        assert comments[0]["author"]["full_name"] == client_user.full_name
        assert comments[1]["author"]["full_name"] == ba_user.full_name
    
    def test_get_crs_comments_pagination(
        self,
        client: TestClient,
        db: Session,
        ba_user: User,
        ba_token: str,
        sample_crs: CRSDocument
    ):
        """Test pagination of comments."""
        # Create 5 comments
        for i in range(5):
            comment = Comment(
                crs_id=sample_crs.id,
                author_id=ba_user.id,
                content=f"Comment {i+1}"
            )
            db.add(comment)
        db.commit()
        
        # Get first 2 comments
        response = client.get(
            f"/api/crs/{sample_crs.id}/comments?skip=0&limit=2",
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["comments"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 2
        
        # Get next 2 comments
        response = client.get(
            f"/api/crs/{sample_crs.id}/comments?skip=2&limit=2",
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["comments"]) == 2
        assert data["skip"] == 2
    
    def test_get_comment_by_id(
        self,
        client: TestClient,
        db: Session,
        ba_user: User,
        ba_token: str,
        sample_crs: CRSDocument
    ):
        """Test retrieving a specific comment by ID."""
        comment = Comment(
            crs_id=sample_crs.id,
            author_id=ba_user.id,
            content="Specific comment"
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        
        response = client.get(
            f"/api/comments/{comment.id}",
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == comment.id
        assert data["content"] == "Specific comment"
        assert data["author"]["full_name"] == ba_user.full_name
    
    def test_get_nonexistent_comment(
        self,
        client: TestClient,
        ba_token: str
    ):
        """Test retrieving a non-existent comment returns 404."""
        response = client.get(
            "/api/comments/99999",
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 404
    
    def test_update_comment(
        self,
        client: TestClient,
        db: Session,
        ba_user: User,
        ba_token: str,
        sample_crs: CRSDocument
    ):
        """Test updating a comment by its owner."""
        comment = Comment(
            crs_id=sample_crs.id,
            author_id=ba_user.id,
            content="Original content"
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        
        payload = {
            "content": "Updated content with more details"
        }
        
        response = client.put(
            f"/api/comments/{comment.id}",
            json=payload,
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == comment.id
        assert data["content"] == payload["content"]
        
        # Verify in database
        db.refresh(comment)
        assert comment.content == payload["content"]
    
    def test_update_comment_not_owner(
        self,
        client: TestClient,
        db: Session,
        ba_user: User,
        client_user: User,
        client_token: str,
        sample_crs: CRSDocument
    ):
        """Test that users cannot update comments they don't own."""
        comment = Comment(
            crs_id=sample_crs.id,
            author_id=ba_user.id,
            content="BA's comment"
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        
        payload = {
            "content": "Trying to update someone else's comment"
        }
        
        response = client.put(
            f"/api/comments/{comment.id}",
            json=payload,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        
        assert response.status_code == 403
    
    def test_delete_comment(
        self,
        client: TestClient,
        db: Session,
        ba_user: User,
        ba_token: str,
        sample_crs: CRSDocument
    ):
        """Test deleting a comment by its owner."""
        comment = Comment(
            crs_id=sample_crs.id,
            author_id=ba_user.id,
            content="Comment to delete"
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        comment_id = comment.id
        
        response = client.delete(
            f"/api/comments/{comment_id}",
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 204
        
        # Verify comment is deleted from database
        deleted_comment = db.query(Comment).filter(Comment.id == comment_id).first()
        assert deleted_comment is None
    
    def test_delete_comment_not_owner(
        self,
        client: TestClient,
        db: Session,
        ba_user: User,
        client_token: str,
        sample_crs: CRSDocument
    ):
        """Test that users cannot delete comments they don't own."""
        comment = Comment(
            crs_id=sample_crs.id,
            author_id=ba_user.id,
            content="BA's comment"
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        
        response = client.delete(
            f"/api/comments/{comment.id}",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        
        assert response.status_code == 403
    
    def test_client_cannot_access_other_project_crs_comments(
        self,
        client: TestClient,
        db: Session,
        client_user: User,
        client_token: str
    ):
        """Test that clients cannot access comments on CRS documents they don't have access to."""
        # Create another user and their project
        other_user = User(
            full_name="Other Client",
            email="other@example.com",
            password_hash="hashed",
            role=UserRole.client
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)
        
        # Create a team for the other user
        other_team = Team(
            name="Other Team",
            created_by=other_user.id
        )
        db.add(other_team)
        db.commit()
        db.refresh(other_team)
        
        # Create a project for the other user
        other_project = Project(
            name="Other Project",
            team_id=other_team.id,
            created_by=other_user.id
        )
        db.add(other_project)
        db.commit()
        db.refresh(other_project)
        
        # Create a CRS for the other project
        other_crs = CRSDocument(
            project_id=other_project.id,
            created_by=other_user.id,
            content="Other CRS content",
            summary_points="[]",
            status=CRSStatus.draft
        )
        db.add(other_crs)
        db.commit()
        db.refresh(other_crs)
        
        # Try to access comments on the other CRS
        response = client.get(
            f"/api/crs/{other_crs.id}/comments",
            headers={"Authorization": f"Bearer {client_token}"}
        )
        
        assert response.status_code == 403
    
    def test_empty_comment_content_validation(
        self,
        client: TestClient,
        ba_token: str,
        sample_crs: CRSDocument
    ):
        """Test that empty comment content is rejected."""
        payload = {
            "crs_id": sample_crs.id,
            "content": ""
        }
        
        response = client.post(
            "/api/comments",
            json=payload,
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_comment_content_max_length(
        self,
        client: TestClient,
        ba_token: str,
        sample_crs: CRSDocument
    ):
        """Test that comment content exceeding max length is rejected."""
        payload = {
            "crs_id": sample_crs.id,
            "content": "x" * 5001  # Exceeds 5000 character limit
        }
        
        response = client.post(
            "/api/comments",
            json=payload,
            headers={"Authorization": f"Bearer {ba_token}"}
        )
        
        assert response.status_code == 422  # Validation error
