from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectOut
from app.models.project import Project
from app.models.team import Team, TeamMember
from app.models.user import User
from app.core.security import get_current_user


router = APIRouter()


@router.post("/", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project. User must be a member of the specified team."""
    # Check if team exists
    team = db.query(Team).filter(Team.id ==uvipayload.team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Check if user is a member of the team
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == payload.team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You must be a member of this team to create projects."
        )
    
    # Check if project name already exists in this team
    existing_project = db.query(Project).filter(
        Project.name == payload.name,
        Project.team_id == payload.team_id
    ).first()
    
    if existing_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A project with this name already exists in this team"
        )
    
    project = Project(
        name=payload.name, 
        description=payload.description, 
        team_id=payload.team_id,
        created_by=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get project details. Only team members can view projects."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    # Check if user is a member of the project's team
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == project.team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You must be a member of this project's team to view it."
        )
    
    return project