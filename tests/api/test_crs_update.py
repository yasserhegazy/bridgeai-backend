from unittest.mock import MagicMock, patch

import pytest
from fastapi import status

from app.models.crs import CRSDocument, CRSStatus
from app.schemas.crs import CRSContentUpdate

def test_update_crs_content(client, db, client_token, client_user):
    # 1. Setup: Create team, project, and CRS
    from app.models.team import Team, TeamMember
    from app.models.project import Project, ProjectStatus
    
    # Create team
    team = Team(name="Test Team", created_by=client_user.id)
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Add client_user as team member
    member = TeamMember(team_id=team.id, user_id=client_user.id)
    db.add(member)
    db.commit()
    
    # Create project
    project = Project(
        name="Test Project",
        description="Test project",
        team_id=team.id,
        created_by=client_user.id,
        status=ProjectStatus.active.value,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Create CRS
    crs = CRSDocument(
        project_id=project.id,
        created_by=client_user.id,
        content='{"project_title": "Test Project"}',
        status=CRSStatus.draft,
        version=1,
        edit_version=1
    )
    db.add(crs)
    db.commit()
    db.refresh(crs)

    # 2. Update content successfully
    new_content = '{"project_title": "Updated Project", "description": "New description"}'
    
    headers = {"Authorization": f"Bearer {client_token}"}
    response = client.put(
        f"/api/crs/{crs.id}/content",
        json={
            "content": new_content,
            "expected_version": 1
        },
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["content"] == new_content
    assert data["edit_version"] == 2
    
    # Verify DB update
    db.refresh(crs)
    assert crs.content == new_content
    assert crs.edit_version == 2

def test_update_crs_content_conflict(client, db, client_token, client_user):
    # 1. Setup
    from app.models.team import Team, TeamMember
    from app.models.project import Project, ProjectStatus
    
    team = Team(name="Test Team 2", created_by=client_user.id)
    db.add(team)
    db.commit()
    
    member = TeamMember(team_id=team.id, user_id=client_user.id)
    db.add(member)
    db.commit()
    
    project = Project(
        name="Test Project 2",
        description="Test",
        team_id=team.id,
        created_by=client_user.id,
        status=ProjectStatus.active.value,
    )
    db.add(project)
    db.commit()
    
    crs = CRSDocument(
        project_id=project.id,
        created_by=client_user.id,
        content='{}',
        status=CRSStatus.draft,
        version=1,
        edit_version=5
    )
    db.add(crs)
    db.commit()

    # 2. Try to update with WRONG version
    headers = {"Authorization": f"Bearer {client_token}"}
    response = client.put(
        f"/api/crs/{crs.id}/content",
        json={
            "content": '{}',
            "edit_version": 1 # Expecting 1, actual is 5
        },
        headers=headers
    )
    
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "modified by another user" in response.json()["detail"]

def test_update_crs_approved_fails(client, db, client_token, client_user):
    # 1. Setup
    from app.models.team import Team, TeamMember
    from app.models.project import Project, ProjectStatus
    
    team = Team(name="Test Team 3", created_by=client_user.id)
    db.add(team)
    db.commit()
    
    member = TeamMember(team_id=team.id, user_id=client_user.id)
    db.add(member)
    db.commit()
    
    project = Project(
        name="Test Project 3",
        description="Test",
        team_id=team.id,
        created_by=client_user.id,
        status=ProjectStatus.active.value,
    )
    db.add(project)
    db.commit()
    
    crs = CRSDocument(
        project_id=project.id,
        created_by=client_user.id,
        content='{}',
        status=CRSStatus.approved, # APPROVED
        version=1,
        edit_version=1
    )
    db.add(crs)
    db.commit()

    # 2. Try to update an approved CRS
    headers = {"Authorization": f"Bearer {client_token}"}
    response = client.put(
        f"/api/crs/{crs.id}/content",
        json={
            "content": '{}',
            "expected_version": 1
        },
        headers=headers
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot edit an approved CRS" in response.json()["detail"]
