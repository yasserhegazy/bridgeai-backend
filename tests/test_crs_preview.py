"""
Tests for CRS preview generation and API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.crs_service import generate_preview_crs
from app.models.session_model import SessionModel
from app.models.message import Message, SenderType
from app.models.user import User


class TestCRSPreviewGeneration:
    """Test CRS preview generation from conversation."""
    
    @patch('app.services.crs_service.LLMTemplateFiller')
    def test_generate_preview_with_sufficient_conversation(self, mock_filler_class, db_session):
        """Test preview generation with enough conversation context."""
        # Setup mocks
        mock_filler = MagicMock()
        mock_filler_class.return_value = mock_filler
        
        mock_filler.fill_template.return_value = {
            "crs_content": '{"project_title": "Test Project"}',
            "crs_template": {"project_title": "Test Project"},
            "summary_points": ["Point 1", "Point 2"],
            "overall_summary": "Test summary",
            "is_complete": False,
            "completeness_percentage": 60,
            "missing_required_fields": ["functional_requirements"],
            "missing_optional_fields": ["project_objectives", "target_users"],
            "filled_optional_count": 0,
            "weak_fields": [],
            "field_sources": {"project_title": "explicit_user_input"}
        }
        
        mock_filler._check_completeness.return_value = True
        
        # Create test data
        user = User(id=1, email="test@test.com", role="client", hashed_password="test")
        db_session.add(user)
        db_session.commit()
        
        session = SessionModel(
            id=1,
            user_id=1,
            project_id=1,
            status="active"
        )
        db_session.add(session)
        db_session.commit()
        
        # Add messages
        messages = [
            Message(
                session_id=1,
                sender_type=SenderType.client,
                sender_id=1,
                content="I need a task management system"
            ),
            Message(
                session_id=1,
                sender_type=SenderType.ai,
                content="Great! Can you tell me more about the features you need?"
            ),
            Message(
                session_id=1,
                sender_type=SenderType.client,
                sender_id=1,
                content="Users should be able to create tasks, assign them, and track progress"
            )
        ]
        for msg in messages:
            db_session.add(msg)
        db_session.commit()
        
        # Generate preview
        result = generate_preview_crs(db_session, session_id=1, user_id=1)
        
        # Assertions
        assert result["content"] == '{"project_title": "Test Project"}'
        assert result["completeness_percentage"] == 60
        assert result["project_id"] == 1
        assert result["session_id"] == 1
        assert "weak_fields" in result
        assert "field_sources" in result
        
        # Verify LLM was called
        mock_filler.fill_template.assert_called_once()
    
    def test_generate_preview_no_messages_raises_error(self, db_session):
        """Test preview generation fails with no messages."""
        user = User(id=1, email="test@test.com", role="client", hashed_password="test")
        db_session.add(user)
        db_session.commit()
        
        session = SessionModel(
            id=1,
            user_id=1,
            project_id=1,
            status="active"
        )
        db_session.add(session)
        db_session.commit()
        
        # Should raise error
        with pytest.raises(ValueError, match="No messages found"):
            generate_preview_crs(db_session, session_id=1, user_id=1)
    
    def test_generate_preview_wrong_user_raises_error(self, db_session):
        """Test preview generation fails for wrong user."""
        user = User(id=1, email="test@test.com", role="client", hashed_password="test")
        db_session.add(user)
        db_session.commit()
        
        session = SessionModel(
            id=1,
            user_id=1,
            project_id=1,
            status="active"
        )
        db_session.add(session)
        db_session.commit()
        
        # Different user ID
        with pytest.raises(ValueError, match="does not have access"):
            generate_preview_crs(db_session, session_id=1, user_id=999)
    
    @patch('app.services.crs_service.LLMTemplateFiller')
    def test_generate_preview_minimal_conversation_raises_error(self, mock_filler_class, db_session):
        """Test preview generation with minimal conversation that produces no content."""
        # Setup mocks
        mock_filler = MagicMock()
        mock_filler_class.return_value = mock_filler
        
        mock_filler.fill_template.return_value = {
            "crs_content": '{}',
            "crs_template": {},
            "summary_points": [],
            "overall_summary": "",
            "is_complete": False,
            "completeness_percentage": 0,
            "missing_required_fields": ["project_title", "project_description", "functional_requirements"],
            "missing_optional_fields": [],
            "filled_optional_count": 0,
            "weak_fields": [],
            "field_sources": {}
        }
        
        # _check_completeness returns False for no content
        mock_filler._check_completeness.return_value = False
        
        # Create test data
        user = User(id=1, email="test@test.com", role="client", hashed_password="test")
        db_session.add(user)
        db_session.commit()
        
        session = SessionModel(
            id=1,
            user_id=1,
            project_id=1,
            status="active"
        )
        db_session.add(session)
        db_session.commit()
        
        # Single vague message
        message = Message(
            session_id=1,
            sender_type=SenderType.client,
            sender_id=1,
            content="Hi"
        )
        db_session.add(message)
        db_session.commit()
        
        # Should raise error for insufficient content
        with pytest.raises(ValueError, match="No CRS content available yet"):
            generate_preview_crs(db_session, session_id=1, user_id=1)
    
    @patch('app.services.crs_service.LLMTemplateFiller')
    def test_generate_preview_with_weak_fields(self, mock_filler_class, db_session):
        """Test preview correctly identifies weak fields."""
        # Setup mocks
        mock_filler = MagicMock()
        mock_filler_class.return_value = mock_filler
        
        mock_filler.fill_template.return_value = {
            "crs_content": '{"project_title": "App", "project_description": "Short"}',
            "crs_template": {"project_title": "App", "project_description": "Short"},
            "summary_points": ["Point 1"],
            "overall_summary": "Summary",
            "is_complete": False,
            "completeness_percentage": 20,
            "missing_required_fields": ["functional_requirements"],
            "missing_optional_fields": ["project_objectives", "target_users"],
            "filled_optional_count": 0,
            "weak_fields": ["project_title", "project_description"],  # Both weak
            "field_sources": {
                "project_title": "llm_inference",
                "project_description": "llm_inference"
            }
        }
        
        mock_filler._check_completeness.return_value = True
        
        # Create test data
        user = User(id=1, email="test@test.com", role="client", hashed_password="test")
        db_session.add(user)
        db_session.commit()
        
        session = SessionModel(
            id=1,
            user_id=1,
            project_id=1,
            status="active"
        )
        db_session.add(session)
        db_session.commit()
        
        message = Message(
            session_id=1,
            sender_type=SenderType.client,
            sender_id=1,
            content="I want an app"
        )
        db_session.add(message)
        db_session.commit()
        
        # Generate preview
        result = generate_preview_crs(db_session, session_id=1, user_id=1)
        
        # Assertions
        assert result["completeness_percentage"] == 20
        assert "project_title" in result["weak_fields"]
        assert "project_description" in result["weak_fields"]
        assert result["field_sources"]["project_title"] == "llm_inference"
        assert result["field_sources"]["project_description"] == "llm_inference"


class TestOptimisticLocking:
    """Test optimistic locking for CRS updates."""
    
    def test_update_crs_status_with_correct_version(self, db_session):
        """Test successful update with correct version."""
        from app.services.crs_service import update_crs_status
        from app.models.crs import CRSDocument, CRSStatus
        
        # Create CRS
        crs = CRSDocument(
            project_id=1,
            created_by=1,
            content="{}",
            summary_points="[]",
            field_sources="{}",
            version=1,
            edit_version=1,
            status=CRSStatus.draft
        )
        db_session.add(crs)
        db_session.commit()
        
        # Update with correct version
        updated = update_crs_status(
            db_session,
            crs_id=crs.id,
            new_status=CRSStatus.under_review,
            expected_version=1
        )
        
        assert updated.status == CRSStatus.under_review
        assert updated.edit_version == 2  # Incremented
    
    def test_update_crs_status_with_wrong_version_raises_error(self, db_session):
        """Test update fails with wrong version (concurrent modification)."""
        from app.services.crs_service import update_crs_status
        from app.models.crs import CRSDocument, CRSStatus
        
        # Create CRS
        crs = CRSDocument(
            project_id=1,
            created_by=1,
            content="{}",
            summary_points="[]",
            field_sources="{}",
            version=1,
            edit_version=2,  # Someone already updated it
            status=CRSStatus.draft
        )
        db_session.add(crs)
        db_session.commit()
        
        # Try to update with old version
        with pytest.raises(ValueError, match="was modified by another user"):
            update_crs_status(
                db_session,
                crs_id=crs.id,
                new_status=CRSStatus.under_review,
                expected_version=1  # Stale version
            )
    
    def test_update_crs_status_without_version_check(self, db_session):
        """Test update without version check still works (backward compatible)."""
        from app.services.crs_service import update_crs_status
        from app.models.crs import CRSDocument, CRSStatus
        
        # Create CRS
        crs = CRSDocument(
            project_id=1,
            created_by=1,
            content="{}",
            summary_points="[]",
            field_sources="{}",
            version=1,
            edit_version=1,
            status=CRSStatus.draft
        )
        db_session.add(crs)
        db_session.commit()
        
        # Update without version check (None)
        updated = update_crs_status(
            db_session,
            crs_id=crs.id,
            new_status=CRSStatus.under_review,
            expected_version=None  # No check
        )
        
        assert updated.status == CRSStatus.under_review
        assert updated.edit_version == 2


# Fixtures
@pytest.fixture
def db_session():
    """Create a test database session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.session import Base
    
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
