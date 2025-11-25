"""
Tests for notification functionality.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.models.user import User


class TestNotificationRetrieval:
    """Test retrieving notifications."""

    def test_get_notifications_empty(
        self,
        client: TestClient,
        client_auth_headers: dict
    ):
        """Test getting notifications when none exist."""
        response = client.get("/api/notifications/", headers=client_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["unread_count"] == 0
        assert len(data["notifications"]) == 0

    def test_get_notifications_with_data(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_client_user: User,
        db: Session
    ):
        """Test getting notifications when they exist."""
        # Create notifications
        notif1 = Notification(
            user_id=test_client_user.id,
            type=NotificationType.PROJECT_APPROVAL,
            reference_id=1,
            title="Test Notification 1",
            message="First notification",
            is_read=False
        )
        notif2 = Notification(
            user_id=test_client_user.id,
            type=NotificationType.TEAM_INVITATION,
            reference_id=2,
            title="Test Notification 2",
            message="Second notification",
            is_read=True
        )
        db.add_all([notif1, notif2])
        db.commit()
        
        # Get notifications
        response = client.get("/api/notifications/", headers=client_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert data["unread_count"] == 1
        assert len(data["notifications"]) == 2

    def test_get_unread_notifications_only(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_client_user: User,
        db: Session
    ):
        """Test filtering for unread notifications only."""
        # Create notifications
        notif1 = Notification(
            user_id=test_client_user.id,
            type=NotificationType.PROJECT_APPROVAL,
            reference_id=1,
            title="Unread",
            message="Unread notification",
            is_read=False
        )
        notif2 = Notification(
            user_id=test_client_user.id,
            type=NotificationType.TEAM_INVITATION,
            reference_id=2,
            title="Read",
            message="Read notification",
            is_read=True
        )
        db.add_all([notif1, notif2])
        db.commit()
        
        # Get unread only
        response = client.get(
            "/api/notifications/?unread_only=true",
            headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["title"] == "Unread"

    def test_notifications_are_user_specific(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_client_user: User,
        test_another_client_user: User,
        db: Session
    ):
        """Test that users only see their own notifications."""
        # Create notifications for different users
        notif1 = Notification(
            user_id=test_client_user.id,
            type=NotificationType.PROJECT_APPROVAL,
            reference_id=1,
            title="User 1 Notification",
            message="For user 1",
            is_read=False
        )
        notif2 = Notification(
            user_id=test_another_client_user.id,
            type=NotificationType.TEAM_INVITATION,
            reference_id=2,
            title="User 2 Notification",
            message="For user 2",
            is_read=False
        )
        db.add_all([notif1, notif2])
        db.commit()
        
        # User 1 gets their notifications
        response1 = client.get("/api/notifications/", headers=client_auth_headers)
        data1 = response1.json()
        assert len(data1["notifications"]) == 1
        assert data1["notifications"][0]["title"] == "User 1 Notification"
        
        # User 2 gets their notifications
        response2 = client.get("/api/notifications/", headers=another_client_auth_headers)
        data2 = response2.json()
        assert len(data2["notifications"]) == 1
        assert data2["notifications"][0]["title"] == "User 2 Notification"


class TestMarkNotificationAsRead:
    """Test marking notifications as read."""

    def test_mark_single_notification_as_read(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_client_user: User,
        db: Session
    ):
        """Test marking a single notification as read."""
        # Create unread notification
        notif = Notification(
            user_id=test_client_user.id,
            type=NotificationType.PROJECT_APPROVAL,
            reference_id=1,
            title="Test",
            message="Test notification",
            is_read=False
        )
        db.add(notif)
        db.commit()
        notif_id = notif.id
        
        # Mark as read
        response = client.patch(
            f"/api/notifications/{notif_id}/read",
            headers=client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_read"] is True
        assert data["id"] == notif_id

    def test_mark_all_notifications_as_read(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_client_user: User,
        db: Session
    ):
        """Test marking all notifications as read."""
        # Create multiple unread notifications
        notif1 = Notification(
            user_id=test_client_user.id,
            type=NotificationType.PROJECT_APPROVAL,
            reference_id=1,
            title="Test 1",
            message="Test notification 1",
            is_read=False
        )
        notif2 = Notification(
            user_id=test_client_user.id,
            type=NotificationType.TEAM_INVITATION,
            reference_id=2,
            title="Test 2",
            message="Test notification 2",
            is_read=False
        )
        db.add_all([notif1, notif2])
        db.commit()
        
        # Mark all as read
        response = client.patch(
            "/api/notifications/read-all",
            headers=client_auth_headers
        )
        assert response.status_code == 200
        
        # Verify all are read
        get_response = client.get("/api/notifications/", headers=client_auth_headers)
        data = get_response.json()
        assert data["unread_count"] == 0
        for notif in data["notifications"]:
            assert notif["is_read"] is True

    def test_cannot_mark_other_users_notification(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_another_client_user: User,
        db: Session
    ):
        """Test that users cannot mark other users' notifications."""
        # Create notification for user 2
        notif = Notification(
            user_id=test_another_client_user.id,
            type=NotificationType.PROJECT_APPROVAL,
            reference_id=1,
            title="Test",
            message="Test notification",
            is_read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        
        # User 1 tries to mark it as read
        response = client.patch(
            f"/api/notifications/{notif.id}/read",
            headers=client_auth_headers
        )
        assert response.status_code == 404


class TestDeleteNotification:
    """Test deleting notifications."""

    def test_delete_notification(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_client_user: User,
        db: Session
    ):
        """Test deleting a notification."""
        # Create notification
        notif = Notification(
            user_id=test_client_user.id,
            type=NotificationType.PROJECT_APPROVAL,
            reference_id=1,
            title="Test",
            message="Test notification",
            is_read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        
        # Delete notification
        response = client.delete(
            f"/api/notifications/{notif.id}",
            headers=client_auth_headers
        )
        assert response.status_code == 200
        
        # Verify deletion
        get_response = client.get("/api/notifications/", headers=client_auth_headers)
        data = get_response.json()
        assert data["total_count"] == 0

    def test_cannot_delete_other_users_notification(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_another_client_user: User,
        db: Session
    ):
        """Test that users cannot delete other users' notifications."""
        # Create notification for user 2
        notif = Notification(
            user_id=test_another_client_user.id,
            type=NotificationType.PROJECT_APPROVAL,
            reference_id=1,
            title="Test",
            message="Test notification",
            is_read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        
        # User 1 tries to delete it
        response = client.delete(
            f"/api/notifications/{notif.id}",
            headers=client_auth_headers
        )
        assert response.status_code == 404


class TestNotificationMetadata:
    """Test notification metadata enrichment."""

    def test_project_approval_notification_has_metadata(
        self,
        client: TestClient,
        ba_auth_headers: dict,
        client_auth_headers: dict,
        test_client_user: User,
        db: Session
    ):
        """Test that project approval notifications include project metadata."""
        # Create team with both users
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=ba_auth_headers
        )
        team_id = team_response.json()["id"]
        
        client.post(
            f"/api/teams/{team_id}/members",
            json={"user_id": test_client_user.id, "role": "member"},
            headers=ba_auth_headers
        )
        
        # Client creates project (pending)
        project_response = client.post(
            "/api/projects/",
            json={"name": "Test Project", "description": "Test", "team_id": team_id},
            headers=client_auth_headers
        )
        project_id = project_response.json()["id"]
        
        # BA approves project (creates notification)
        client.put(
            f"/api/projects/{project_id}/approve",
            headers=ba_auth_headers
        )
        
        # Check notification has metadata
        response = client.get("/api/notifications/", headers=client_auth_headers)
        data = response.json()
        assert len(data["notifications"]) >= 1
        
        approval_notif = next((n for n in data["notifications"] if "approved" in n["message"].lower()), None)
        assert approval_notif is not None
        assert approval_notif["metadata"] is not None
        assert approval_notif["metadata"]["project_id"] == project_id
        assert approval_notif["metadata"]["project_name"] == "Test Project"

    def test_team_invitation_notification_has_metadata(
        self,
        client: TestClient,
        client_auth_headers: dict,
        test_another_client_user: User,
        db: Session
    ):
        """Test that team invitation notifications include team metadata."""
        # Create team
        team_response = client.post(
            "/api/teams/",
            json={"name": "Test Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        # Send invitation to existing user
        client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": test_another_client_user.email, "role": "member"},
            headers=client_auth_headers
        )
        
        # Check notification has metadata
        from app.models.notification import Notification
        notification = db.query(Notification).filter(
            Notification.user_id == test_another_client_user.id
        ).first()
        assert notification is not None
        
        # Get through API to check enriched metadata
        from tests.conftest import TestingSessionLocal
        from app.api.notifications import enrich_notification
        enriched = enrich_notification(notification, db)
        assert enriched["metadata"] is not None
        assert enriched["metadata"]["team_id"] == team_id
        assert enriched["metadata"]["team_name"] == "Test Team"


class TestAcceptInvitationFromNotification:
    """Test accepting invitations directly from notifications."""

    def test_accept_invitation_from_notification(
        self,
        client: TestClient,
        client_auth_headers: dict,
        another_client_auth_headers: dict,
        test_client_user: User,
        test_another_client_user: User,
        db: Session
    ):
        """Test accepting an invitation via notification endpoint."""
        # Create team and send invitation
        team_response = client.post(
            "/api/teams/",
            json={"name": "Team", "description": "Test"},
            headers=client_auth_headers
        )
        team_id = team_response.json()["id"]
        
        client.post(
            f"/api/teams/{team_id}/invite",
            json={"email": test_another_client_user.email, "role": "member"},
            headers=client_auth_headers
        )
        
        # Get notification
        notif_response = client.get("/api/notifications/", headers=another_client_auth_headers)
        notifications = notif_response.json()["notifications"]
        invitation_notif = next((n for n in notifications if "invited" in n["message"].lower()), None)
        assert invitation_notif is not None
        
        # Accept invitation via notification
        response = client.post(
            f"/api/notifications/{invitation_notif['id']}/accept-invitation",
            headers=another_client_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Invitation accepted successfully"
        assert data["team_id"] == team_id
        
        # Verify notification is marked as read
        notif_check = client.get("/api/notifications/", headers=another_client_auth_headers)
        updated_notif = next(
            (n for n in notif_check.json()["notifications"] if n["id"] == invitation_notif["id"]),
            None
        )
        assert updated_notif["is_read"] is True
