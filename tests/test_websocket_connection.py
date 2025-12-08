#!/usr/bin/env python3
"""
Simple script to test WebSocket connection with proper authentication.
Run this after starting the server with: uvicorn app.main:app --reload
"""
import asyncio
import json
import requests
import websockets
from datetime import datetime

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

def print_step(step, message):
    """Print formatted step message"""
    print(f"\n{'='*60}")
    print(f"STEP {step}: {message}")
    print('='*60)

def main():
    print("\n🚀 WebSocket Connection Test Script")
    print("="*60)
    
    # Step 1: Use provided token
    print_step(1, "Authentication")
    
    # Use the token you provided
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwicm9sZSI6ImJhIiwiZXhwIjoxNzY1MTk2OTkyfQ.E5eXq_csfXusglOpUavE_ss1kIb5bgXovYvbbrWCUMw"
    
    print("✅ Using provided token")
    print(f"Token: {token[:50]}...")
    print(f"Role: ba")
    print(f"User ID: 1")
    
    # Step 2: Get or create a team
    print_step(2, "Get Teams")
    
    headers = {"Authorization": f"Bearer {token}"}
    teams_response = requests.get(f"{BASE_URL}/api/teams", headers=headers)
    
    if teams_response.status_code == 200:
        teams = teams_response.json()
        print(f"✅ Found {len(teams)} team(s)")
        
        if not teams:
            print("\n💡 Creating a new team...")
            team_data = {"name": "WebSocket Test Team"}
            create_team_response = requests.post(
                f"{BASE_URL}/api/teams",
                json=team_data,
                headers=headers
            )
            if create_team_response.status_code in [200, 201]:
                team = create_team_response.json()
                team_id = team["id"]
                print(f"✅ Team created with ID: {team_id}")
            else:
                print(f"❌ Failed to create team: {create_team_response.status_code}")
                print(f"Response: {create_team_response.text}")
                return
        else:
            team_id = teams[0]["id"]
            print(f"✅ Using team ID: {team_id}")
    else:
        print(f"❌ Failed to get teams: {teams_response.text}")
        return
    
    # Step 3: Get or create a project
    print_step(3, "Get Projects")
    
    projects_response = requests.get(f"{BASE_URL}/api/teams/{team_id}/projects", headers=headers)
    
    if projects_response.status_code == 200:
        projects = projects_response.json()
        print(f"✅ Found {len(projects)} project(s)")
        
        if not projects:
            print("\n💡 Creating a new project...")
            project_data = {
                "name": "WebSocket Test Project",
                "description": "Testing WebSocket connections",
                "team_id": team_id
            }
            create_project_response = requests.post(
                f"{BASE_URL}/api/projects/",
                json=project_data,
                headers=headers
            )
            if create_project_response.status_code in [200, 201]:
                project = create_project_response.json()
                project_id = project["id"]
                print(f"✅ Project created with ID: {project_id}")
            else:
                print(f"❌ Failed to create project: {create_project_response.status_code}")
                print(f"Response: {create_project_response.text}")
                return
        else:
            project_id = projects[0]["id"]
            print(f"✅ Using project ID: {project_id}")
    else:
        print(f"❌ Failed to get projects: {projects_response.text}")
        return
    
    # Step 4: Get or create a chat session
    print_step(4, "Get Chat Sessions")
    
    chats_response = requests.get(
        f"{BASE_URL}/api/projects/{project_id}/chats",
        headers=headers
    )
    
    if chats_response.status_code == 200:
        chats = chats_response.json()
        print(f"✅ Found {len(chats)} chat(s)")
        
        if not chats:
            print("\n💡 Creating a new chat session...")
            chat_data = {"name": "WebSocket Test Chat"}
            create_chat_response = requests.post(
                f"{BASE_URL}/api/projects/{project_id}/chats",
                json=chat_data,
                headers=headers
            )
            if create_chat_response.status_code in [200, 201]:
                chat = create_chat_response.json()
                chat_id = chat["id"]
                print(f"✅ Chat created with ID: {chat_id}")
            else:
                print(f"❌ Failed to create chat: {create_chat_response.status_code}")
                print(f"Response: {create_chat_response.text}")
                return
        else:
            chat_id = chats[0]["id"]
            print(f"✅ Using chat ID: {chat_id}")
    else:
        print(f"❌ Failed to get chats: {chats_response.text}")
        return
    
    # Step 5: Connect to WebSocket
    print_step(5, "WebSocket Connection")
    
    ws_url = f"{WS_URL}/api/projects/{project_id}/chats/{chat_id}/ws?token={token}"
    print(f"Connecting to: {ws_url[:80]}...")
    
    asyncio.run(test_websocket(ws_url))

async def test_websocket(ws_url):
    """Test WebSocket connection"""
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Send a test message
            print("\n📤 Sending test message...")
            test_message = {
                "content": f"Test message at {datetime.now().isoformat()}",
                "sender_type": "client"
            }
            await websocket.send(json.dumps(test_message))
            print(f"Sent: {test_message}")
            
            # Receive response
            print("\n📥 Waiting for response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            message = json.loads(response)
            
            if "error" in message:
                print(f"❌ Error received: {message['error']}")
            else:
                print(f"✅ Message received successfully!")
                print(f"   ID: {message['id']}")
                print(f"   Content: {message['content']}")
                print(f"   Sender: {message['sender_type']}")
                print(f"   Timestamp: {message['timestamp']}")
            
            # Send another message
            print("\n📤 Sending another message...")
            message2 = {
                "content": "Second test message - WebSocket is working! 🎉",
                "sender_type": "client"
            }
            await websocket.send(json.dumps(message2))
            
            response2 = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            message2_data = json.loads(response2)
            print(f"✅ Second message received: ID {message2_data['id']}")
            
            print("\n" + "="*60)
            print("🎉 WebSocket test completed successfully!")
            print("="*60)
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed with status: {e.status_code}")
        if e.status_code == 403:
            print("💡 This usually means authentication failed or access denied")
        elif e.status_code == 404:
            print("💡 WebSocket endpoint not found - check the URL")
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for response")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
