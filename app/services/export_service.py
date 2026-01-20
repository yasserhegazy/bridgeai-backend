from typing import Optional, List, Dict, Any
import csv
import io
import json

from datetime import datetime

try:
    import markdown as _md
except Exception:
    _md = None


def markdown_to_html(markdown_text: str) -> str:
    """Convert Markdown text to HTML with proper styling.
    Uses `markdown` package when available, otherwise returns a safe preformatted HTML fallback.
    """
    if markdown_text is None:
        markdown_text = ""
    
    # Convert markdown to HTML
    if _md:
        html_content = _md.markdown(markdown_text)
    else:
        # Fallback: escape and wrap in <pre>
        escaped = html_module.escape(markdown_text)
        html_content = f"<pre>{escaped}</pre>"
    
    # Wrap with proper styling
    styled_html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1, h2, h3, h4, h5, h6 {{
                margin-top: 1.5em;
                margin-bottom: 0.5em;
                font-weight: 600;
            }}
            h1 {{
                font-size: 2em;
                border-bottom: 2px solid #007bff;
                padding-bottom: 0.3em;
            }}
            h2 {{
                font-size: 1.5em;
                border-bottom: 1px solid #ddd;
                padding-bottom: 0.2em;
            }}
            p {{
                margin: 0.5em 0;
            }}
            strong {{
                font-weight: 600;
                color: #333;
            }}
            code {{
                background-color: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: "Courier New", monospace;
                font-size: 0.9em;
            }}
            pre {{
                background-color: #f4f4f4;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                font-family: "Courier New", monospace;
            }}
            pre code {{
                background-color: transparent;
                padding: 0;
            }}
            blockquote {{
                border-left: 4px solid #007bff;
                margin: 0.5em 0;
                padding-left: 1em;
                color: #666;
            }}
            ul, ol {{
                margin: 0.5em 0;
                padding-left: 2em;
            }}
            li {{
                margin: 0.25em 0;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }}
            table thead {{
                background-color: #f4f4f4;
            }}
            table th, table td {{
                border: 1px solid #ddd;
                padding: 8px 12px;
                text-align: left;
            }}
            a {{
                color: #007bff;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    return styled_html


def crs_to_professional_html(content: str, project_name: str = "Project") -> str:
    """Convert CRS Markdown content to a professional, corporate-style HTML document.
    
    Args:
        content: Markdown-formatted CRS content
        project_name: Name of the project for the document header
        
    Returns:
        HTML string with professional formatting suitable for PDF export
    """
    if content is None:
        content = ""
    
    # Convert markdown to HTML
    if _md:
        html_content = _md.markdown(content)
    else:
        escaped = html_module.escape(content)
        html_content = f"<pre>{escaped}</pre>"
    
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Professional corporate styling for CRS documents - simplified for weasyprint compatibility
    styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.7;
            color: #2c3e50;
            background: white;
            padding: 40px;
            font-size: 11pt;
        }}
        
        .document-header {{
            border-top: 5px solid #0066cc;
            border-bottom: 2px solid #0066cc;
            padding: 25px 0;
            margin-bottom: 30px;
        }}
        
        .document-title {{
            font-size: 28pt;
            font-weight: bold;
            color: #0066cc;
            margin-bottom: 8px;
        }}
        
        .document-subtitle {{
            font-size: 16pt;
            color: #555;
            font-weight: bold;
            margin-bottom: 12px;
        }}
        
        .document-meta {{
            font-size: 10pt;
            color: #666;
            border-top: 1px solid #ddd;
            padding-top: 10px;
        }}
        
        .meta-line {{
            margin: 3px 0;
        }}
        
        .meta-label {{
            font-weight: bold;
            color: #0066cc;
            display: inline-block;
            width: 100px;
        }}
        
        .content {{
            margin-top: 20px;
        }}
        
        h1 {{
            font-size: 20pt;
            font-weight: bold;
            color: #0066cc;
            margin: 25px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #0066cc;
            page-break-after: avoid;
        }}
        
        h2 {{
            font-size: 16pt;
            font-weight: bold;
            color: #0088dd;
            margin: 20px 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #ddd;
            page-break-after: avoid;
        }}
        
        h3 {{
            font-size: 13pt;
            font-weight: bold;
            color: #333;
            margin: 15px 0 10px 0;
            page-break-after: avoid;
        }}
        
        h4, h5, h6 {{
            font-size: 11pt;
            font-weight: bold;
            margin: 12px 0 8px 0;
        }}
        
        p {{
            margin-bottom: 12px;
            text-align: justify;
        }}
        
        strong {{
            font-weight: bold;
            color: #0066cc;
        }}
        
        em {{
            font-style: italic;
        }}
        
        code {{
            background-color: #f5f5f5;
            padding: 2px 4px;
            font-family: "Courier New", monospace;
            font-size: 9pt;
            color: #c41e3a;
        }}
        
        pre {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            padding: 12px;
            overflow-x: auto;
            margin: 15px 0;
            font-family: "Courier New", monospace;
            font-size: 9pt;
            line-height: 1.4;
            color: #333;
        }}
        
        blockquote {{
            border-left: 4px solid #0066cc;
            background-color: #f0f7ff;
            margin: 15px 0;
            padding: 12px 15px;
            color: #2c3e50;
        }}
        
        ul {{
            margin: 12px 0;
            padding-left: 25px;
        }}
        
        ol {{
            margin: 12px 0;
            padding-left: 25px;
        }}
        
        li {{
            margin-bottom: 6px;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            border: 1px solid #ddd;
        }}
        
        table thead {{
            background-color: #0066cc;
            color: white;
        }}
        
        table th {{
            padding: 10px;
            text-align: left;
            font-weight: bold;
            font-size: 10pt;
            border: 1px solid #0066cc;
        }}
        
        table td {{
            padding: 8px 10px;
            border: 1px solid #ddd;
            font-size: 10pt;
        }}
        
        table tbody tr:nth-child(odd) {{
            background-color: #fafafa;
        }}
        
        a {{
            color: #0066cc;
            text-decoration: underline;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #ddd;
            margin: 25px 0;
        }}
    </style>
</head>
<body>
    <div class="document-header">
        <div class="document-title">Client Requirements Specification</div>
        <div class="document-subtitle">{project_name}</div>
        <div class="document-meta">
            <div class="meta-line"><span class="meta-label">Generated:</span> {current_date}</div>
            <div class="meta-line"><span class="meta-label">Document Type:</span> CRS</div>
            <div class="meta-line"><span class="meta-label">Status:</span> Official</div>
        </div>
    </div>
    
    <div class="content">
        {html_content}
    </div>
</body>
</html>
"""
    return styled_html


def export_markdown_bytes(markdown_text: str) -> bytes:
    """Return raw markdown bytes for download."""
    if markdown_text is None:
        markdown_text = ""
    return markdown_text.encode("utf-8")


def html_to_pdf_bytes(html: str) -> bytes:
    """Render HTML to PDF bytes using xhtml2pdf.

    Converts HTML to PDF using xhtml2pdf (pisa), which is cross-platform compatible
    with Windows and Linux without external system dependencies.
    Preserves formatting, colors, fonts, and layout.
    """
    if html is None:
        html = ""
    try:
        from xhtml2pdf import pisa
        from io import BytesIO
    except Exception as e:
        raise RuntimeError("PDF export requires xhtml2pdf to be installed") from e

    try:
        # Wrap HTML with proper DOCTYPE for xhtml2pdf
        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            margin: 20px;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #0066cc;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        h1 {{
            font-size: 24pt;
            border-bottom: 2px solid #0066cc;
            padding-bottom: 0.3em;
        }}
        h2 {{
            font-size: 18pt;
            border-bottom: 1px solid #ddd;
            padding-bottom: 0.2em;
        }}
        p {{
            margin: 0.5em 0;
            text-align: justify;
        }}
        strong {{
            font-weight: bold;
            color: #0066cc;
        }}
        em {{
            font-style: italic;
        }}
        code {{
            background-color: #f5f5f5;
            padding: 2px 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #c41e3a;
        }}
        pre {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            padding: 12px;
            overflow-x: auto;
            margin: 15px 0;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.4;
        }}
        blockquote {{
            border-left: 4px solid #0066cc;
            background-color: #f0f7ff;
            margin: 15px 0;
            padding: 12px 15px;
            color: #2c3e50;
        }}
        ul, ol {{
            margin: 12px 0;
            padding-left: 25px;
        }}
        li {{
            margin-bottom: 6px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            border: 1px solid #ddd;
        }}
        table thead {{
            background-color: #0066cc;
            color: white;
        }}
        table th {{
            padding: 10px;
            text-align: left;
            font-weight: bold;
            border: 1px solid #0066cc;
        }}
        table td {{
            padding: 8px 10px;
            border: 1px solid #ddd;
        }}
        table tbody tr:nth-child(odd) {{
            background-color: #fafafa;
        }}
        a {{
            color: #0066cc;
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 2px solid #ddd;
            margin: 25px 0;
        }}
    </style>
</head>
<body>
    {html}
</body>
</html>"""
        
        pdf_buffer = BytesIO()
        
        # Convert HTML to PDF
        status = pisa.CreatePDF(
            full_html,
            pdf_buffer,
            encoding='UTF-8'
        )
        
        if status.err:
            raise RuntimeError(f"PDF generation failed: {status.err}")
        
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
    except Exception as e:
        raise RuntimeError(f"Failed to render PDF: {str(e)}") from e


CSV_COLUMNS = [
    "artifact_id", "type", "label", "parent_id", "order_index", "title",
    "content", "doc_id", "doc_version", "doc_section_path", "req_type",
    "priority", "stakeholder", "acceptance_criteria", "status", "source",
    "related_artifact_id", "rationale", "verification_method", "risk_level",
    "complexity", "created_by", "created_date", "last_modified", "in_scope"
]


def crs_to_csv_data(crs_json: Dict[str, Any], doc_id: int, doc_version: int, created_by: str, created_date: str, requirements_only: bool = False) -> List[Dict[str, Any]]:
    """
    Convert CRS JSON structure to a flat list of artifact rows for CSV export.
    """
    rows = []
    order_index = 1
    
    # Helper to create a base row
    def create_row(**kwargs):
        row = {col: "" for col in CSV_COLUMNS}
        row.update({
            "doc_id": doc_id,
            "doc_version": doc_version,
            "created_by": created_by,
            "created_date": created_date,
            "in_scope": "True"
        })
        row.update(kwargs)
        return row

    # 1. Project Info (Header + Text artifacts)
    project_title = crs_json.get("project_title", "Untitled Project")
    root_id = "ROOT"
    
    # Root Node (Project Title)
    rows.append(create_row(
        artifact_id=root_id,
        type="header",
        title=project_title,
        order_index=order_index,
        content=crs_json.get("project_description", "")
    ))
    order_index += 1

    # Helper for sections
    def add_section(section_title: str, items: List[Any], item_type: str = "text", req_type: str = ""):
        nonlocal order_index
        # Iterate even if items is empty? No, usually skip empty sections
        if not items:
            return

        section_id = f"SEC-{order_index}"
        rows.append(create_row(
            artifact_id=section_id,
            parent_id=root_id,
            type="header",
            title=section_title,
            order_index=order_index,
            doc_section_path=f"/{project_title}/{section_title}"
        ))
        # parent_order = order_index # Unused
        order_index += 1
        
        for i, item in enumerate(items, 1):
            item_id = f"{section_id}-{i}"
            row_data = {
                "artifact_id": item_id,
                "parent_id": section_id,
                "order_index": order_index,
                "doc_section_path": f"/{project_title}/{section_title}",
                "type": item_type,
            }
            
            if isinstance(item, str):
                row_data["content"] = item
                if req_type:
                    row_data["req_type"] = req_type
            elif isinstance(item, dict):
                # Handle structured requirements (FRs)
                row_data["artifact_id"] = item.get("id", item_id)
                row_data["title"] = item.get("title", "")
                row_data["content"] = item.get("description", "")
                row_data["priority"] = item.get("priority", "")
                row_data["req_type"] = req_type or "functional"
                
                if "verification" in item: row_data["verification_method"] = item["verification"]
                if "complexity" in item: row_data["complexity"] = item["complexity"]
                
            rows.append(create_row(**row_data))
            order_index += 1

    # Map sections
    # Objectives
    add_section("Objectives", crs_json.get("project_objectives", []), item_type="req", req_type="objective")
    
    # Target Users
    add_section("Target Users", crs_json.get("target_users", []), item_type="text")
    
    # Stakeholders
    add_section("Stakeholders", crs_json.get("stakeholders", []), item_type="text")

    # Functional Requirements
    add_section("Functional Requirements", crs_json.get("functional_requirements", []), item_type="req", req_type="functional")

    # Non-Functional Requirements
    add_section("Performance Requirements", crs_json.get("performance_requirements", []), item_type="req", req_type="performance")
    add_section("Security Requirements", crs_json.get("security_requirements", []), item_type="req", req_type="security")
    add_section("Scalability Requirements", crs_json.get("scalability_requirements", []), item_type="req", req_type="scalability")
    
    # Technical
    tech_stack = crs_json.get("technology_stack", {})
    if tech_stack:
        tech_items = []
        for category, techs in tech_stack.items():
            if isinstance(techs, list):
                tech_items.append(f"{category.capitalize()}: {', '.join(techs)}")
            else:
                 tech_items.append(f"{category.capitalize()}: {techs}")
        add_section("Technology Stack", tech_items, item_type="text")

    add_section("Integrations", crs_json.get("integrations", []), item_type="text")
    
    # Constraints
    constraints = []
    if crs_json.get("budget_constraints"): constraints.append(f"Budget: {crs_json['budget_constraints']}")
    if crs_json.get("timeline_constraints"): constraints.append(f"Timeline: {crs_json['timeline_constraints']}")
    constraints.extend(crs_json.get("technical_constraints", []))
    add_section("Constraints", constraints, item_type="constraint")

    # Success Criteria
    add_section("Success Metrics", crs_json.get("success_metrics", []), item_type="req", req_type="success_metric")
    add_section("Acceptance Criteria", crs_json.get("acceptance_criteria", []), item_type="req", req_type="acceptance_criterion")
    
    # Others
    add_section("Assumptions", crs_json.get("assumptions", []), item_type="note")
    add_section("Risks", crs_json.get("risks", []), item_type="note")
    add_section("Out of Scope", crs_json.get("out_of_scope", []), item_type="note")

    if requirements_only:
        return [r for r in rows if r["type"] == "req"]

    return rows


def generate_csv_bytes(rows: List[Dict[str, Any]]) -> bytes:
    """
    Generate CSV bytes from a list of artifact dictionaries.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")
