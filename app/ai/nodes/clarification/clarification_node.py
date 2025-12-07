"""
Clarification Node using Groq LLM for requirement ambiguity detection.
"""

from typing import Dict, Any
from app.ai.state import AgentState
from app.ai.nodes.clarification.llm_ambiguity_detector import LLMAmbiguityDetector


def clarification_node(state: AgentState) -> Dict[str, Any]:
    user_input = state.get("user_input", "")
    conversation_history = state.get("conversation_history", [])
    extracted_fields = state.get("extracted_fields", {})

    # Build context payload
    context = {
        "conversation_history": conversation_history,
        "extracted_fields": extracted_fields
    }

    # Run Groq-powered ambiguity detection
    detector = LLMAmbiguityDetector()
    result = detector.analyze_and_generate_questions(user_input, context)

    ambiguities = result["ambiguities"]
    clarification_questions = result["clarification_questions"]
    clarity_score = result["clarity_score"]
    summary = result["summary"]
    needs_clarification = result["needs_clarification"]

    # Build response message
    if needs_clarification:
        response = "I'd like to clarify a few points:\n\n"
        for i, q in enumerate(clarification_questions, 1):
            response += f"{i}. {q}\n"
    else:
        response = f"Your requirements are clear. (Clarity Score: {clarity_score}/100)"

    # Update state and return
    return {
        "clarification_questions": clarification_questions,
        "ambiguities": [
            {
                "type": a.type,
                "field": a.field,
                "reason": a.reason,
                "severity": a.severity,
                "suggestion": a.suggestion
            }
            for a in ambiguities
        ],
        "needs_clarification": needs_clarification,
        "clarity_score": clarity_score,
        "quality_summary": summary,
        "output": response,
        "last_node": "clarification"
    }


def should_request_clarification(state: AgentState) -> bool:
    return state.get("needs_clarification", False)
