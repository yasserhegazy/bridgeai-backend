import json
from typing import List, Optional
from datetime import datetime
import io

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.projects import get_project_or_404, verify_team_membership
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.crs import CRSDocument, CRSStatus
from app.models.user import User
from app.services.crs_service import get_latest_crs, persist_crs_document, get_crs_versions, update_crs_status, get_crs_by_id
from app.schemas.export import ExportFormat
from app.services.export_service import (
    crs_to_professional_html,
    html_to_pdf_bytes,
    export_markdown_bytes,
)


router = APIRouter()


class CRSCreate(BaseModel):
    project_id: int
    content: str
    summary_points: List[str] = Field(default_factory=list)


class CRSStatusUpdate(BaseModel):
    """Schema for updating CRS status (approval workflow)."""
    status: str = Field(..., description="New status: draft, under_review, approved, rejected")


class CRSOut(BaseModel):
    id: int
    project_id: int
    status: str
    version: int
    content: str
    summary_points: List[str]
    created_by: Optional[int] = None
    approved_by: Optional[int] = None
    created_at: datetime

    class Config:
        orm_mode = True


@router.post("/", response_model=CRSOut, status_code=status.HTTP_201_CREATED)
def create_crs(
    payload: CRSCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create and persist a CRS document for a project.
    """
    project = get_project_or_404(db, payload.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    crs = persist_crs_document(
        db,
        project_id=payload.project_id,
        created_by=current_user.id,
        content=payload.content,
        summary_points=payload.summary_points,
    )

    return CRSOut(
        id=crs.id,
        project_id=crs.project_id,
        status=crs.status.value,
        version=crs.version,
        content=crs.content,
        summary_points=payload.summary_points,
        created_by=crs.created_by,
        approved_by=crs.approved_by,
        created_at=crs.created_at,
    )


@router.get("/latest", response_model=Optional[CRSOut])
def read_latest_crs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch the most recent CRS for a project.
    """
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    crs = get_latest_crs(db, project_id=project_id)
    if not crs:
        return None

    try:
        summary_points = json.loads(crs.summary_points) if crs.summary_points else []
    except Exception:
        summary_points = []

    return CRSOut(
        id=crs.id,
        project_id=crs.project_id,
        status=crs.status.value,
        version=crs.version,
        content=crs.content,
        summary_points=summary_points,
        created_by=crs.created_by,
        approved_by=crs.approved_by,
        created_at=crs.created_at,
    )


@router.get("/versions", response_model=List[CRSOut])
def read_crs_versions(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch all CRS versions for a project, ordered by version descending (newest first).
    """
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    versions = get_crs_versions(db, project_id=project_id)
    result = []
    for crs in versions:
        try:
            summary_points = json.loads(crs.summary_points) if crs.summary_points else []
        except Exception:
            summary_points = []
        result.append(CRSOut(
            id=crs.id,
            project_id=crs.project_id,
            status=crs.status.value,
            version=crs.version,
            content=crs.content,
            summary_points=summary_points,
            created_by=crs.created_by,
            approved_by=crs.approved_by,
            created_at=crs.created_at,
        ))
    return result


@router.get("/{crs_id}", response_model=CRSOut)
def read_crs(
    crs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch a specific CRS document version by its unique ID.
    """
    crs = get_crs_by_id(db, crs_id=crs_id)
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CRS document not found"
        )
    
    project = get_project_or_404(db, crs.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    try:
        summary_points = json.loads(crs.summary_points) if crs.summary_points else []
    except Exception:
        summary_points = []
    
    return CRSOut(
        id=crs.id,
        project_id=crs.project_id,
        status=crs.status.value,
        version=crs.version,
        content=crs.content,
        summary_points=summary_points,
        created_by=crs.created_by,
        approved_by=crs.approved_by,
        created_at=crs.created_at,
    )


@router.put("/{crs_id}/status", response_model=CRSOut)
def update_crs_status_endpoint(
    crs_id: int,
    payload: CRSStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the status of a CRS document (approval workflow).
    
    Status transitions:
    - draft -> under_review (Client submits for review)
    - under_review -> approved/rejected (BA reviews)
    - rejected -> draft (Client revises)
    """
    # Validate status value
    try:
        new_status = CRSStatus(payload.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {[s.value for s in CRSStatus]}"
        )

    # Get CRS and verify access
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CRS document not found"
        )

    project = get_project_or_404(db, crs.project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    # Update status using service function
    updated_crs = update_crs_status(
        db,
        crs_id=crs_id,
        new_status=new_status,
        approved_by=current_user.id if new_status == CRSStatus.approved else None,
    )

    try:
        summary_points = json.loads(updated_crs.summary_points) if updated_crs.summary_points else []
    except Exception:
        summary_points = []

    return CRSOut(
        id=updated_crs.id,
        project_id=updated_crs.project_id,
        status=updated_crs.status.value,
        version=updated_crs.version,
        content=updated_crs.content,
        summary_points=summary_points,
        created_by=updated_crs.created_by,
        approved_by=updated_crs.approved_by,
        created_at=updated_crs.created_at,
    )

@router.post("/{crs_id}/export")
def export_crs(
    crs_id: int,
    format: ExportFormat = Query(ExportFormat.pdf),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export a CRS document as PDF or Markdown with professional formatting.
    
    PDF exports include a professional corporate document header and styling.
    """
    # Get CRS document
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CRS document not found"
        )
    
    # Verify access
    project = get_project_or_404(db, crs.project_id)
    verify_team_membership(db, project.team_id, current_user.id)
    
    filename = f"crs-v{crs.version}.{format.value}"
    
    # If CRS content is JSON, convert to markdown
    import json
    def crs_json_to_markdown(crs_json):
        md = []
        md.append(f"# {crs_json.get('project_title', 'CRS Document')}")
        md.append("\n---\n")
        if crs_json.get('project_description'):
            md.append(f"**Description:** {crs_json['project_description']}\n")
        if crs_json.get('project_objectives'):
            md.append("## Objectives\n" + "\n".join(f"- {o}" for o in crs_json['project_objectives']) + "\n")
        if crs_json.get('target_users'):
            md.append(f"**Target Users:** {', '.join(crs_json['target_users'])}\n")
        if crs_json.get('stakeholders'):
            md.append(f"**Stakeholders:** {', '.join(crs_json['stakeholders'])}\n")
        md.append("\n---\n")
        if crs_json.get('functional_requirements'):
            md.append("## Functional Requirements\n")
            for fr in crs_json['functional_requirements']:
                md.append(f"- **{fr['id']} {fr['title']}** ({fr['priority']}): {fr['description']}")
        md.append("\n---\n")
        if crs_json.get('performance_requirements'):
            md.append("## Performance Requirements\n" + "\n".join(f"- {p}" for p in crs_json['performance_requirements']) + "\n")
        if crs_json.get('security_requirements'):
            md.append("## Security Requirements\n" + "\n".join(f"- {s}" for s in crs_json['security_requirements']) + "\n")
        if crs_json.get('scalability_requirements'):
            md.append("## Scalability Requirements\n" + "\n".join(f"- {s}" for s in crs_json['scalability_requirements']) + "\n")
        md.append("\n---\n")
        if crs_json.get('technology_stack'):
            md.append("## Technology Stack\n")
            for k, v in crs_json['technology_stack'].items():
                md.append(f"- **{k.capitalize()}**: {', '.join(v)}")
        if crs_json.get('integrations'):
            md.append(f"**Integrations:** {', '.join(crs_json['integrations'])}\n")
        if crs_json.get('budget_constraints'):
            md.append(f"**Budget:** {crs_json['budget_constraints']}\n")
        if crs_json.get('timeline_constraints'):
            md.append(f"**Timeline:** {crs_json['timeline_constraints']}\n")
        if crs_json.get('technical_constraints'):
            md.append(f"**Technical Constraints:** {', '.join(crs_json['technical_constraints'])}\n")
        md.append("\n---\n")
        if crs_json.get('success_metrics'):
            md.append("## Success Metrics\n" + "\n".join(f"- {m}" for m in crs_json['success_metrics']) + "\n")
        if crs_json.get('acceptance_criteria'):
            md.append("## Acceptance Criteria\n" + "\n".join(f"- {a}" for a in crs_json['acceptance_criteria']) + "\n")
        if crs_json.get('assumptions'):
            md.append(f"**Assumptions:** {', '.join(crs_json['assumptions'])}\n")
        if crs_json.get('risks'):
            md.append(f"**Risks:** {', '.join(crs_json['risks'])}\n")
        if crs_json.get('out_of_scope'):
            md.append(f"**Out of Scope:** {', '.join(crs_json['out_of_scope'])}\n")
        md.append("\n---\n")
        return "\n".join(md)

    content = crs.content or ""
    try:
        crs_json = json.loads(content)
        markdown_content = crs_json_to_markdown(crs_json)
    except Exception:
        markdown_content = content

    if format == ExportFormat.markdown:
        data = export_markdown_bytes(markdown_content)
        media_type = "text/markdown"
    elif format == ExportFormat.pdf:
        from app.services.export_service import markdown_to_html
        html = markdown_to_html(markdown_content)
        try:
            data = html_to_pdf_bytes(html)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )