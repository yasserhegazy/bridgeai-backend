"""
Tests for CRS (Customer Requirements Specification) service functionality.
Covers persistence, versioning, status updates, and retrieval operations.
"""

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # ensures all tables are registered with Base metadata
from app.db.session import Base
from app.models.crs import CRSStatus
from app.services.crs_service import (
    get_crs_versions,
    get_latest_crs,
    persist_crs_document,
    update_crs_status,
)


def _in_memory_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_persist_and_fetch_latest_crs():
    """Test that a CRS document can be persisted and retrieved."""
    db = _in_memory_session()
    try:
        content = json.dumps({"title": "Test CRS"})
        summary = ["Point A", "Point B"]

        created = persist_crs_document(
            db,
            project_id=1,
            created_by=99,
            content=content,
            summary_points=summary,
            store_embedding=False,  # avoid external dependencies in unit test
        )

        latest = get_latest_crs(db, project_id=1)

        assert latest is not None
        assert latest.id == created.id
        assert json.loads(latest.summary_points) == summary
        assert latest.content == content
    finally:
        db.close()


def test_crs_versioning():
    """Test that multiple CRS documents are versioned correctly."""
    db = _in_memory_session()
    try:
        # Create first version
        crs_v1 = persist_crs_document(
            db,
            project_id=1,
            created_by=99,
            content=json.dumps({"version": 1}),
            summary_points=["Version 1"],
            store_embedding=False,
        )

        # Create second version
        crs_v2 = persist_crs_document(
            db,
            project_id=1,
            created_by=99,
            content=json.dumps({"version": 2}),
            summary_points=["Version 2"],
            store_embedding=False,
        )

        # Verify versions are different
        assert crs_v1.id != crs_v2.id

        # Verify get_crs_versions returns all versions in correct order
        versions = get_crs_versions(db, project_id=1)
        assert len(versions) == 2
        # Newest first (highest version)
        assert versions[0].id == crs_v2.id
        assert versions[1].id == crs_v1.id

        # Latest should return the most recent
        latest = get_latest_crs(db, project_id=1)
        assert latest.id == crs_v2.id
    finally:
        db.close()


def test_update_crs_status():
    """Test that CRS status can be updated through the approval workflow."""
    db = _in_memory_session()
    try:
        # Create a draft CRS
        crs = persist_crs_document(
            db,
            project_id=1,
            created_by=99,
            content=json.dumps({"title": "Status Test"}),
            summary_points=["Test point"],
            store_embedding=False,
        )

        # Initial status should be draft
        assert crs.status == CRSStatus.draft

        # Update to under_review
        updated = update_crs_status(
            db, crs_id=crs.id, new_status=CRSStatus.under_review
        )
        assert updated.status == CRSStatus.under_review

        # Approve the CRS
        approved = update_crs_status(
            db,
            crs_id=crs.id,
            new_status=CRSStatus.approved,
            approved_by=100,  # BA user ID
        )
        assert approved.status == CRSStatus.approved
        assert approved.approved_by == 100
    finally:
        db.close()


def test_crs_not_found_returns_none():
    """Test that fetching CRS for non-existent project returns None."""
    db = _in_memory_session()
    try:
        latest = get_latest_crs(db, project_id=9999)
        assert latest is None

        versions = get_crs_versions(db, project_id=9999)
        assert versions == []
    finally:
        db.close()
