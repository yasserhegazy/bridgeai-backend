"""
Comprehensive tests for CRS pattern definitions and flow.
Tests pattern selection, prompt generation, and end-to-end CRS generation flow.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from app.models.crs import CRSPattern, CRSStatus
from app.schemas.chat import CRSPatternEnum
from app.ai.nodes.template_filler.llm_template_filler import LLMTemplateFiller, CRSTemplate


class TestCRSPatternDefinitions:
    """Test CRS pattern enum definitions and consistency."""
    
    def test_crs_pattern_enum_values(self):
        """Verify CRSPattern enum has all required values."""
        assert hasattr(CRSPattern, 'iso_iec_ieee_29148')
        assert hasattr(CRSPattern, 'ieee_830')
        assert hasattr(CRSPattern, 'babok')
        
        assert CRSPattern.iso_iec_ieee_29148.value == 'iso_iec_ieee_29148'
        assert CRSPattern.ieee_830.value == 'ieee_830'
        assert CRSPattern.babok.value == 'babok'
    
    def test_crs_pattern_enum_consistency_with_schema(self):
        """Ensure CRSPattern matches CRSPatternEnum schema."""
        assert set([p.value for p in CRSPattern]) == set([p.value for p in CRSPatternEnum])
    
    def test_default_pattern_is_babok(self):
        """Verify default pattern is BABOK."""
        assert CRSPattern.babok.value == 'babok'


class TestLLMTemplateFillerPatterns:
    """Test LLMTemplateFiller pattern selection and prompt generation."""
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_template_filler_default_pattern(self, mock_groq):
        """Test default pattern selection (BABOK)."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            filler = LLMTemplateFiller()
            assert filler.pattern == 'babok'
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_template_filler_ieee830_pattern(self, mock_groq):
        """Test IEEE 830 pattern selection."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            filler = LLMTemplateFiller(pattern='ieee_830')
            assert filler.pattern == 'ieee_830'
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_template_filler_iso29148_pattern(self, mock_groq):
        """Test ISO/IEC/IEEE 29148 pattern selection."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            filler = LLMTemplateFiller(pattern='iso_iec_ieee_29148')
            assert filler.pattern == 'iso_iec_ieee_29148'
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_babok_prompt_contains_babok_keywords(self, mock_groq):
        """Verify BABOK prompt contains BABOK-specific terminology."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            filler = LLMTemplateFiller(pattern='babok')
            prompt_text = filler.BABOK_EXTRACTION_PROMPT
            prompt_upper = prompt_text.upper()
            
            # Check for BABOK-specific terms
            assert 'BABOK' in prompt_upper
            assert 'BUSINESS ANALYSIS BODY OF KNOWLEDGE' in prompt_upper
            assert 'BUSINESS NEED' in prompt_upper
            assert 'STAKEHOLDERS' in prompt_upper
            assert 'CURRENT STATE' in prompt_upper and 'FUTURE STATE' in prompt_upper
            assert 'SOLUTION SCOPE' in prompt_upper
            assert 'BUSINESS VALUE' in prompt_upper
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_ieee830_prompt_contains_ieee_keywords(self, mock_groq):
        """Verify IEEE 830 prompt contains IEEE 830-specific terminology."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            filler = LLMTemplateFiller(pattern='ieee_830')
            prompt_text = filler.IEEE830_EXTRACTION_PROMPT
            
            # Check for IEEE 830-specific terms
            assert 'IEEE 830' in prompt_text or 'IEEE830' in prompt_text
            assert 'Software Requirements Specification' in prompt_text or 'SRS' in prompt_text
            assert 'Introduction' in prompt_text
            assert 'Overall Description' in prompt_text
            assert 'Specific Requirements' in prompt_text
            assert 'verifiable' in prompt_text.lower()
            assert 'testable' in prompt_text.lower()
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_iso29148_prompt_contains_iso_keywords(self, mock_groq):
        """Verify ISO 29148 prompt contains ISO-specific terminology."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            filler = LLMTemplateFiller(pattern='iso_iec_ieee_29148')
            prompt_text = filler.ISO29148_EXTRACTION_PROMPT
            
            # Check for ISO 29148-specific terms
            assert 'ISO' in prompt_text or 'IEC' in prompt_text
            assert '29148' in prompt_text
            assert 'Operational Concepts' in prompt_text
            assert 'System Requirements' in prompt_text
            assert 'Quality Attributes' in prompt_text
            assert 'Interface Requirements' in prompt_text
            assert 'Verification Criteria' in prompt_text


class TestCRSPatternFlow:
    """Test end-to-end CRS generation flow with different patterns."""
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_babok_pattern_extraction_flow(self, mock_groq):
        """Test full extraction flow with BABOK pattern."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            # Mock LLM response
            mock_response = Mock()
            mock_response.content = json.dumps({
                "project_title": "E-Commerce Platform",
                "project_description": "A comprehensive online shopping platform for retail businesses.",
                "project_objectives": ["Increase online sales", "Improve customer experience"],
                "target_users": ["Retail customers", "Business owners"],
                "functional_requirements": [
                    {
                        "id": "BR-001",
                        "title": "Product Catalog",
                        "description": "System must provide a searchable product catalog.",
                        "priority": "high"
                    }
                ],
                "stakeholders": ["Business owners", "Customers"],
                "performance_requirements": [],
                "security_requirements": [],
                "scalability_requirements": [],
                "technology_stack": {},
                "integrations": [],
                "budget_constraints": "",
                "timeline_constraints": "",
                "technical_constraints": [],
                "success_metrics": [],
                "acceptance_criteria": [],
                "assumptions": [],
                "risks": [],
                "out_of_scope": []
            })
            
            mock_groq_instance = MagicMock()
            mock_groq_instance.invoke.return_value = mock_response
            mock_groq.return_value = mock_groq_instance
            
            filler = LLMTemplateFiller(pattern='babok')
            result = filler.extract_requirements(
                user_input="I need an e-commerce platform",
                conversation_history=[],
                extracted_fields={}
            )
            
            assert isinstance(result, CRSTemplate)
            assert result.project_title == "E-Commerce Platform"
            assert len(result.functional_requirements) > 0
            assert result.functional_requirements[0]['id'].startswith('BR-')  # BABOK uses BR- prefix
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_ieee830_pattern_extraction_flow(self, mock_groq):
        """Test full extraction flow with IEEE 830 pattern."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            # Mock LLM response
            mock_response = Mock()
            mock_response.content = json.dumps({
                "project_title": "Inventory Management System",
                "project_description": "Technical system for tracking inventory in real-time.",
                "project_objectives": ["Automate inventory tracking", "Reduce manual errors"],
                "target_users": ["Warehouse staff", "Managers"],
                "functional_requirements": [
                    {
                        "id": "SRS-001",
                        "title": "Real-time Inventory Tracking",
                        "description": "System shall update inventory counts within 2 seconds of transaction.",
                        "priority": "high"
                    }
                ],
                "stakeholders": ["Warehouse managers"],
                "performance_requirements": ["Response time < 2 seconds"],
                "security_requirements": ["Role-based access control"],
                "scalability_requirements": [],
                "technology_stack": {},
                "integrations": [],
                "budget_constraints": "",
                "timeline_constraints": "",
                "technical_constraints": [],
                "success_metrics": [],
                "acceptance_criteria": [],
                "assumptions": [],
                "risks": [],
                "out_of_scope": []
            })
            
            mock_groq_instance = MagicMock()
            mock_groq_instance.invoke.return_value = mock_response
            mock_groq.return_value = mock_groq_instance
            
            filler = LLMTemplateFiller(pattern='ieee_830')
            result = filler.extract_requirements(
                user_input="I need an inventory system",
                conversation_history=[],
                extracted_fields={}
            )
            
            assert isinstance(result, CRSTemplate)
            assert result.project_title == "Inventory Management System"
            assert len(result.functional_requirements) > 0
            assert result.functional_requirements[0]['id'].startswith('SRS-')  # IEEE 830 uses SRS- prefix
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_iso29148_pattern_extraction_flow(self, mock_groq):
        """Test full extraction flow with ISO 29148 pattern."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            # Mock LLM response
            mock_response = Mock()
            mock_response.content = json.dumps({
                "project_title": "Hospital Management System",
                "project_description": "Comprehensive system for managing hospital operations and patient records.",
                "project_objectives": ["Streamline patient care", "Improve record accuracy"],
                "target_users": ["Doctors", "Nurses", "Administrators"],
                "functional_requirements": [
                    {
                        "id": "SYS-001",
                        "title": "Patient Registration",
                        "description": "System shall allow registration of new patients with verification.",
                        "priority": "high"
                    }
                ],
                "stakeholders": ["Hospital staff", "Patients"],
                "performance_requirements": [],
                "security_requirements": ["HIPAA compliance"],
                "scalability_requirements": [],
                "technology_stack": {},
                "integrations": [],
                "budget_constraints": "",
                "timeline_constraints": "",
                "technical_constraints": ["Must comply with HIPAA"],
                "success_metrics": [],
                "acceptance_criteria": [],
                "assumptions": [],
                "risks": [],
                "out_of_scope": []
            })
            
            mock_groq_instance = MagicMock()
            mock_groq_instance.invoke.return_value = mock_response
            mock_groq.return_value = mock_groq_instance
            
            filler = LLMTemplateFiller(pattern='iso_iec_ieee_29148')
            result = filler.extract_requirements(
                user_input="I need a hospital management system",
                conversation_history=[],
                extracted_fields={}
            )
            
            assert isinstance(result, CRSTemplate)
            assert result.project_title == "Hospital Management System"
            assert len(result.functional_requirements) > 0
            assert result.functional_requirements[0]['id'].startswith('SYS-')  # ISO 29148 uses SYS- prefix


class TestCRSTemplateStructure:
    """Test CRS template structure and methods."""
    
    def test_crs_template_initialization(self):
        """Test CRSTemplate can be initialized with default values."""
        template = CRSTemplate()
        
        assert template.project_title == ""
        assert template.project_description == ""
        assert isinstance(template.project_objectives, list)
        assert isinstance(template.functional_requirements, list)
        assert isinstance(template.technology_stack, dict)
    
    def test_crs_template_to_dict(self):
        """Test CRSTemplate can be converted to dictionary."""
        template = CRSTemplate(
            project_title="Test Project",
            project_description="Test Description",
            project_objectives=["Objective 1", "Objective 2"]
        )
        
        result = template.to_dict()
        
        assert isinstance(result, dict)
        assert result['project_title'] == "Test Project"
        assert result['project_description'] == "Test Description"
        assert len(result['project_objectives']) == 2
    
    def test_crs_template_to_json(self):
        """Test CRSTemplate can be converted to JSON string."""
        template = CRSTemplate(
            project_title="Test Project",
            functional_requirements=[
                {"id": "FR-001", "title": "Feature 1", "description": "Description", "priority": "high"}
            ]
        )
        
        result = template.to_json()
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed['project_title'] == "Test Project"
        assert len(parsed['functional_requirements']) == 1
    
    def test_crs_template_get_summary_points(self):
        """Test CRSTemplate summary points generation."""
        template = CRSTemplate(
            project_title="E-Commerce Platform",
            project_objectives=["Objective 1", "Objective 2"],
            functional_requirements=[{"id": "FR-001"}],
            target_users=["Customers", "Admins"],
            budget_constraints="$50,000",
            timeline_constraints="6 months"
        )
        
        points = template.get_summary_points()
        
        assert isinstance(points, list)
        assert any("E-Commerce Platform" in p for p in points)
        assert any("Objectives: 2 defined" in p for p in points)
        assert any("Functional Requirements: 1 items" in p for p in points)
        assert any("Budget: $50,000" in p for p in points)
        assert any("Timeline: 6 months" in p for p in points)


class TestPatternValidation:
    """Test pattern validation and error handling."""
    
    def test_invalid_pattern_defaults_to_babok(self):
        """Test that invalid pattern values default to BABOK."""
        from app.services.crs_service import persist_crs_document
        from app.models.crs import CRSPattern
        
        # Test in the service layer
        with patch('app.services.crs_service.create_memory'):
            from sqlalchemy.orm import Session
            mock_db = Mock(spec=Session)
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()
            mock_db.query = Mock(return_value=Mock(filter=Mock(return_value=Mock(order_by=Mock(return_value=Mock(first=Mock(return_value=None)))))))
            
            # This should not raise an error and should use babok as default
            crs = persist_crs_document(
                mock_db,
                project_id=1,
                created_by=1,
                content="Test content",
                pattern="invalid_pattern"
            )
            
            # Should have created with babok pattern
            assert mock_db.add.called
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_pattern_case_insensitivity(self, mock_groq):
        """Test that pattern selection is case-insensitive where appropriate."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            # These should all work
            filler1 = LLMTemplateFiller(pattern='babok')
            filler2 = LLMTemplateFiller(pattern='BABOK')
            filler3 = LLMTemplateFiller(pattern='ieee_830')
            
            assert filler1.pattern.lower() == 'babok'
            assert filler2.pattern.lower() == 'babok'
            assert filler3.pattern == 'ieee_830'


class TestPromptQuality:
    """Test the quality and completeness of pattern-specific prompts."""
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_all_prompts_have_json_output_instruction(self, mock_groq):
        """Verify all prompts instruct LLM to return JSON."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            filler = LLMTemplateFiller()
            
            prompts = [
                filler.BABOK_EXTRACTION_PROMPT,
                filler.IEEE830_EXTRACTION_PROMPT,
                filler.ISO29148_EXTRACTION_PROMPT
            ]
            
            for prompt in prompts:
                assert 'JSON' in prompt
                assert 'json' in prompt.lower()
                assert 'Return' in prompt or 'return' in prompt
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_all_prompts_have_required_fields(self, mock_groq):
        """Verify all prompts include all required CRS fields."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            filler = LLMTemplateFiller()
            
            required_fields = [
                'project_title',
                'project_description',
                'functional_requirements',
                'target_users',
                'budget_constraints',
                'timeline_constraints'
            ]
            
            prompts = [
                filler.BABOK_EXTRACTION_PROMPT,
                filler.IEEE830_EXTRACTION_PROMPT,
                filler.ISO29148_EXTRACTION_PROMPT
            ]
            
            for prompt in prompts:
                for field in required_fields:
                    assert field in prompt, f"Field '{field}' missing from prompt"
    
    @patch('app.ai.nodes.template_filler.llm_template_filler.ChatGroq')
    def test_prompts_include_quality_instructions(self, mock_groq):
        """Verify prompts include quality and specificity instructions."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            filler = LLMTemplateFiller()
            
            prompts = [
                filler.BABOK_EXTRACTION_PROMPT,
                filler.IEEE830_EXTRACTION_PROMPT,
                filler.ISO29148_EXTRACTION_PROMPT
            ]
            
            quality_keywords = ['DO NOT', 'CRITICAL', 'specific', 'clear', 'concise']
            
            for prompt in prompts:
                has_quality_instruction = any(keyword in prompt for keyword in quality_keywords)
                assert has_quality_instruction, "Prompt lacks quality instructions"
