from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectOut
from app.models.project import Project
from app.models.user import User
from app.core.security import get_current_user, require_ba


router = APIRouter()


@router.post("/", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ba)  # Only BA can create projects
):
    project = Project(name=payload.name, description=payload.description, created_by=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Any authenticated user can view
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project