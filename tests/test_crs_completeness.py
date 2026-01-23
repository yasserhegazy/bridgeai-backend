"""
Tests for CRS completeness calculation and quality validation.
"""

import pytest

from app.ai.nodes.template_filler.llm_template_filler import (
    CRSTemplate,
    LLMTemplateFiller,
)


class TestFieldQualityValidation:
    """Test field quality validation logic."""

    def test_validate_project_description_quality(self):
        """Test project description must be at least 50 characters with specificity."""
        filler = LLMTemplateFiller()

        # Quality description (>50 chars with specific details)
        assert (
            filler._validate_field_quality(
                "project_description",
                "A comprehensive task management system with real-time collaboration features, deadline tracking, and automated reporting for software development teams.",
            )
            is True
        )

        # Weak description (<50 chars)
        assert (
            filler._validate_field_quality(
                "project_description", "A project management app"
            )
            is False
        )

        # Empty
        assert filler._validate_field_quality("project_description", "") is False

    def test_validate_constraints_quality(self):
        """Test constraints must have specific details with breakdown/phases."""
        filler = LLMTemplateFiller()

        # Quality budget (>50 chars with breakdown keywords)
        assert (
            filler._validate_field_quality(
                "budget_constraints",
                "Total budget of $50,000 allocated as follows: development $30,000, testing $10,000, infrastructure $10,000",
            )
            is True
        )

        # Weak budget (no breakdown)
        assert (
            filler._validate_field_quality("budget_constraints", "Budget is $50,000")
            is False
        )

        # Weak budget (<50 chars)
        assert (
            filler._validate_field_quality("budget_constraints", "Under $100,000")
            is False
        )

        # Quality timeline (>40 chars with phases)
        assert (
            filler._validate_field_quality(
                "timeline_constraints",
                "Project timeline: Phase 1 (Weeks 1-4): Design, Phase 2 (Weeks 5-12): Development, Phase 3 (Weeks 13-16): Testing",
            )
            is True
        )

        # Weak timeline (no phases/milestones)
        assert (
            filler._validate_field_quality(
                "timeline_constraints", "Complete within 6 months"
            )
            is False
        )

    def test_validate_placeholder_values(self):
        """Test placeholder values are rejected."""
        filler = LLMTemplateFiller()

        placeholders = [
            "Not specified",
            "N/A",
            "TBD",
            "To be determined",
            "Pending",
            "Unknown",
            "Not applicable",
        ]

        for placeholder in placeholders:
            assert filler._validate_field_quality("project_title", placeholder) is False

    def test_validate_functional_requirements_count(self):
        """Test functional requirements need at least 5 items with 30+ char descriptions."""
        filler = LLMTemplateFiller()

        # Quality (5 requirements with detailed descriptions)
        reqs_good = [
            {
                "id": "FR-001",
                "title": "User Authentication",
                "description": "Implement secure user authentication system with email/password login and password reset functionality",
                "priority": "high",
            },
            {
                "id": "FR-002",
                "title": "Dashboard",
                "description": "Create main dashboard view showing real-time project status, task counts, and team member activity metrics",
                "priority": "high",
            },
            {
                "id": "FR-003",
                "title": "Reports",
                "description": "Generate PDF and Excel reports with customizable filters for project timeline, budget, and resource allocation",
                "priority": "medium",
            },
            {
                "id": "FR-004",
                "title": "Notifications",
                "description": "Send email and in-app notifications for task assignments, deadline reminders, and status updates",
                "priority": "medium",
            },
            {
                "id": "FR-005",
                "title": "File Upload",
                "description": "Allow users to upload and attach documents (PDF, Word, Excel) up to 25MB per file with version control",
                "priority": "low",
            },
        ]
        assert (
            filler._validate_field_quality("functional_requirements", reqs_good) is True
        )

        # Weak (only 3 requirements - less than 5)
        reqs_weak = reqs_good[:3]
        assert (
            filler._validate_field_quality("functional_requirements", reqs_weak)
            is False
        )

        # Empty
        assert filler._validate_field_quality("functional_requirements", []) is False

    def test_validate_objectives_and_users_count(self):
        """Test objectives and users need at least 2 items with 15+ chars each."""
        filler = LLMTemplateFiller()

        # Quality (2 items with sufficient detail)
        assert (
            filler._validate_field_quality(
                "project_objectives",
                [
                    "Improve team productivity and reduce task completion time by 30%",
                    "Reduce operational costs through process automation and resource optimization",
                ],
            )
            is True
        )

        # Weak (1 item)
        assert (
            filler._validate_field_quality("project_objectives", ["Improve efficiency"])
            is False
        )

        # Quality users (detailed descriptions)
        assert (
            filler._validate_field_quality(
                "target_users",
                [
                    "Project managers in software development teams",
                    "Team members and developers working on collaborative projects",
                ],
            )
            is True
        )

        # Weak users (too short)
        assert (
            filler._validate_field_quality("target_users", ["Managers", "Users"])
            is False
        )


class TestCompletenessCalculation:
    """Test completeness percentage calculation."""

    def test_empty_template_zero_percent(self):
        """Empty template should be 0%."""
        filler = LLMTemplateFiller()
        template = CRSTemplate()

        metadata = filler._get_completeness_metadata(template)

        assert metadata["percentage"] == 0
        assert len(metadata["missing_required"]) == 3
        assert "project_title" in metadata["missing_required"]
        assert "project_description" in metadata["missing_required"]
        assert "functional_requirements" in metadata["missing_required"]

    def test_only_required_fields_sixty_percent(self):
        """Only required fields filled should be 60% (3/5)."""
        filler = LLMTemplateFiller()
        template = CRSTemplate(
            project_title="Task Manager Pro",
            project_description="A comprehensive task management system with real-time collaboration features, deadline tracking, automated reporting, and mobile app support for software development teams",
            functional_requirements=[
                {
                    "id": "FR-001",
                    "title": "User Authentication",
                    "description": "Implement secure user authentication system with email/password login and password reset functionality",
                    "priority": "high",
                },
                {
                    "id": "FR-002",
                    "title": "Dashboard",
                    "description": "Create main dashboard view showing real-time project status, task counts, and team member activity metrics",
                    "priority": "high",
                },
                {
                    "id": "FR-003",
                    "title": "Task Management",
                    "description": "Allow users to create, edit, delete, and assign tasks with priority levels, due dates, and status tracking",
                    "priority": "high",
                },
                {
                    "id": "FR-004",
                    "title": "Notifications",
                    "description": "Send email and in-app notifications for task assignments, deadline reminders, and status updates",
                    "priority": "medium",
                },
                {
                    "id": "FR-005",
                    "title": "Reports",
                    "description": "Generate PDF and Excel reports with customizable filters for project timeline, budget, and resource allocation",
                    "priority": "low",
                },
            ],
        )

        metadata = filler._get_completeness_metadata(template)

        assert metadata["percentage"] == 60
        assert len(metadata["missing_required"]) == 0
        assert metadata["filled_optional_count"] == 0

    def test_required_plus_one_optional_eighty_percent(self):
        """Required + 1 optional should be 80% (4/5)."""
        filler = LLMTemplateFiller()
        template = CRSTemplate(
            project_title="Task Manager Pro",
            project_description="A comprehensive task management system with real-time collaboration features, deadline tracking, automated reporting, and mobile app support for software development teams",
            functional_requirements=[
                {
                    "id": "FR-001",
                    "title": "User Authentication",
                    "description": "Implement secure user authentication system with email/password login and password reset functionality",
                    "priority": "high",
                },
                {
                    "id": "FR-002",
                    "title": "Dashboard",
                    "description": "Create main dashboard view showing real-time project status, task counts, and team member activity metrics",
                    "priority": "high",
                },
                {
                    "id": "FR-003",
                    "title": "Task Management",
                    "description": "Allow users to create, edit, delete, and assign tasks with priority levels, due dates, and status tracking",
                    "priority": "high",
                },
                {
                    "id": "FR-004",
                    "title": "Notifications",
                    "description": "Send email and in-app notifications for task assignments, deadline reminders, and status updates",
                    "priority": "medium",
                },
                {
                    "id": "FR-005",
                    "title": "Reports",
                    "description": "Generate PDF and Excel reports with customizable filters for project timeline, budget, and resource allocation",
                    "priority": "low",
                },
            ],
            project_objectives=[
                "Improve team productivity and reduce task completion time by 30%",
                "Streamline project workflows through process automation",
            ],
        )

        metadata = filler._get_completeness_metadata(template)

        assert metadata["percentage"] == 80
        assert metadata["filled_optional_count"] == 1

    def test_required_plus_two_optional_hundred_percent(self):
        """Required + 2 optional should be 100% (5/5)."""
        filler = LLMTemplateFiller()
        template = CRSTemplate(
            project_title="Task Manager Pro",
            project_description="A comprehensive task management system with real-time collaboration features, deadline tracking, automated reporting, and mobile app support for software development teams",
            functional_requirements=[
                {
                    "id": "FR-001",
                    "title": "User Authentication",
                    "description": "Implement secure user authentication system with email/password login and password reset functionality",
                    "priority": "high",
                },
                {
                    "id": "FR-002",
                    "title": "Dashboard",
                    "description": "Create main dashboard view showing real-time project status, task counts, and team member activity metrics",
                    "priority": "high",
                },
                {
                    "id": "FR-003",
                    "title": "Task Management",
                    "description": "Allow users to create, edit, delete, and assign tasks with priority levels, due dates, and status tracking",
                    "priority": "high",
                },
                {
                    "id": "FR-004",
                    "title": "Notifications",
                    "description": "Send email and in-app notifications for task assignments, deadline reminders, and status updates",
                    "priority": "medium",
                },
                {
                    "id": "FR-005",
                    "title": "Reports",
                    "description": "Generate PDF and Excel reports with customizable filters for project timeline, budget, and resource allocation",
                    "priority": "low",
                },
            ],
            project_objectives=[
                "Improve team productivity and reduce task completion time by 30%",
                "Streamline project workflows through process automation and integration",
            ],
            target_users=[
                "Project managers in software development teams",
                "Team members and developers working on collaborative projects",
            ],
        )

        metadata = filler._get_completeness_metadata(template)

        assert metadata["percentage"] == 100
        assert metadata["filled_optional_count"] == 2

    def test_weak_values_dont_count(self):
        """Weak values should not count toward progress."""
        filler = LLMTemplateFiller()
        template = CRSTemplate(
            project_title="Task Manager",  # Only 12 chars, but >10 so acceptable for title
            project_description="A task app",  # <50 chars - WEAK
            functional_requirements=[  # Only 1 requirement - WEAK (need 3)
                {
                    "id": "FR-001",
                    "title": "Login",
                    "description": "Auth",
                    "priority": "high",
                }
            ],
            budget_constraints="Limited budget",  # No numbers - WEAK
            timeline_constraints="ASAP",  # <20 chars, no dates - WEAK
        )

        metadata = filler._get_completeness_metadata(template)

        # Only project_title is acceptable (>10 chars)
        # project_description is weak (<50 chars)
        # functional_requirements is weak (<3 items)
        # budget_constraints is weak (no numbers)
        # timeline_constraints is weak (<20 chars, no dates)

        assert metadata["percentage"] < 40  # Should be low
        assert "project_description" in metadata["weak_fields"]
        assert "functional_requirements" in metadata["weak_fields"]
        assert "budget_constraints" in metadata["weak_fields"]
        assert "timeline_constraints" in metadata["weak_fields"]

    def test_more_than_two_optional_capped_at_hundred(self):
        """More than 2 optional fields should still be 100% (capped)."""
        filler = LLMTemplateFiller()
        template = CRSTemplate(
            project_title="Task Manager Pro",
            project_description="A comprehensive task management system with real-time collaboration features, deadline tracking, automated reporting, and mobile app support for software development teams",
            functional_requirements=[
                {
                    "id": "FR-001",
                    "title": "User Authentication",
                    "description": "Implement secure user authentication system with email/password login and password reset functionality",
                    "priority": "high",
                },
                {
                    "id": "FR-002",
                    "title": "Dashboard",
                    "description": "Create main dashboard view showing real-time project status, task counts, and team member activity metrics",
                    "priority": "high",
                },
                {
                    "id": "FR-003",
                    "title": "Task Management",
                    "description": "Allow users to create, edit, delete, and assign tasks with priority levels, due dates, and status tracking",
                    "priority": "high",
                },
                {
                    "id": "FR-004",
                    "title": "Notifications",
                    "description": "Send email and in-app notifications for task assignments, deadline reminders, and status updates",
                    "priority": "medium",
                },
                {
                    "id": "FR-005",
                    "title": "Reports",
                    "description": "Generate PDF and Excel reports with customizable filters for project timeline, budget, and resource allocation",
                    "priority": "low",
                },
            ],
            project_objectives=[
                "Improve team productivity and reduce task completion time by 30%",
                "Streamline project workflows through process automation and integration",
            ],
            target_users=[
                "Project managers in software development teams",
                "Team members and developers working on collaborative projects",
            ],
            budget_constraints="Total budget of $75,000 allocated as follows: development phase $45,000, testing phase $15,000, infrastructure $15,000",
            timeline_constraints="Project timeline: Phase 1 (Weeks 1-8): Requirements and design, Phase 2 (Weeks 9-24): Development, Phase 3 (Weeks 25-32): Testing and deployment",
            success_metrics=[
                "User adoption rate exceeding 80% within 3 months",
                "Task completion speed improvement of 30% compared to current process",
            ],
        )

        metadata = filler._get_completeness_metadata(template)

        # 3 required + 5 optional filled, but capped at 3+2=5
        assert metadata["percentage"] == 100
        assert metadata["filled_optional_count"] == 5  # All filled

    def test_mixed_quality_fields(self):
        """Test mix of quality and weak fields."""
        filler = LLMTemplateFiller()
        template = CRSTemplate(
            project_title="Good Project Title",
            project_description="This is a sufficiently detailed project description with specific information about features, target audience, and technical requirements that exceeds the minimum requirement",
            functional_requirements=[
                {
                    "id": "FR-001",
                    "title": "Feature One",
                    "description": "Brief description",
                    "priority": "high",
                },
                {
                    "id": "FR-002",
                    "title": "Feature Two",
                    "description": "Another brief description",
                    "priority": "high",
                },
            ],  # Only 2 items and descriptions <30 chars - WEAK
            project_objectives=["Short obj"],  # Only 1 item and <15 chars - WEAK
            budget_constraints="Not specified",  # Placeholder - WEAK
        )

        metadata = filler._get_completeness_metadata(template)

        # project_title: ✓ quality
        # project_description: ✓ quality
        # functional_requirements: ✗ weak (only 2, need 5 with 30+ char descriptions)
        # project_objectives: ✗ weak (only 1, need 2)
        # budget_constraints: ✗ weak (placeholder)

        # 2 required out of 3 = 40%
        assert metadata["percentage"] == 40
        assert "functional_requirements" in metadata["weak_fields"]
        assert "project_objectives" in metadata["weak_fields"]


class TestFieldSourcesTracking:
    """Test field sources tracking."""

    def test_track_new_fields_as_explicit(self):
        """New quality fields should be marked as explicit_user_input."""
        filler = LLMTemplateFiller()
        template = CRSTemplate(
            project_title="Task Manager Pro",
            project_description="A comprehensive task management system with real-time collaboration features, deadline tracking, automated reporting, and mobile app support for software development teams",
            functional_requirements=[
                {
                    "id": "FR-001",
                    "title": "User Authentication",
                    "description": "Implement secure user authentication system with email/password login and password reset functionality",
                    "priority": "high",
                },
                {
                    "id": "FR-002",
                    "title": "Dashboard",
                    "description": "Create main dashboard view showing real-time project status, task counts, and team member activity metrics",
                    "priority": "high",
                },
                {
                    "id": "FR-003",
                    "title": "Task Management",
                    "description": "Allow users to create, edit, delete, and assign tasks with priority levels, due dates, and status tracking",
                    "priority": "high",
                },
                {
                    "id": "FR-004",
                    "title": "Notifications",
                    "description": "Send email and in-app notifications for task assignments, deadline reminders, and status updates",
                    "priority": "medium",
                },
                {
                    "id": "FR-005",
                    "title": "Reports",
                    "description": "Generate PDF and Excel reports with customizable filters for project timeline, budget, and resource allocation",
                    "priority": "low",
                },
            ],
        )

        sources = filler._track_field_sources(template, None)

        assert sources["project_title"] == "explicit_user_input"
        assert sources["project_description"] == "explicit_user_input"
        assert sources["functional_requirements"] == "explicit_user_input"

    def test_track_weak_fields_as_inferred(self):
        """Weak quality fields should be marked as llm_inference."""
        filler = LLMTemplateFiller()
        template = CRSTemplate(
            project_title="App",  # <10 chars - weak
            project_description="Short desc",  # <50 chars - weak
            budget_constraints="Limited",  # <50 chars, no breakdown - weak
        )

        sources = filler._track_field_sources(template, None)

        assert sources["project_title"] == "llm_inference"
        assert sources["project_description"] == "llm_inference"
        assert sources["budget_constraints"] == "llm_inference"

    def test_track_empty_fields(self):
        """Empty fields should be marked as empty."""
        filler = LLMTemplateFiller()
        template = CRSTemplate()

        sources = filler._track_field_sources(template, None)

        assert sources["project_title"] == "empty"
        assert sources["project_description"] == "empty"
        assert sources["functional_requirements"] == "empty"


class TestCompletenessCheck:
    """Test completeness boolean check."""

    def test_strict_mode_requires_all_criteria(self):
        """Strict mode should require all 3 required + 2 optional fields."""
        filler = LLMTemplateFiller()

        # Missing optional fields
        template_incomplete = CRSTemplate(
            project_title="Task Manager Pro",
            project_description="A comprehensive task management system that helps teams track and organize their work",
            functional_requirements=[
                {
                    "id": "FR-001",
                    "title": "Login",
                    "description": "Auth",
                    "priority": "high",
                },
                {
                    "id": "FR-002",
                    "title": "Dashboard",
                    "description": "View",
                    "priority": "high",
                },
                {
                    "id": "FR-003",
                    "title": "Tasks",
                    "description": "Manage",
                    "priority": "high",
                },
            ],
        )

        assert (
            filler._check_completeness(template_incomplete, strict_mode=True) is False
        )

        # All criteria met
        template_complete = CRSTemplate(
            project_title="Task Manager Pro",
            project_description="A comprehensive task management system that helps teams track and organize their work",
            functional_requirements=[
                {
                    "id": "FR-001",
                    "title": "Login",
                    "description": "Auth",
                    "priority": "high",
                },
                {
                    "id": "FR-002",
                    "title": "Dashboard",
                    "description": "View",
                    "priority": "high",
                },
                {
                    "id": "FR-003",
                    "title": "Tasks",
                    "description": "Manage",
                    "priority": "high",
                },
            ],
            project_objectives=["Improve productivity", "Streamline work"],
            target_users=["Managers", "Team members"],
        )

        assert filler._check_completeness(template_complete, strict_mode=True) is True

    def test_non_strict_mode_accepts_partial(self):
        """Non-strict mode should accept any content."""
        filler = LLMTemplateFiller()

        # Minimal content
        template = CRSTemplate(project_title="App")

        assert filler._check_completeness(template, strict_mode=False) is True

        # Empty template
        empty_template = CRSTemplate()

        assert filler._check_completeness(empty_template, strict_mode=False) is False
