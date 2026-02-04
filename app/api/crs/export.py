"""
CRS Export and Audit Module.
Handles CRS document export (PDF, Markdown, CSV), audit logs, and SSE streaming.
"""
import asyncio
import io
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user, verify_token
from app.db.session import get_db
from app.models.audit import CRSAuditLog
from app.models.crs import CRSDocument
from app.models.session_model import SessionModel
from app.models.user import User
from app.schemas.export import ExportFormat
from app.services.permission_service import PermissionService
from app.services.crs_service import get_crs_by_id
from app.services.export_service import (
    crs_to_csv_data,
    crs_to_professional_html,
    export_markdown_bytes,
    generate_csv_bytes,
    html_to_pdf_bytes,
)
from app.schemas.crs import AuditLogOut


router = APIRouter()


@router.get("/{crs_id}/audit", response_model=List[AuditLogOut])
def get_crs_audit_logs(
    crs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return audit log entries for a CRS document."""
    # Verify access to CRS
    crs = get_crs_by_id(db, crs_id=crs_id)
    if not crs:
        raise HTTPException(status_code=404, detail="CRS document not found")
    project = PermissionService.verify_project_access(db, crs.project_id, current_user.id)

    logs = (
        db.query(CRSAuditLog)
        .filter(CRSAuditLog.crs_id == crs_id)
        .order_by(CRSAuditLog.changed_at.desc())
        .all()
    )

    return [
        {
            "id": log.id,
            "crs_id": log.crs_id,
            "changed_by": log.changed_by,
            "changed_at": log.changed_at,
            "action": log.action,
            "old_status": log.old_status,
            "new_status": log.new_status,
            "old_content": log.old_content,
            "new_content": log.new_content,
            "summary": log.summary,
        }
        for log in logs
    ]


@router.post("/{crs_id}/export")
def export_crs(
    crs_id: int,
    format: ExportFormat = Query(ExportFormat.pdf),
    requirements_only: bool = Query(
        False, description="If true, export only requirements (CSV only)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export a CRS document as PDF or Markdown with professional formatting.

    PDF exports include a professional corporate document header and styling.
    """
    # Helper function to convert CRS JSON to markdown
    def crs_json_to_markdown(crs_json):
        md = []
        md.append(f"# {crs_json.get('project_title', 'CRS Document')}")
        md.append("\n---\n")
        if crs_json.get("project_description"):
            md.append(f"**Description:** {crs_json['project_description']}\n")
        if crs_json.get("project_objectives"):
            md.append(
                "## Objectives\n"
                + "\n".join(f"- {o}" for o in crs_json["project_objectives"])
                + "\n"
            )
        if crs_json.get("target_users"):
            md.append(f"**Target Users:** {', '.join(crs_json['target_users'])}\n")
        if crs_json.get("stakeholders"):
            md.append(f"**Stakeholders:** {', '.join(crs_json['stakeholders'])}\n")
        md.append("\n---\n")
        if crs_json.get("functional_requirements"):
            md.append("## Functional Requirements\n")
            for fr in crs_json["functional_requirements"]:
                md.append(
                    f"- **{fr['id']} {fr['title']}** ({fr['priority']}): {fr['description']}"
                )
        md.append("\n---\n")
        if crs_json.get("performance_requirements"):
            md.append(
                "## Performance Requirements\n"
                + "\n".join(f"- {p}" for p in crs_json["performance_requirements"])
                + "\n"
            )
        if crs_json.get("security_requirements"):
            md.append(
                "## Security Requirements\n"
                + "\n".join(f"- {s}" for s in crs_json["security_requirements"])
                + "\n"
            )
        if crs_json.get("scalability_requirements"):
            md.append(
                "## Scalability Requirements\n"
                + "\n".join(f"- {s}" for s in crs_json["scalability_requirements"])
                + "\n"
            )
        md.append("\n---\n")
        if crs_json.get("technology_stack"):
            md.append("## Technology Stack\n")
            for k, v in crs_json["technology_stack"].items():
                md.append(f"- **{k.capitalize()}**: {', '.join(v)}")
        if crs_json.get("integrations"):
            md.append(f"**Integrations:** {', '.join(crs_json['integrations'])}\n")
        if crs_json.get("budget_constraints"):
            md.append(f"**Budget:** {crs_json['budget_constraints']}\n")
        if crs_json.get("timeline_constraints"):
            md.append(f"**Timeline:** {crs_json['timeline_constraints']}\n")
        if crs_json.get("technical_constraints"):
            md.append(
                f"**Technical Constraints:** {', '.join(crs_json['technical_constraints'])}\n"
            )
        md.append("\n---\n")
        if crs_json.get("success_metrics"):
            md.append(
                "## Success Metrics\n"
                + "\n".join(f"- {m}" for m in crs_json["success_metrics"])
                + "\n"
            )
        if crs_json.get("acceptance_criteria"):
            md.append(
                "## Acceptance Criteria\n"
                + "\n".join(f"- {a}" for a in crs_json["acceptance_criteria"])
                + "\n"
            )
        if crs_json.get("assumptions"):
            md.append(f"**Assumptions:** {', '.join(crs_json['assumptions'])}\n")
        if crs_json.get("risks"):
            md.append(f"**Risks:** {', '.join(crs_json['risks'])}\n")
        if crs_json.get("out_of_scope"):
            md.append(f"**Out of Scope:** {', '.join(crs_json['out_of_scope'])}\n")
        md.append("\n---\n")
        return "\n".join(md)

    # Get CRS document
    crs = db.query(CRSDocument).filter(CRSDocument.id == crs_id).first()
    if not crs:
        raise HTTPException(
            status_code=404, detail="CRS document not found"
        )

    # Verify access
    project = PermissionService.verify_project_access(db, crs.project_id, current_user.id)

    filename = f"crs-v{crs.version}.{format.value}"

    # If CRS content is JSON, convert to markdown
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
    elif format == ExportFormat.csv:
        # Ensure we have JSON content
        try:
            crs_json_for_csv = json.loads(content)
        except json.JSONDecodeError:
            # Fallback if content is not JSON (legacy or plain text)
            crs_json_for_csv = {
                "project_title": "CRS Export",
                "project_description": content,
            }

        csv_rows = crs_to_csv_data(
            crs_json_for_csv,
            doc_id=crs.id,
            doc_version=crs.version,
            created_by=str(crs.created_by),
            created_date=crs.created_at.isoformat() if crs.created_at else "",
            requirements_only=requirements_only,
        )
        data = generate_csv_bytes(csv_rows)
        media_type = "text/csv"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/stream/{session_id}")
async def stream_crs_updates(
    session_id: int,
    token: str = Query(...),  # Required for EventSource auth
    db: Session = Depends(get_db),
):
    """
    Stream live CRS updates for a specific chat session via Server-Sent Events (SSE).
    This allows the frontend to show a real-time, gradually updated document
    as the AI extracts requirements from the conversation.
    """
    # Authenticate user via query token
    try:
        current_user = verify_token(token, db)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")

    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify project access
    project = PermissionService.verify_project_access(db, session.project_id, current_user.id)

    async def event_generator():
        from app.core.events import event_bus
        
        print(f"[SSE] Client connected to live CRS stream for session {session_id}")
        
        # Send initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        
        try:
            # Create subscription queue
            queue = asyncio.Queue()
            event_bus.subscribers[session_id].add(queue)
            
            try:
                while True:
                    try:
                        # Wait for event with timeout for keepalive pings
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        # Send keepalive ping every 30 seconds
                        yield f": keepalive\n\n"
            finally:
                # Cleanup subscription
                event_bus.subscribers[session_id].discard(queue)
                if not event_bus.subscribers[session_id]:
                    del event_bus.subscribers[session_id]
                    
        except asyncio.CancelledError:
            print(f"[SSE] Stream cancelled for session {session_id}")
        except Exception as e:
            print(f"[SSE] Stream error for session {session_id}: {str(e)}")
        finally:
            print(f"[SSE] Client disconnected from live CRS stream for session {session_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
