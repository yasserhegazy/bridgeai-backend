"""
Clarification Node Module

This module implements the clarification agent node for LangGraph.
It analyzes user input for ambiguities and generates clarification questions
to improve requirement quality.
"""

from typing import Dict, Any
from app.ai.state import AgentState
from app.ai.nodes.clarification.ambiguity_detector import AmbiguityDetector


def clarification_node(state: AgentState) -> Dict[str, Any]:
    """
    Clarification agent node that detects ambiguities and generates questions.
    
    This node:
    1. Analyzes user input for missing, incomplete, or ambiguous information
    2. Generates targeted clarification questions
    3. Updates the state with detected ambiguities and questions
    
    Args:
        state: Current agent state containing user input and context
        
    Returns:
        Updated state with clarification questions and ambiguities
    """
    user_input = state.get("user_input", "")
    conversation_history = state.get("conversation_history", [])
    extracted_fields = state.get("extracted_fields", {})
    
    # Initialize the ambiguity detector
    detector = AmbiguityDetector()
    
    # Build context for detection
    context = {
        "conversation_history": conversation_history,
        "extracted_fields": extracted_fields
    }
    
    # Detect ambiguities
    ambiguities = detector.detect_ambiguities(user_input, context)
    
    # Generate clarification questions
    clarification_questions = detector.generate_clarification_questions(ambiguities)
    
    # Prepare ambiguity summary
    ambiguity_summary = [
        {
            "type": amb.type,
            "field": amb.field,
            "reason": amb.reason,
            "severity": amb.severity,
            "suggestion": amb.suggestion
        }
        for amb in ambiguities
    ]
    
    # Determine if clarification is needed
    needs_clarification = len(clarification_questions) > 0
    
    # Generate response message
    if needs_clarification:
        response = "I'd like to clarify a few points to ensure I capture your requirements accurately:\n\n"
        for i, question in enumerate(clarification_questions, 1):
            response += f"{i}. {question}\n"
    else:
        response = "Thank you! Your requirements are clear. I'll proceed with processing them."
    
    # Update state
    return {
        "clarification_questions": clarification_questions,
        "ambiguities": ambiguity_summary,
        "needs_clarification": needs_clarification,
        "output": response,
        "last_node": "clarification"
    }


def should_request_clarification(state: AgentState) -> bool:
    """
    Conditional function to determine if clarification is needed.
    
    Args:
        state: Current agent state
        
    Returns:
        True if clarification questions exist, False otherwise
    """
    return state.get("needs_clarification", False)
