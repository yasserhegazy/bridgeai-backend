"""
Tests for invitation functionality.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.invitation import Invitation
from app.models.team import TeamMember
from app.models.user import User


class TestInvitationCreation:
    """Test creating team invitations."""

    def test_owner_invites_user(
        self,
        client: TestClient,
        client_auth_headers: dict,
        db: Session
    ):
        """Test team owner inviting a user."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Send invitation
        response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "invited@test.com", "role": "member"},
            headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "invite_link" in data
        assert "invitation" in data
        assert data["invitation"]["email"] == "invited@test.com"
        assert data["invitation"]["role"] == "member"
        assert data["invitation"]["status"] == "pending"

    def test_admin_can_invite(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_another_client_user: User,
        db: Session
    ):
        """Test that admins can invite users."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Add another user as admin
        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_another_client_user.id, "role": "admin"},
            headers=client_auth_headers
        )
        
        # Admin sends invitation
        response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "newmember@test.com", "role": "viewer"},
            headers=another_client_auth_headers
        )
        assert response.status_code == 200

    def test_member_cannot_invite(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_another_client_user: User
    ):
        """Test that regular members cannot invite."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Add another user as member
        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_another_client_user.id, "role": "member"},
            headers=client_auth_headers
        )
        
        # Member tries to send invitation
        response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "newmember@test.com", "role": "member"},
            headers=another_client_auth_headers
        )
        assert response.status_code == 403

    def test_cannot_invite_existing_member(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_another_client_user: User
    ):
        """Test that cannot invite someone who is already a member."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Add user as member
        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_another_client_user.id, "role": "member"},
            headers=client_auth_headers
        )
        
        # Try to invite same user
        response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": test_another_client_user.email, "role": "member"},
            headers=client_auth_headers
        )
        assert response.status_code == 400
        assert "already a member" in response.json()["detail"].lower()

    def test_cannot_send_duplicate_invitation(
        self,
        client: TestClient,
        client_auth_headers: dict
    ):
        """Test that cannot send duplicate invitations to same email."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Send first invitation
        client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "invited@test.com", "role": "member"},
            headers=client_auth_headers
        )
        
        # Try to send duplicate
        response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "invited@test.com", "role": "admin"},
            headers=client_auth_headers
        )
        assert response.status_code == 400
        assert "already been sent" in response.json()["detail"].lower()


class TestInvitationRetrieval:
    """Test retrieving invitation information."""

    def test_get_invitation_by_token(
        self,
        client: TestClient,
        client_auth_headers: dict,
        db: Session
    ):
        """Test getting invitation details by token."""
        # Create team and invitation
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        invite_response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "invited@test.com", "role": "member"},
            headers=client_auth_headers
        )
        token = invite_response.json()["invitation"]["token"]
        
        # Get invitation by token
        response = client.get(f"/api/invitation/{token}")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "invited@test.com"
        assert data["role"] == "member"
        assert data["status"] == "pending"
        assert data["team_name"] == "Team"

    def test_list_team_invitations(
        self,
        client: TestClient,
        client_auth_headers: dict
    ):
        """Test listing invitations for a team."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Send multiple invitations
        client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "user1@test.com", "role": "member"},
            headers=client_auth_headers
        )
        client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "user2@test.com", "role": "admin"},
            headers=client_auth_headers
        )
        
        # List invitations
        response = client.get(
            f"/api/teams/{team_id}/invitations",
            headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        emails = [inv["email"] for inv in data]
        assert "user1@test.com" in emails
        assert "user2@test.com" in emails

    def test_member_cannot_list_invitations(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_another_client_user: User
    ):
        """Test that regular members cannot list invitations."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Add user as member
        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_another_client_user.id, "role": "member"},
            headers=client_auth_headers
        )
        
        # Try to list invitations
        response = client.get(
            f"/api/teams/{team_id}/invitations",
            headers=another_client_auth_headers
        )
        assert response.status_code == 403


class TestInvitationAcceptance:
    """Test accepting invitations."""

    def test_accept_invitation_success(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_another_client_user: User,
        another_client_auth_headers: dict,
        db: Session
    ):
        """Test successfully accepting an invitation."""
        # Create team and send invitation
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        invite_response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": test_another_client_user.email, "role": "member"},
            headers=client_auth_headers
        )
        token = invite_response.json()["invitation"]["token"]
        
        # Accept invitation
        response = client.post(
            f"/api/invitation/{token}/accept",
            headers=another_client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Invitation accepted successfully"
        assert data["team_id"] == team_id
        assert data["role"] == "member"
        
        # Verify membership was created
        member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == test_another_client_user.id,
            TeamMember.is_active == True
        ).first()
        assert member is not None
        
        # Verify invitation status updated
        invitation = db.query(Invitation).filter(Invitation.token == token).first()
        assert invitation.status == "accepted"

    def test_accept_invitation_wrong_email(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict
    ):
        """Test that user cannot accept invitation sent to different email."""
        # Create team and send invitation to different email
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        invite_response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": "different@test.com", "role": "member"},
            headers=client_auth_headers
        )
        token = invite_response.json()["invitation"]["token"]
        
        # Try to accept with wrong user
        response = client.post(
            f"/api/invitation/{token}/accept",
            headers=another_client_auth_headers
        )
        assert response.status_code == 403
        assert "different email" in response.json()["detail"].lower()

    def test_cannot_accept_expired_invitation(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_another_client_user: User,
        db: Session
    ):
        """Test that expired invitations cannot be accepted."""
        # Create team and invitation
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        invite_response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": test_another_client_user.email, "role": "member"},
            headers=client_auth_headers
        )
        token = invite_response.json()["invitation"]["token"]
        
        # Manually expire the invitation
        invitation = db.query(Invitation).filter(Invitation.token == token).first()
        invitation.expires_at = datetime.utcnow() - timedelta(days=1)
        db.commit()
        
        # Try to accept
        response = client.post(
            f"/api/invitation/{token}/accept",
            headers=another_client_auth_headers
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_cannot_accept_already_accepted_invitation(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_another_client_user: User
    ):
        """Test that already accepted invitations cannot be re-accepted."""
        # Create team and invitation
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        invite_response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": test_another_client_user.email, "role": "member"},
            headers=client_auth_headers
        )
        token = invite_response.json()["invitation"]["token"]
        
        # Accept invitation
        client.post(
            f"/api/invitation/{token}/accept",
            headers=another_client_auth_headers
        )
        
        # Try to accept again
        response = client.post(
            f"/api/invitation/{token}/accept",
            headers=another_client_auth_headers
        )
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "already" in detail or "accepted" in detail


class TestInvitationNotifications:
    """Test that invitations create appropriate notifications."""

    def test_invitation_creates_notification_for_existing_user(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_another_client_user: User,
        db: Session
    ):
        """Test that inviting an existing user creates a notification."""
        from app.models.notification import Notification
        
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Send invitation to existing user
        client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": test_another_client_user.email, "role": "member"},
            headers=client_auth_headers
        )
        
        # Check notification was created
        notification = db.query(Notification).filter(
            Notification.user_id == test_another_client_user.id
        ).first()
        assert notification is not None
        assert "invited" in notification.message.lower()

    def test_accepting_invitation_notifies_owner(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_client_user: User,
        test_another_client_user: User,
        db: Session
    ):
        """Test that accepting invitation notifies team owner."""
        from app.models.notification import Notification
        
        # Create team and invitation
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        invite_response = client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": test_another_client_user.email, "role": "member"},
            headers=client_auth_headers
        )
        token = invite_response.json()["invitation"]["token"]
        
        # Accept invitation
        client.post(
            f"/api/invitation/{token}/accept",
            headers=another_client_auth_headers
        )
        
        # Check owner received notification
        notifications = db.query(Notification).filter(
            Notification.user_id == test_client_user.id
        ).all()
        acceptance_notif = next((n for n in notifications if "joined" in n.message.lower()), None)
        assert acceptance_notif is not None
