"""
Tests for team management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember, TeamRole, TeamStatus
from app.models.user import User


class TestTeamCreation:
    """Test team creation functionality."""

    def test_create_team_success(self, client: TestClient, client_auth_headers: dict, test_client_user: User, db: Session):
        """Test successful team creation."""
        response = client.post(
            "/api/teams/",
            json={
                "name": "Test Team",
                "description": "A test team"
            },
            headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Team"
        assert data["description"] == "A test team"
        assert data["created_by"] == test_client_user.id
        assert data["status"] == "active"
        
        # Verify creator is added as owner
        assert len(data["members"]) == 1
        assert data["members"][0]["user_id"] == test_client_user.id
        assert data["members"][0]["role"] == "owner"

    def test_create_team_duplicate_name_same_user(
        self, 
        client: TestClient, 
        client_auth_headers: dict,
        test_client_user: User,
        db: Session
    ):
        """Test that creating duplicate team name by same user fails."""
        # Create first team
        client.post(
            "/api/teams/",
            json={"name": "My Team", "description": "First team"},
            headers=client_auth_headers
        )
        
        # Try to create team with same name
        response = client.post(
            "/api/teams/",
            json={"name": "My Team", "description": "Second team"},
            headers=client_auth_headers
        )
        assert response.status_code == 400
        assert "already have a team with this name" in response.json()["detail"]

    def test_create_team_unauthenticated(self, client: TestClient):
        """Test creating team without authentication fails."""
        response = client.post(
            "/api/teams/",
            json={"name": "Test Team", "description": "A test team"}
        )
        assert response.status_code == 401


class TestTeamRetrieval:
    """Test team retrieval functionality."""

    def test_list_teams(self, client: TestClient, client_auth_headers: dict, db: Session):
        """Test listing teams for authenticated user."""
        # Create teams
        response1 = client.post(
            "/api/teams/",
            json={"name": "Team 1", "description": "First team"},
            headers=client_auth_headers
        )
        team1_id = response1.json()["id"]
        
        response2 = client.post(
            "/api/teams/",
            json={"name": "Team 2", "description": "Second team"},
            headers=client_auth_headers
        )
        team2_id = response2.json()["id"]
        
        # List teams
        response = client.get("/api/teams/", headers=client_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        team_ids = [team["id"] for team in data]
        assert team1_id in team_ids
        assert team2_id in team_ids

    def test_get_team_by_id(self, client: TestClient, client_auth_headers: dict):
        """Test getting specific team details."""
        # Create team
        create_response = client.post(
            "/api/teams/",
            json={"name": "Test Team", "description": "A test team"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        # Get team
        response = client.get(f"/api/teams/{team_id}", headers=client_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == team_id
        assert data["name"] == "Test Team"

    def test_get_team_not_member(
        self, 
        client: TestClient, 
        client_auth_headers: dict,
        another_client_auth_headers: dict
    ):
        """Test that non-members cannot view team details."""
        # User 1 creates team
        create_response = client.post(
            "/api/teams/",
            json={"name": "Private Team", "description": "Private"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        # User 2 tries to access
        response = client.get(f"/api/teams/{team_id}", headers=another_client_auth_headers)
        assert response.status_code == 403


class TestTeamUpdate:
    """Test team update functionality."""

    def test_update_team_as_owner(self, client: TestClient, client_auth_headers: dict):
        """Test updating team as owner."""
        # Create team
        create_response = client.post(
            "/api/teams/",
            json={"name": "Original Name", "description": "Original description"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        # Update team
        response = client.put(
            f"/api/teams/{team_id}",
            json={
                "name": "Updated Name",
                "description": "Updated description",
                "status": "archived"
            },
            headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["status"] == "archived"

    def test_update_team_as_non_member(
        self, 
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict
    ):
        """Test that non-members cannot update team."""
        # User 1 creates team
        create_response = client.post(
            "/api/teams/",
            json={"name": "Test Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        # User 2 tries to update
        response = client.put(
            f"/api/teams/{team_id}",
            json={"name": "Hacked Name"},
            headers=another_client_auth_headers
        )
        assert response.status_code == 403


class TestTeamDeletion:
    """Test team deletion functionality."""

    def test_delete_team_as_owner(self, client: TestClient, client_auth_headers: dict):
        """Test deleting team as owner."""
        # Create team
        create_response = client.post(
            "/api/teams/",
            json={"name": "Team to Delete", "description": "Will be deleted"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        # Delete team
        response = client.delete(f"/api/teams/{team_id}", headers=client_auth_headers)
        assert response.status_code == 200
        
        # Verify deletion
        get_response = client.get(f"/api/teams/{team_id}", headers=client_auth_headers)
        assert get_response.status_code == 403 or get_response.status_code == 404

    def test_delete_team_as_non_owner(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict
    ):
        """Test that non-owners cannot delete team."""
        # User 1 creates team
        create_response = client.post(
            "/api/teams/",
            json={"name": "Protected Team", "description": "Cannot delete"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        # User 2 tries to delete
        response = client.delete(f"/api/teams/{team_id}", headers=another_client_auth_headers)
        assert response.status_code == 403


class TestTeamMemberManagement:
    """Test team member management."""

    def test_add_team_member(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_another_client_user: User,
        db: Session
    ):
        """Test adding a member to team."""
        # Create team
        create_response = client.post(
            "/api/teams/",
            json={"name": "Team with Members", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        # Add member
        response = client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_another_client_user.id, "role": "member"},
            headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_another_client_user.id
        assert data["role"] == "member"
        assert data["is_active"] is True

    def test_list_team_members(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_another_client_user: User
    ):
        """Test listing team members."""
        # Create team
        create_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        # Add member
        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_another_client_user.id, "role": "member"},
            headers=client_auth_headers
        )
        
        # List members
        response = client.get(f"/api/teams/{team_id}/members", headers=client_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Owner + added member
        
    def test_update_team_member_role(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_another_client_user: User
    ):
        """Test updating team member role."""
        # Create team and add member
        create_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        add_response = client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_another_client_user.id, "role": "member"},
            headers=client_auth_headers
        )
        member_id = add_response.json()["id"]
        
        # Update role
        response = client.put(
            f"/api/teams/{team_id}/members/{member_id}",
            json={"role": "admin"},
            headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

    def test_remove_team_member(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_another_client_user: User
    ):
        """Test removing a team member."""
        # Create team and add member
        create_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        add_response = client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_another_client_user.id, "role": "member"},
            headers=client_auth_headers
        )
        member_id = add_response.json()["id"]
        
        # Remove member
        response = client.delete(
            f"/api/teams/{team_id}/members/{member_id}",
            headers=client_auth_headers
        )
        assert response.status_code == 200
        
        # Verify member is deactivated
        list_response = client.get(
            f"/api/teams/{team_id}/members?include_inactive=true",
            headers=client_auth_headers
        )
        members = list_response.json()
        removed_member = next((m for m in members if m["id"] == member_id), None)
        assert removed_member is not None
        assert removed_member["is_active"] is False

    def test_cannot_remove_last_owner(self, client: TestClient, client_auth_headers: dict, db: Session):
        """Test that the last owner cannot be removed."""
        # Create team
        create_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = create_response.json()["id"]
        
        # Get owner member ID
        members_response = client.get(
            f"/api/teams/{team_id}/members",
            headers=client_auth_headers
        )
        owner_member = members_response.json()[0]
        
        # Try to remove owner
        response = client.delete(
            f"/api/teams/{team_id}/members/{owner_member['id']}",
            headers=client_auth_headers
        )
        assert response.status_code == 400
        assert "last owner" in response.json()["detail"].lower()
