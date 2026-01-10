"""
Security validation tests for input validation and XSS prevention.
Run with: pytest tests/test_security.py -v
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.user import UserCreate
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRejectionRequest
from app.schemas.team import TeamCreate, TeamUpdate
from app.schemas.notification import NotificationBase
from app.models.notification import NotificationType
from pydantic import ValidationError


class TestInputValidation:
    """Test input validation across all schemas."""
    
    def test_user_password_validation(self):
        """Test password complexity requirements."""
        # Too short
        with pytest.raises(ValidationError) as exc:
            UserCreate(full_name="Test User", email="test@example.com", password="short")
        assert "at least 8 characters" in str(exc.value).lower()
        
        # No uppercase
        with pytest.raises(ValidationError) as exc:
            UserCreate(full_name="Test User", email="test@example.com", password="password123")
        assert "uppercase" in str(exc.value).lower()
        
        # No lowercase
        with pytest.raises(ValidationError) as exc:
            UserCreate(full_name="Test User", email="test@example.com", password="PASSWORD123")
        assert "lowercase" in str(exc.value).lower()
        
        # No digit
        with pytest.raises(ValidationError) as exc:
            UserCreate(full_name="Test User", email="test@example.com", password="Password")
        assert "digit" in str(exc.value).lower()
        
        # Valid password
        user = UserCreate(
            full_name="Test User",
            email="test@example.com",
            password="ValidPass123"
        )
        assert user.password == "ValidPass123"
    
    def test_user_name_validation(self):
        """Test name field validation."""
        # Invalid characters
        with pytest.raises(ValidationError) as exc:
            UserCreate(
                full_name="Test<script>alert('xss')</script>",
                email="test@example.com",
                password="ValidPass123"
            )
        assert "can only contain" in str(exc.value).lower()
        
        # Valid name
        user = UserCreate(
            full_name="John Doe-Smith",
            email="test@example.com",
            password="ValidPass123"
        )
        assert user.full_name == "John Doe-Smith"
    
    def test_project_name_validation(self):
        """Test project name validation."""
        # Invalid characters
        with pytest.raises(ValidationError) as exc:
            ProjectCreate(
                name="Project<script>",
                description="Test",
                team_id=1
            )
        assert "can only contain" in str(exc.value).lower()
        
        # Valid name
        project = ProjectCreate(
            name="My-Project_2024",
            description="Test description",
            team_id=1
        )
        assert project.name == "My-Project_2024"
    
    def test_project_description_xss_prevention(self):
        """Test XSS prevention in project description."""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "onclick=alert('xss')"
        ]
        
        for xss_input in xss_inputs:
            with pytest.raises(ValidationError) as exc:
                ProjectCreate(
                    name="Test Project",
                    description=xss_input,
                    team_id=1
                )
            assert "invalid content" in str(exc.value).lower()
    
    def test_team_name_validation(self):
        """Test team name validation."""
        # Invalid characters
        with pytest.raises(ValidationError) as exc:
            TeamCreate(name="Team@#$%", description="Test")
        assert "can only contain" in str(exc.value).lower()
        
        # Valid name
        team = TeamCreate(name="Dev-Team_2024", description="Test")
        assert team.name == "Dev-Team_2024"
    
    def test_team_description_xss_prevention(self):
        """Test XSS prevention in team description."""
        with pytest.raises(ValidationError) as exc:
            TeamCreate(
                name="Test Team",
                description="<script>alert('xss')</script>"
            )
        assert "invalid content" in str(exc.value).lower()
    
    def test_notification_xss_prevention(self):
        """Test XSS prevention in notifications."""
        with pytest.raises(ValidationError) as exc:
            NotificationBase(
                title="Test<script>alert('xss')</script>",
                message="Test message",
                type=NotificationType.TEAM_INVITATION,
                reference_id=1
            )
        assert "invalid content" in str(exc.value).lower()
    
    def test_length_constraints(self):
        """Test length constraints on various fields."""
        # Project name too long
        with pytest.raises(ValidationError):
            ProjectCreate(
                name="x" * 257,
                description="Test",
                team_id=1
            )
        
        # Description too long
        with pytest.raises(ValidationError):
            ProjectCreate(
                name="Test",
                description="x" * 2001,
                team_id=1
            )
        
        # Team name too long
        with pytest.raises(ValidationError):
            TeamCreate(name="x" * 101, description="Test")
    
    def test_positive_integer_validation(self):
        """Test that IDs must be positive integers."""
        with pytest.raises(ValidationError):
            ProjectCreate(
                name="Test",
                description="Test",
                team_id=0  # Must be > 0
            )
        
        with pytest.raises(ValidationError):
            ProjectCreate(
                name="Test",
                description="Test",
                team_id=-1  # Must be > 0
            )


class TestSecurityHeaders:
    """Test security headers are present in responses."""
    
    def test_security_headers_present(self):
        """Test that security headers are added to responses."""
        client = TestClient(app)
        response = client.get("/")
        
        # Check all security headers
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
    
    def test_csp_header_configuration(self):
        """Test Content Security Policy is properly configured."""
        client = TestClient(app)
        response = client.get("/")
        
        csp = response.headers.get("Content-Security-Policy")
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp


class TestRequestSizeLimits:
    """Test request size limiting."""
    
    def test_large_request_rejected(self):
        """Test that requests larger than 10MB are rejected."""
        client = TestClient(app)
        
        # Create a large payload (simulated with content-length header)
        large_size = 11 * 1024 * 1024  # 11MB
        
        response = client.post(
            "/api/projects/",
            json={"name": "Test", "team_id": 1},
            headers={"content-length": str(large_size)}
        )
        
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()


class TestSanitization:
    """Test input sanitization."""
    
    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed from inputs."""
        user = UserCreate(
            full_name="  John Doe  ",
            email="test@example.com",
            password="ValidPass123"
        )
        assert user.full_name == "John Doe"
    
    def test_email_normalization(self):
        """Test that emails are normalized to lowercase."""
        from app.schemas.invitation import InvitationCreate
        
        invitation = InvitationCreate(
            email="  TEST@EXAMPLE.COM  ",
            role="member"
        )
        assert invitation.email == "test@example.com"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_string_validation(self):
        """Test that empty strings are rejected."""
        with pytest.raises(ValidationError):
            ProjectCreate(name="", description="Test", team_id=1)
        
        with pytest.raises(ValidationError):
            TeamCreate(name="", description="Test")
    
    def test_whitespace_only_validation(self):
        """Test that whitespace-only strings are rejected."""
        with pytest.raises(ValidationError):
            ProjectCreate(name="   ", description="Test", team_id=1)
    
    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        # Should accept valid unicode
        project = ProjectCreate(
            name="Project2024",  # ASCII only for name
            description="Test with émojis 🚀",
            team_id=1
        )
        assert project.description == "Test with émojis 🚀"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
