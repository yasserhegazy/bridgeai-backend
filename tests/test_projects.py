"""
Tests for project management endpoints including approval workflow.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.project import Project, ProjectStatus
from app.models.user import User


class TestProjectCreation:
    """Test project creation with role-based workflow."""

    def test_ba_creates_approved_project(
        self, client: TestClient, ba_auth_headers: dict, test_ba_user: User, db: Session
    ):
        """Test that BA creates projects with approved status."""
        # Create team first
        team_response = client.post(
            "/api/teams/",
            json={"name": "BA Team", "description": "Test team"},
            headers=ba_auth_headers,
        )
        team_id = team_response.json()["id"]

        # Create project
        response = client.post(
            "/api/projects/",
            json={
                "name": "BA Project",
                "description": "Created by BA",
                "team_id": team_id,
            },
            headers=ba_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "BA Project"
        assert data["status"] == "approved"
        assert data["approved_by"] == test_ba_user.id
        assert data["approved_at"] is not None

    def test_client_creates_pending_project(
        self, client: TestClient, client_auth_headers: dict, test_client_user: User
    ):
        """Test that Client creates projects with pending status."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Client Team", "description": "Test team"},
            headers=client_auth_headers,
        )
        team_id = team_response.json()["id"]

        # Create project
        response = client.post(
            "/api/projects/",
            json={
                "name": "Client Project",
                "description": "Created by client",
                "team_id": team_id,
            },
            headers=client_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Client Project"
        assert data["status"] == "pending"
        assert data["approved_by"] is None
        assert data["approved_at"] is None

    def test_create_project_duplicate_name_same_team(
        self, client: TestClient, client_auth_headers: dict
    ):
        """Test that duplicate project names in same team are rejected."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers,
        )
        team_id = team_response.json()["id"]

        # Create first project
        client.post(
            "/api/projects/",
            json={"name": "Unique Project", "description": "First", "team_id": team_id},
            headers=client_auth_headers,
        )

        # Try to create duplicate
        response = client.post(
            "/api/projects/",
            json={
                "name": "Unique Project",
                "description": "Duplicate",
                "team_id": team_id,
            },
            headers=client_auth_headers,
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_project_non_team_member(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
    ):
        """Test that non-team members cannot create projects."""
        # User 1 creates team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Private Team", "description": "Test"},
            headers=client_auth_headers,
        )
        team_id = team_response.json()["id"]

        # User 2 tries to create project
        response = client.post(
            "/api/projects/",
            json={"name": "Project", "description": "Test", "team_id": team_id},
            headers=another_client_auth_headers,
        )
        assert response.status_code == 403


class TestProjectRetrieval:
    """Test project retrieval with role-based filtering."""

    def test_get_project_by_id(self, client: TestClient, client_auth_headers: dict):
        """Test getting specific project details."""
        # Create team and project
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers,
        )
        team_id = team_response.json()["id"]

        project_response = client.post(
            "/api/projects/",
            json={"name": "Project", "description": "Test", "team_id": team_id},
            headers=client_auth_headers,
        )
        project_id = project_response.json()["id"]

        # Get project
        response = client.get(
            f"/api/projects/{project_id}", headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Project"

    def test_list_projects_client_sees_approved_and_own(
        self,
        client: TestClient,
        client_auth_headers: dict,
        ba_auth_headers: dict,
        test_ba_user: User,
        test_client_user: User,
        db: Session,
    ):
        """Test that clients see approved projects and their own pending requests."""
        # Create team with both BA and client
        team_response = client.post(
            "/api/teams/",
            json={"name": "Mixed Team", "description": "Test"},
            headers=ba_auth_headers,
        )
        team_id = team_response.json()["id"]

        # Add client to team
        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_client_user.id, "role": "member"},
            headers=ba_auth_headers,
        )

        # BA creates approved project
        client.post(
            "/api/projects/",
            json={
                "name": "Approved Project",
                "description": "By BA",
                "team_id": team_id,
            },
            headers=ba_auth_headers,
        )

        # Client creates pending project
        client.post(
            "/api/projects/",
            json={
                "name": "Pending Project",
                "description": "By Client",
                "team_id": team_id,
            },
            headers=client_auth_headers,
        )

        # Client lists projects
        response = client.get("/api/projects/", headers=client_auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 2
        project_names = [p["name"] for p in projects]
        assert "Approved Project" in project_names
        assert "Pending Project" in project_names

    def test_list_projects_ba_sees_all(
        self,
        client: TestClient,
        ba_auth_headers: dict,
        client_auth_headers: dict,
        test_ba_user: User,
        test_client_user: User,
        db: Session,
    ):
        """Test that BAs see all projects in their teams."""
        # Create team with both BA and client
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=ba_auth_headers,
        )
        team_id = team_response.json()["id"]

        # Add client to team
        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_client_user.id, "role": "member"},
            headers=ba_auth_headers,
        )

        # Client creates pending project
        client.post(
            "/api/projects/",
            json={
                "name": "Pending Project",
                "description": "By Client",
                "team_id": team_id,
            },
            headers=client_auth_headers,
        )

        # BA lists projects - should see pending project
        response = client.get("/api/projects/", headers=ba_auth_headers)
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) >= 1
        pending_project = next(
            (p for p in projects if p["name"] == "Pending Project"), None
        )
        assert pending_project is not None
        assert pending_project["status"] == "pending"


class TestProjectUpdate:
    """Test project update functionality."""

    def test_creator_can_update_own_project(
        self, client: TestClient, client_auth_headers: dict
    ):
        """Test that project creator can update their project."""
        # Create team and project
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers,
        )
        team_id = team_response.json()["id"]

        project_response = client.post(
            "/api/projects/",
            json={
                "name": "Original Name",
                "description": "Original",
                "team_id": team_id,
            },
            headers=client_auth_headers,
        )
        project_id = project_response.json()["id"]

        # Update project
        response = client.put(
            f"/api/projects/{project_id}",
            json={"name": "Updated Name", "description": "Updated description"},
            headers=client_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    def test_ba_can_update_any_project(
        self,
        client: TestClient,
        ba_auth_headers: dict,
        client_auth_headers: dict,
        test_client_user: User,
        db: Session,
    ):
        """Test that BA can update any project in their team."""
        # Create team with BA and client
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=ba_auth_headers,
        )
        team_id = team_response.json()["id"]

        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_client_user.id, "role": "member"},
            headers=ba_auth_headers,
        )

        # Client creates project
        project_response = client.post(
            "/api/projects/",
            json={"name": "Client Project", "description": "Test", "team_id": team_id},
            headers=client_auth_headers,
        )
        project_id = project_response.json()["id"]

        # BA updates project
        response = client.put(
            f"/api/projects/{project_id}",
            json={"name": "BA Updated", "description": "Updated by BA"},
            headers=ba_auth_headers,
        )
        assert response.status_code == 200

    def test_other_user_cannot_update_project(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_another_client_user: User,
        db: Session,
    ):
        """Test that other users cannot update projects."""
        # User 1 creates team and project
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers,
        )
        team_id = team_response.json()["id"]

        # Add user 2 to team as member
        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_another_client_user.id, "role": "member"},
            headers=client_auth_headers,
        )

        project_response = client.post(
            "/api/projects/",
            json={
                "name": "Protected Project",
                "description": "Test",
                "team_id": team_id,
            },
            headers=client_auth_headers,
        )
        project_id = project_response.json()["id"]

        # User 2 tries to update
        response = client.put(
            f"/api/projects/{project_id}",
            json={"name": "Hacked Name"},
            headers=another_client_auth_headers,
        )
        assert response.status_code == 403


class TestProjectApprovalWorkflow:
    """Test project approval and rejection workflow."""

    def test_ba_approves_pending_project(
        self,
        client: TestClient,
        ba_auth_headers: dict,
        client_auth_headers: dict,
        test_ba_user: User,
        test_client_user: User,
        db: Session,
    ):
        """Test BA approving a pending project."""
        # Create team with BA and client
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=ba_auth_headers,
        )
        team_id = team_response.json()["id"]

        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_client_user.id, "role": "member"},
            headers=ba_auth_headers,
        )

        # Client creates pending project
        project_response = client.post(
            "/api/projects/",
            json={"name": "Pending Project", "description": "Test", "team_id": team_id},
            headers=client_auth_headers,
        )
        project_id = project_response.json()["id"]

        # BA approves project
        response = client.put(
            f"/api/projects/{project_id}/approve", headers=ba_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == test_ba_user.id
        assert data["approved_at"] is not None

        # Check notification was created
        notifications = (
            db.query(Notification)
            .filter(Notification.user_id == test_client_user.id)
            .all()
        )
        assert len(notifications) >= 1
        approval_notif = next(
            (n for n in notifications if "approved" in n.message.lower()), None
        )
        assert approval_notif is not None

    def test_ba_rejects_pending_project(
        self,
        client: TestClient,
        ba_auth_headers: dict,
        client_auth_headers: dict,
        test_client_user: User,
        db: Session,
    ):
        """Test BA rejecting a pending project."""
        # Create team with BA and client
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=ba_auth_headers,
        )
        team_id = team_response.json()["id"]

        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_client_user.id, "role": "member"},
            headers=ba_auth_headers,
        )

        # Client creates pending project
        project_response = client.post(
            "/api/projects/",
            json={
                "name": "Project to Reject",
                "description": "Test",
                "team_id": team_id,
            },
            headers=client_auth_headers,
        )
        project_id = project_response.json()["id"]

        # BA rejects project
        response = client.put(
            f"/api/projects/{project_id}/reject",
            json={"rejection_reason": "Does not meet requirements"},
            headers=ba_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Does not meet requirements"

        # Check notification was created
        notifications = (
            db.query(Notification)
            .filter(Notification.user_id == test_client_user.id)
            .all()
        )
        rejection_notif = next(
            (n for n in notifications if "rejected" in n.message.lower()), None
        )
        assert rejection_notif is not None

    def test_client_cannot_approve_project(
        self, client: TestClient, client_auth_headers: dict
    ):
        """Test that clients cannot approve projects."""
        # Create team and project
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers,
        )
        team_id = team_response.json()["id"]

        project_response = client.post(
            "/api/projects/",
            json={"name": "Project", "description": "Test", "team_id": team_id},
            headers=client_auth_headers,
        )
        project_id = project_response.json()["id"]

        # Try to approve
        response = client.put(
            f"/api/projects/{project_id}/approve", headers=client_auth_headers
        )
        assert response.status_code == 403

    def test_cannot_approve_already_approved_project(
        self, client: TestClient, ba_auth_headers: dict
    ):
        """Test that already approved projects cannot be re-approved."""
        # Create team and project (auto-approved by BA)
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=ba_auth_headers,
        )
        team_id = team_response.json()["id"]

        project_response = client.post(
            "/api/projects/",
            json={
                "name": "Already Approved",
                "description": "Test",
                "team_id": team_id,
            },
            headers=ba_auth_headers,
        )
        project_id = project_response.json()["id"]

        # Try to approve again
        response = client.put(
            f"/api/projects/{project_id}/approve", headers=ba_auth_headers
        )
        assert response.status_code == 400
