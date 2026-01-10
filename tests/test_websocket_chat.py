import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.session_model import SessionModel, SessionStatus
from app.models.message import Message, SenderType
from app.models.team import Team, TeamMember
from app.core.security import create_access_token


@pytest.fixture
def websocket_test_data(db: Session, test_client_user: User):
    """Create test data for WebSocket tests."""
    # Create a team
    team = Team(name="WebSocket Test Team", created_by=test_client_user.id)
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Add user to team
    team_member = TeamMember(team_id=team.id, user_id=test_client_user.id, role="owner")
    db.add(team_member)
    db.commit()
    
    # Create a project
    project = Project(
        name="WebSocket Test Project",
        description="Test project for WebSocket",
        team_id=team.id,
        created_by=test_client_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create a chat session
    session = SessionModel(
        project_id=project.id,
        user_id=test_client_user.id,
        name="WebSocket Test Chat",
        status=SessionStatus.active
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return {
        "team": team,
        "project": project,
        "session": session,
        "user": test_client_user
    }


def test_websocket_connection_without_token(client: TestClient, websocket_test_data):
    """Test WebSocket connection fails without authentication token."""
    project_id = websocket_test_data["project"].id
    session_id = websocket_test_data["session"].id
    
    # Try to connect without token - should fail
    with pytest.raises(Exception):
        with client.websocket_connect(
            f"/api/projects/{project_id}/chats/{session_id}/ws"
        ):
            pass


def test_websocket_connection_with_valid_token(client: TestClient, websocket_test_data):
    """Test WebSocket connection succeeds with valid token."""
    user = websocket_test_data["user"]
    project_id = websocket_test_data["project"].id
    session_id = websocket_test_data["session"].id
    
    # Create access token
    token = create_access_token(data={"sub": str(user.id)})
    
    # Connect to WebSocket
    with client.websocket_connect(
        f"/api/projects/{project_id}/chats/{session_id}/ws?token={token}"
    ) as websocket:
        # Send a message
        message_data = {
            "content": "Hello from WebSocket test!",
            "sender_type": "client"
        }
        websocket.send_json(message_data)
        
        # Receive the broadcast message
        response = websocket.receive_json()
        
        assert response["content"] == "Hello from WebSocket test!"
        assert response["sender_type"] == "client"
        assert response["sender_id"] == user.id
        assert response["session_id"] == session_id
        assert "id" in response
        assert "timestamp" in response


def test_websocket_message_persistence(client: TestClient, websocket_test_data, db: Session):
    """Test that WebSocket messages are persisted to database."""
    user = websocket_test_data["user"]
    project_id = websocket_test_data["project"].id
    session_id = websocket_test_data["session"].id
    
    # Create access token
    token = create_access_token(data={"sub": str(user.id)})
    
    # Count messages before
    messages_before = db.query(Message).filter(
        Message.session_id == session_id
    ).count()
    
    # Connect and send message
    with client.websocket_connect(
        f"/api/projects/{project_id}/chats/{session_id}/ws?token={token}"
    ) as websocket:
        message_data = {
            "content": "Test message for persistence",
            "sender_type": "client"
        }
        websocket.send_json(message_data)
        websocket.receive_json()
    
    # Count messages after
    messages_after = db.query(Message).filter(
        Message.session_id == session_id
    ).count()
    
    # Verify message was saved
    assert messages_after == messages_before + 1
    
    # Verify message content
    saved_message = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.timestamp.desc()).first()
    
    assert saved_message.content == "Test message for persistence"
    assert saved_message.sender_type == SenderType.client
    assert saved_message.sender_id == user.id


def test_websocket_broadcast_to_multiple_clients(client: TestClient, websocket_test_data):
    """Test that messages are broadcast to all connected clients."""
    user = websocket_test_data["user"]
    project_id = websocket_test_data["project"].id
    session_id = websocket_test_data["session"].id
    
    # Create access token
    token = create_access_token(data={"sub": str(user.id)})
    
    # Connect two clients to the same session
    with client.websocket_connect(
        f"/api/projects/{project_id}/chats/{session_id}/ws?token={token}"
    ) as websocket1:
        with client.websocket_connect(
            f"/api/projects/{project_id}/chats/{session_id}/ws?token={token}"
        ) as websocket2:
            # Send message from first client
            message_data = {
                "content": "Broadcast test message",
                "sender_type": "client"
            }
            websocket1.send_json(message_data)
            
            # Both clients should receive the message
            response1 = websocket1.receive_json()
            response2 = websocket2.receive_json()
            
            assert response1["content"] == "Broadcast test message"
            assert response2["content"] == "Broadcast test message"
            assert response1["id"] == response2["id"]


def test_websocket_invalid_json(client: TestClient, websocket_test_data):
    """Test WebSocket handles invalid JSON gracefully."""
    user = websocket_test_data["user"]
    project_id = websocket_test_data["project"].id
    session_id = websocket_test_data["session"].id
    
    # Create access token
    token = create_access_token(data={"sub": str(user.id)})
    
    # Connect to WebSocket
    with client.websocket_connect(
        f"/api/projects/{project_id}/chats/{session_id}/ws?token={token}"
    ) as websocket:
        # Send invalid JSON
        websocket.send_text("invalid json {")
        
        # Should receive error message
        response = websocket.receive_json()
        assert "error" in response
        assert "Invalid JSON" in response["error"]


def test_websocket_invalid_sender_type(client: TestClient, websocket_test_data):
    """Test WebSocket validates sender_type."""
    user = websocket_test_data["user"]
    project_id = websocket_test_data["project"].id
    session_id = websocket_test_data["session"].id
    
    # Create access token
    token = create_access_token(data={"sub": str(user.id)})
    
    # Connect to WebSocket
    with client.websocket_connect(
        f"/api/projects/{project_id}/chats/{session_id}/ws?token={token}"
    ) as websocket:
        # Send message with invalid sender_type
        message_data = {
            "content": "Test message",
            "sender_type": "invalid_type"
        }
        websocket.send_json(message_data)
        
        # Should receive error message
        response = websocket.receive_json()
        assert "error" in response
        assert "Invalid sender_type" in response["error"]


def test_websocket_empty_content(client: TestClient, websocket_test_data, db: Session):
    """Test WebSocket ignores empty messages."""
    user = websocket_test_data["user"]
    project_id = websocket_test_data["project"].id
    session_id = websocket_test_data["session"].id
    
    # Create access token
    token = create_access_token(data={"sub": str(user.id)})
    
    # Count messages before
    messages_before = db.query(Message).filter(
        Message.session_id == session_id
    ).count()
    
    # Connect and send empty message
    with client.websocket_connect(
        f"/api/projects/{project_id}/chats/{session_id}/ws?token={token}"
    ) as websocket:
        message_data = {
            "content": "   ",
            "sender_type": "client"
        }
        websocket.send_json(message_data)
        
        # Give it a moment to process
        import time
        time.sleep(0.1)
    
    # Count messages after
    messages_after = db.query(Message).filter(
        Message.session_id == session_id
    ).count()
    
    # Verify no message was saved
    assert messages_after == messages_before


def test_websocket_unauthorized_project_access(client: TestClient, websocket_test_data, db: Session):
    """Test WebSocket denies access to unauthorized projects."""
    # Create another user not in the team
    unauthorized_user = User(
        full_name="Unauthorized User",
        email="unauthorized@test.com",
        password_hash="hash",
        role=UserRole.client
    )
    db.add(unauthorized_user)
    db.commit()
    db.refresh(unauthorized_user)
    
    project_id = websocket_test_data["project"].id
    session_id = websocket_test_data["session"].id
    
    # Create token for unauthorized user
    token = create_access_token(data={"sub": str(unauthorized_user.id)})
    
    # Try to connect - should fail
    with pytest.raises(Exception):
        with client.websocket_connect(
            f"/api/projects/{project_id}/chats/{session_id}/ws?token={token}"
        ):
            pass
