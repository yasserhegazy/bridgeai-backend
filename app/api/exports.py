from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import json

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.export import ExportRequest, ExportFormat
from app.services.export_service import (
    export_markdown_bytes,
    markdown_to_html,
    html_to_pdf_bytes,
    crs_to_csv_data,
    generate_csv_bytes,
)
from app.api.projects import get_project_or_404, verify_team_membership

router = APIRouter()


@router.post("/{project_id}/export")
def export_project(
    project_id: int,
    export_req: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)
    verify_team_membership(db, project.team_id, current_user.id)

    filename = export_req.filename or f"export.{export_req.format.value}"

    if export_req.format == ExportFormat.markdown:
        data = export_markdown_bytes(export_req.content or "")
        media_type = "text/markdown"
    elif export_req.format == ExportFormat.pdf:
        html = markdown_to_html(export_req.content or "")
        try:
            data = html_to_pdf_bytes(html)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        media_type = "application/pdf"
    elif export_req.format == ExportFormat.csv:
        content = export_req.content or "{}"
        try:
             crs_json = json.loads(content)
        except json.JSONDecodeError:
             crs_json = {"project_title": "Export", "project_description": content}
        
        # Use placeholders for context not available in this generic endpoint
        rows = crs_to_csv_data(
            crs_json, 
            doc_id=0, 
            doc_version=0, 
            created_by=str(current_user.id), 
            created_date="",
            requirements_only=export_req.requirements_only
        )
        data = generate_csv_bytes(rows)
        media_type = "text/csv"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

    return StreamingResponse(io.BytesIO(data), media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })
