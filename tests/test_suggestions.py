"""
Tests for creative suggestions functionality
"""
import pytest
from unittest.mock import Mock, patch
from app.ai.nodes.suggestions.suggestions_node import suggestions_node, _gather_project_context
from app.ai.nodes.suggestions.llm_suggestions_generator import generate_creative_suggestions
from app.ai.state import AgentState


class TestSuggestionsNode:
    """Test the suggestions node functionality"""
    
    def test_suggestions_node_success(self):
        """Test successful suggestions generation"""
        # Mock state
        state = AgentState(
            project_id=1,
            user_input="I need suggestions for my e-commerce project",
            db=Mock()
        )
        
        # Mock the generate_creative_suggestions function
        with patch('app.ai.nodes.suggestions.suggestions_node.generate_creative_suggestions') as mock_generate:
            mock_generate.return_value = [
                {
                    "category": "ADDITIONAL_FEATURES",
                    "title": "Wishlist Feature",
                    "description": "Allow users to save products for later",
                    "value_proposition": "Increases user engagement and conversion",
                    "complexity": "Medium",
                    "priority": "High"
                }
            ]
            
            # Mock memory search
            with patch('app.ai.nodes.suggestions.suggestions_node.search_project_memories') as mock_search:
                mock_search.return_value = [
                    {"text": "User authentication system", "similarity_score": 0.8}
                ]
                
                result = suggestions_node(state)
                
                assert result["suggestions_generated"] is True
                assert len(result["suggestions"]) == 1
                assert result["suggestions"][0]["title"] == "Wishlist Feature"
    
    def test_suggestions_node_missing_context(self):
        """Test suggestions node with missing project context"""
        state = AgentState(user_input="test")
        
        result = suggestions_node(state)
        
        assert result["suggestions"] == []
        assert "suggestions_generated" not in result or not result["suggestions_generated"]


class TestSuggestionsGenerator:
    """Test the LLM suggestions generator"""
    
    @patch('app.ai.nodes.suggestions.llm_suggestions_generator.client')
    def test_generate_creative_suggestions(self, mock_client):
        """Test creative suggestions generation"""
        # Mock OpenAI response
        mock_message = Mock()
        mock_message.content = '''
        [
          {
            "category": "ADDITIONAL_FEATURES",
            "title": "Real-time Chat Support",
            "description": "Integrate live chat for customer support during shopping",
            "value_proposition": "Improves customer satisfaction and reduces cart abandonment",
            "complexity": "High",
            "priority": "Medium"
          }
        ]
        '''
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        
        project_context = {
            "project_id": 1,
            "current_input": "e-commerce platform",
            "existing_requirements": ["User registration", "Product catalog"],
            "features": ["Shopping cart", "Payment processing"],
            "use_cases": ["Browse products", "Make purchase"],
            "technical_details": ["React frontend", "Node.js backend"]
        }
        
        suggestions = generate_creative_suggestions(project_context, "test input")
        
        assert len(suggestions) == 1
        assert suggestions[0]["title"] == "Real-time Chat Support"
        assert suggestions[0]["category"] == "ADDITIONAL_FEATURES"


class TestGatherProjectContext:
    """Test project context gathering"""
    
    def test_gather_project_context(self):
        """Test gathering comprehensive project context"""
        mock_db = Mock()
        
        with patch('app.ai.nodes.suggestions.suggestions_node.search_project_memories') as mock_search:
            # Mock different types of memory searches
            mock_search.side_effect = [
                [{"text": "User authentication requirement"}],  # CRS memories
                [{"text": "Shopping cart feature"}],  # Feature memories  
                [{"text": "User checkout workflow"}],  # Use case memories
                [{"text": "React and Node.js stack"}]  # Technical memories
            ]
            
            context = _gather_project_context(mock_db, 1, "test input")
            
            assert context["project_id"] == 1
            assert context["current_input"] == "test input"
            assert len(context["existing_requirements"]) == 1
            assert len(context["features"]) == 1
            assert len(context["use_cases"]) == 1
            assert len(context["technical_details"]) == 1