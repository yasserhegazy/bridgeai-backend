"""
Clarification Node Module (LLM-Powered)

This node uses the LLM ambiguity detector to:
- Analyze requirement clarity
- Detect ambiguities dynamically
- Generate clarification questions
- Update AgentState for LangGraph
"""

from typing import Dict, Any
from app.ai.state import AgentState
from app.ai.nodes.clarification.llm_ambiguity_detector import LLMAmbiguityDetector


def clarification_node(state: AgentState) -> Dict[str, Any]:

    user_input = state.get("user_input", "")
    conversation_history = state.get("conversation_history", [])
    extracted_fields = state.get("extracted_fields", {})

    # Build context
    context = {
        "conversation_history": conversation_history,
        "extracted_fields": extracted_fields
    }

    # Initialize pure LLM detector
    detector = LLMAmbiguityDetector()

    # Perform full LLM analysis
    result = detector.analyze_and_generate_questions(user_input, context)

    ambiguities = result["ambiguities"]
    clarification_questions = result["clarification_questions"]
    clarity_score = result["clarity_score"]
    summary = result["summary"]
    needs_clarification = result["needs_clarification"]

    # Build ambiguity summary for API
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

    # Build response message
    if needs_clarification:
        response = (
            "I'd like to clarify a few points to ensure the requirements are fully understood:\n\n"
        )
        for i, q in enumerate(clarification_questions, 1):
            response += f"{i}. {q}\n"
    else:
        response = (
            f"Your requirements look clear! (Clarity Score: {clarity_score}/100)\n"
            "Proceeding to the next step."
        )

    return {
        "clarification_questions": clarification_questions,
        "ambiguities": ambiguity_summary,
        "needs_clarification": needs_clarification,
        "clarity_score": clarity_score,
        "quality_summary": summary,
        "output": response,
        "last_node": "clarification"
    }


def should_request_clarification(state: AgentState) -> bool:
    """Routing function for LangGraph."""
    return state.get("needs_clarification", False)
