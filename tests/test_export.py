from app.services import export_service
import pytest
import csv
import io


def test_markdown_export_bytes():
    md = "# Hello\nWorld"
    b = export_service.export_markdown_bytes(md)
    assert isinstance(b, bytes)
    assert b.decode("utf-8") == md


def test_pdf_export_behavior():
    html = "<p>Hi</p>"
    try:
        import xhtml2pdf
        # If installed, ensure we get bytes back
        pdf = export_service.html_to_pdf_bytes(html)
        assert isinstance(pdf, (bytes, bytearray))
    except ImportError:
        with pytest.raises(RuntimeError):
            export_service.html_to_pdf_bytes(html)


def test_crs_to_csv_data_structure():
    sample_crs = {
        "project_title": "Test Project",
        "project_description": "Test description",
        "project_objectives": ["Obj 1", "Obj 2"],
        "target_users": ["User A"],
        "functional_requirements": [
            {"id": "FR-01", "title": "Req 1", "description": "Desc 1", "priority": "high", "verification": "Test"},
            {"id": "FR-02", "title": "Req 2", "description": "Desc 2", "priority": "medium"}
        ],
        "budget_constraints": "$100k",
    }
    
    rows = export_service.crs_to_csv_data(
        sample_crs,
        doc_id=1,
        doc_version=2,
        created_by="user_123",
        created_date="2023-01-01"
    )
    
    assert len(rows) > 0
    
    # Check Header
    root = rows[0]
    assert root["artifact_id"] == "ROOT"
    assert root["title"] == "Test Project"
    assert root["doc_id"] == 1
    
    # Check Objective Section
    obj_section = next(r for r in rows if r["title"] == "Objectives")
    assert obj_section["type"] == "header"
    
    # Check Objective Items
    objs = [r for r in rows if r["parent_id"] == obj_section["artifact_id"]]
    assert len(objs) == 2
    assert objs[0]["content"] == "Obj 1"
    assert objs[0]["req_type"] == "objective"
    
    # Check FR Section
    fr_section = next(r for r in rows if r["title"] == "Functional Requirements")
    frs = [r for r in rows if r["parent_id"] == fr_section["artifact_id"]]
    assert len(frs) == 2
    assert frs[0]["artifact_id"] == "FR-01"
    assert frs[0]["priority"] == "high"
    assert frs[0]["verification_method"] == "Test"
    
    # Check Constraints
    const_section = next(r for r in rows if r["title"] == "Constraints")
    consts = [r for r in rows if r["parent_id"] == const_section["artifact_id"]]
    assert len(consts) == 1
    assert consts[0]["content"] == "Budget: $100k"
    assert consts[0]["type"] == "constraint"


def test_generate_csv_bytes():
    rows = [{"artifact_id": "1", "title": "Test", "type": "text", "doc_id": 1}]
    # Note: Using limited rows, but generate_csv_bytes uses predefined columns so it might fill others with empty strings
    # Actually crs_to_csv_data guarantees all columns, but let's test a simple dict
    
    # To properly test generate_csv_bytes, we should use a dict that has all keys OR rely on DictWriter behavior
    # export_service.py uses predefined CSV_COLUMNS.
    
    # Let's use the helper to get valid rows
    rows = export_service.crs_to_csv_data({}, 1, 1, "u", "d")
    csv_bytes = export_service.generate_csv_bytes(rows)
    
    assert csv_bytes.startswith(b'\xef\xbb\xbf') # BOM
    
    content = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    csv_rows = list(reader)
    
    assert len(csv_rows) == len(rows)


def test_crs_to_csv_requirements_only():
    sample_crs = {
        "project_title": "Test Project",
        "project_objectives": ["Obj 1"],
        "functional_requirements": [
            {"id": "FR-01", "title": "Req 1", "description": "Desc 1", "priority": "high"}
        ],
        "out_of_scope": ["Scope 1"]
    }
    
    # Test with requirements_only=True
    rows = export_service.crs_to_csv_data(
        sample_crs, 1, 1, "u", "d", requirements_only=True
    )
    
    # Should contain FR and Objective (mapped to req), but NOT Project Title (header) or Out of Scope (note)
    # Wait, my logic for Objectives mapped it to 'req'. 
    # Let's check my implementation: 
    # add_section("Objectives", ..., item_type="req", ...) -> Type is "req"
    # add_section("Out of Scope", ..., item_type="note") -> Type is "note"
    # Code: [r for r in rows if r["type"] == "req"]
    
    types = [r["type"] for r in rows]
    assert "req" in types
    assert "header" not in types
    assert "note" not in types
    assert len(rows) == 2 # 1 Obj + 1 FR

