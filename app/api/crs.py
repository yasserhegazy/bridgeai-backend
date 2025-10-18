from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.crs import CRSDocument
from app.schemas.project import ProjectOut
from pydantic import BaseModel


router = APIRouter()


class CRSCreate(BaseModel):
    project_id: int
    content: str
    summary_points: str = ""


@router.post("/", response_model=dict)
def create_crs(payload: CRSCreate, db: Session = Depends(get_db)):
    crs = CRSDocument(project_id=payload.project_id, created_by=1, content=payload.content, summary_points=payload.summary_points)
    db.add(crs)
    db.commit()
    db.refresh(crs)
    return {"id": crs.id, "status": crs.status.value}