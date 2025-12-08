from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from typing import List, Dict
from datetime import datetime
import json
from app.db.session import get_db
from app.core.security import get_current_user, decode_access_token
from app.models.user import User
from app.models.session_model import SessionModel, SessionStatus
from app.models.message import Message, SenderType
from app.schemas.chat import (
    SessionCreate,
    SessionOut,
    SessionUpdate,
    SessionListOut,
    MessageOut
)
# Import helper functions from projects API
from app.api.projects import get_project_or_404, verify_team_membership

router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        # Store active connections per session
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast_to_session(self, message: dict, session_id: int):
        if session_id in self.active_connections:
            message_json = json.dumps(message)
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(message_json)
                except:
                    pass

manager = ConnectionManager()


# ==================== CRUD Endpoints ====================

@router.get('/{project_id}/chats', response_model=List[SessionListOut])
def get_project_chats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all chat sessions for a specific project."""
    # Get project and verify access
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)
    
    # Get all sessions for the project with message count
    sessions = db.query(
        SessionModel,
        func.count(Message.id).label('message_count')
    ).outerjoin(
        Message, SessionModel.id == Message.session_id
    ).filter(
        SessionModel.project_id == project_id
    ).group_by(
        SessionModel.id
    ).order_by(
        desc(SessionModel.started_at)
    ).all()
    
    # Format response
    result = []
    for session, message_count in sessions:
        result.append(SessionListOut(
            id=session.id,
            project_id=session.project_id,
            user_id=session.user_id,
            name=session.name,
            status=session.status,
            started_at=session.started_at,
            ended_at=session.ended_at,
            message_count=message_count
        ))
    
    return result


@router.post('/{project_id}/chats', response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_project_chat(
    project_id: int,
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat session for a project."""
    # Get project and verify access
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)
    
    # Create new session
    new_session = SessionModel(
        project_id=project_id,
        user_id=current_user.id,
        name=session_data.name,
        status=SessionStatus.active
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    # Return session with empty messages list
    return SessionOut(
        id=new_session.id,
        project_id=new_session.project_id,
        user_id=new_session.user_id,
        name=new_session.name,
        status=new_session.status,
        started_at=new_session.started_at,
        ended_at=new_session.ended_at,
        messages=[]
    )


@router.get('/{project_id}/chats/{chat_id}', response_model=SessionOut)
def get_project_chat(
    project_id: int,
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chat session by its ID with all messages."""
    # Get project and verify access
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)
    
    # Get session and verify it belongs to this project
    session = db.query(SessionModel).options(
        joinedload(SessionModel.messages)
    ).filter(
        SessionModel.id == chat_id,
        SessionModel.project_id == project_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found in this project"
        )
    
    return session


@router.put('/{project_id}/chats/{chat_id}', response_model=SessionOut)
def update_project_chat(
    project_id: int,
    chat_id: int,
    session_update: SessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a chat session status."""
    # Get project and verify access
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)
    
    # Get session and verify it belongs to this project
    session = db.query(SessionModel).filter(
        SessionModel.id == chat_id,
        SessionModel.project_id == project_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found in this project"
        )
    
    # Update session fields
    if session_update.name is not None:
        session.name = session_update.name

    if session_update.status is not None:
        session.status = session_update.status
        
        # If marking as completed, set ended_at timestamp
        if session_update.status == SessionStatus.completed and not session.ended_at:
            session.ended_at = func.now()
    
    db.commit()
    db.refresh(session)
    
    # Get session with messages
    session_with_messages = db.query(SessionModel).options(
        joinedload(SessionModel.messages)
    ).filter(
        SessionModel.id == chat_id
    ).first()
    
    return session_with_messages


@router.delete('/{project_id}/chats/{chat_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_project_chat(
    project_id: int,
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat session and all its messages."""
    # Get project and verify access
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)
    
    # Get session and verify it belongs to this project
    session = db.query(SessionModel).filter(
        SessionModel.id == chat_id,
        SessionModel.project_id == project_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found in this project"
        )
    
    # Delete all messages first
    db.query(Message).filter(Message.session_id == chat_id).delete()
    
    # Delete the session
    db.delete(session)
    db.commit()
    
    return None


# ==================== WebSocket Endpoint ====================

@router.websocket('/{project_id}/chats/{chat_id}/ws')
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: int,
    chat_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat communication.
    
    Client should connect with: ws://host/api/projects/{project_id}/chats/{chat_id}/ws?token={access_token}
    
    Message format (from client):
    {
        "content": "message content",
        "sender_type": "client" | "ba"
    }
    
    Message format (to client):
    {
        "id": 123,
        "session_id": 1,
        "sender_type": "client" | "ai" | "ba",
        "sender_id": 1,
        "content": "message content",
        "timestamp": "2025-12-08T10:30:00Z"
    }
    """
    
    # Authenticate user via token
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=1008, reason="Invalid authentication token")
            return
        
        # Get user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            await websocket.close(code=1008, reason="User not found")
            return
    except Exception as e:
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Verify project access
    try:
        project = get_project_or_404(db, project_id)
        verify_team_membership(db, project.team_id, user.id)
    except HTTPException:
        await websocket.close(code=1008, reason="Access denied to project")
        return
    
    # Verify session exists and belongs to project
    session = db.query(SessionModel).filter(
        SessionModel.id == chat_id,
        SessionModel.project_id == project_id
    ).first()
    
    if not session:
        await websocket.close(code=1008, reason="Chat session not found")
        return
    
    # Connect to WebSocket
    await manager.connect(websocket, chat_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                content = message_data.get("content", "").strip()
                sender_type_str = message_data.get("sender_type", "client")
                
                if not content:
                    continue
                
                # Validate sender_type
                try:
                    sender_type = SenderType[sender_type_str]
                except KeyError:
                    await websocket.send_text(json.dumps({
                        "error": f"Invalid sender_type: {sender_type_str}"
                    }))
                    continue
                
                # Save message to database
                new_message = Message(
                    session_id=chat_id,
                    sender_type=sender_type,
                    sender_id=user.id,
                    content=content
                )
                
                db.add(new_message)
                db.commit()
                db.refresh(new_message)
                
                # Broadcast message to all connected clients in this session
                message_response = {
                    "id": new_message.id,
                    "session_id": new_message.session_id,
                    "sender_type": new_message.sender_type.value,
                    "sender_id": new_message.sender_id,
                    "content": new_message.content,
                    "timestamp": new_message.timestamp.isoformat()
                }
                
                await manager.broadcast_to_session(message_response, chat_id)
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "error": "Invalid JSON format"
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "error": f"Error processing message: {str(e)}"
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)
    except Exception as e:
        manager.disconnect(websocket, chat_id)
