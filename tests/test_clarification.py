"""
Tests for the Clarification Agent.

This module contains unit tests for:
- Clarification node behavior and routing logic
- LLMAmbiguityDetector initialization and validation
- Edge cases and error scenarios

Note: These tests use mocks to avoid requiring actual OpenAI API calls.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.ai.nodes.clarification.llm_ambiguity_detector import LLMAmbiguityDetector, Ambiguity
from app.ai.nodes.clarification.clarification_node import clarification_node, should_request_clarification
from app.ai.state import AgentState


# ============================================================================
# Unit Tests for LLMAmbiguityDetector
# ============================================================================

class TestLLMAmbiguityDetector:
    """Test the LLM-powered ambiguity detector."""

    @patch('app.ai.nodes.clarification.llm_ambiguity_detector.ChatOpenAI')
    def test_initialization_success(self, mock_llm_class):
        """Test successful initialization with API key."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            detector = LLMAmbiguityDetector(model_name="gpt-4o-mini", temperature=0.2)
            assert detector is not None
            mock_llm_class.assert_called_once_with(model="gpt-4o-mini", temperature=0.2)

    @patch('app.ai.nodes.clarification.llm_ambiguity_detector.ChatOpenAI')
    def test_initialization_missing_api_key(self, mock_llm_class):
        """Test initialization fails without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
                LLMAmbiguityDetector()

    @patch('app.ai.nodes.clarification.llm_ambiguity_detector.ChatOpenAI')
    def test_generate_questions_empty(self, mock_llm_class):
        """Test question generation with no ambiguities."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm
            
            detector = LLMAmbiguityDetector()
            
            questions = detector.generate_questions([])
            
            assert questions == []


# ============================================================================
# Unit Tests for Clarification Node
# ============================================================================

class TestClarificationNode:
    """Test the clarification node behavior."""

    @patch('app.ai.nodes.clarification.clarification_node.LLMAmbiguityDetector')
    def test_clarification_node_needs_clarification(self, mock_detector_class):
        """Test node behavior when clarification is needed."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # Setup mock detector
            mock_detector = Mock()
            mock_detector.analyze_and_generate_questions.return_value = {
                "ambiguities": [
                    Ambiguity(
                        type="missing",
                        field="project_name",
                        reason="No name",
                        severity="high"
                    )
                ],
                "clarification_questions": ["What is the project name?"],
                "clarity_score": 40,
                "summary": "Requirements incomplete",
                "needs_clarification": True
            }
            mock_detector_class.return_value = mock_detector
            
            state: AgentState = {
                "user_input": "I want a system",
                "conversation_history": [],
                "extracted_fields": {}
            }
            
            result = clarification_node(state)
            
            assert result["needs_clarification"] is True
            assert len(result["clarification_questions"]) == 1
            assert len(result["ambiguities"]) == 1
            assert result["clarity_score"] == 40
            assert "clarify" in result["output"].lower()
            assert result["last_node"] == "clarification"

    @patch('app.ai.nodes.clarification.clarification_node.LLMAmbiguityDetector')
    def test_clarification_node_clear_requirements(self, mock_detector_class):
        """Test node behavior when requirements are clear."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_detector = Mock()
            mock_detector.analyze_and_generate_questions.return_value = {
                "ambiguities": [],
                "clarification_questions": [],
                "clarity_score": 95,
                "summary": "Requirements are clear",
                "needs_clarification": False
            }
            mock_detector_class.return_value = mock_detector
            
            state: AgentState = {
                "user_input": "Build ShopEasy e-commerce platform with user auth, product catalog, cart, and Stripe payment processing",
                "conversation_history": [],
                "extracted_fields": {}
            }
            
            result = clarification_node(state)
            
            assert result["needs_clarification"] is False
            assert len(result["clarification_questions"]) == 0
            assert result["clarity_score"] == 95
            assert "clear" in result["output"].lower()
            assert result["last_node"] == "clarification"

    def test_should_request_clarification_true(self):
        """Test routing function returns True when clarification needed."""
        state: AgentState = {
            "needs_clarification": True,
            "user_input": "test"
        }
        
        result = should_request_clarification(state)
        
        assert result is True

    def test_should_request_clarification_false(self):
        """Test routing function returns False when clarification not needed."""
        state: AgentState = {
            "needs_clarification": False,
            "user_input": "test"
        }
        
        result = should_request_clarification(state)
        
        assert result is False

    def test_should_request_clarification_default(self):
        """Test routing function defaults to False if key missing."""
        state: AgentState = {
            "user_input": "test"
        }
        
        result = should_request_clarification(state)
        
        assert result is False


# ============================================================================
# API Integration Tests
# ============================================================================

class TestClarificationAPI:
    """Test the clarification API endpoints."""

    def test_analyze_requirements_invalid_input(self, client):
        """Test API endpoint with invalid input."""
        response = client.post(
            "/api/ai/analyze-requirements",
            json={
                "invalid_field": "test"
            }
        )
        
        assert response.status_code == 422  # Validation error


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================

class TestClarificationEdgeCases:
    """Test edge cases and special scenarios."""

    @patch('app.ai.nodes.clarification.clarification_node.LLMAmbiguityDetector')
    def test_empty_user_input(self, mock_detector_class):
        """Test handling of empty user input."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_detector = Mock()
            mock_detector.analyze_and_generate_questions.return_value = {
                "ambiguities": [],
                "clarification_questions": ["Could you provide more details about your project?"],
                "clarity_score": 0,
                "summary": "No input provided",
                "needs_clarification": True
            }
            mock_detector_class.return_value = mock_detector
            
            state: AgentState = {
                "user_input": "",
                "conversation_history": [],
                "extracted_fields": {}
            }
            
            result = clarification_node(state)
            
            assert result["needs_clarification"] is True
            assert len(result["clarification_questions"]) > 0

    @patch('app.ai.nodes.clarification.clarification_node.LLMAmbiguityDetector')
    def test_very_long_input(self, mock_detector_class):
        """Test handling of very long user input."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_detector = Mock()
            mock_detector.analyze_and_generate_questions.return_value = {
                "ambiguities": [],
                "clarification_questions": [],
                "clarity_score": 85,
                "summary": "Detailed requirements",
                "needs_clarification": False
            }
            mock_detector_class.return_value = mock_detector
            
            long_input = "Build a platform " * 1000  # Very long input
            
            state: AgentState = {
                "user_input": long_input,
                "conversation_history": [],
                "extracted_fields": {}
            }
            
            result = clarification_node(state)
            
            # Should still process successfully
            assert "last_node" in result
            assert result["last_node"] == "clarification"

    @patch('app.ai.nodes.clarification.clarification_node.LLMAmbiguityDetector')
    def test_multiple_high_severity_ambiguities(self, mock_detector_class):
        """Test handling of multiple high-severity ambiguities."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_detector = Mock()
            ambiguities = [
                Ambiguity("missing", f"field_{i}", "Missing", "high")
                for i in range(10)
            ]
            mock_detector.analyze_and_generate_questions.return_value = {
                "ambiguities": ambiguities,
                "clarification_questions": [f"Question {i}?" for i in range(10)],
                "clarity_score": 20,
                "summary": "Many critical issues",
                "needs_clarification": True
            }
            mock_detector_class.return_value = mock_detector
            
            state: AgentState = {
                "user_input": "vague input",
                "conversation_history": [],
                "extracted_fields": {}
            }
            
            result = clarification_node(state)
            
            assert result["needs_clarification"] is True
            assert len(result["ambiguities"]) == 10
            assert result["clarity_score"] == 20
