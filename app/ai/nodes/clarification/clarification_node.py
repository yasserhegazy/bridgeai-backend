"""
Clarification Node using Groq LLM for requirement ambiguity detection.
Integrates memory search to provide context from previous interactions.
"""

from typing import Dict, Any, Optional
from app.ai.state import AgentState
from app.ai.nodes.clarification.llm_ambiguity_detector import LLMAmbiguityDetector


def clarification_node(state: AgentState) -> Dict[str, Any]:
    user_input = state.get("user_input", "")
    conversation_history = state.get("conversation_history", [])
    extracted_fields = state.get("extracted_fields", {})
    project_id = state.get("project_id")
    db = state.get("db")  # Optional: database session for memory lookup

    # Build context payload
    context = {
        "conversation_history": conversation_history,
        "extracted_fields": extracted_fields
    }
    
    # Enrich context with relevant memories if available
    if db and project_id:
        try:
            from app.ai.memory_service import search_project_memories
            relevant_memories = search_project_memories(
                db=db,
                project_id=project_id,
                query=user_input,
                limit=3,
                similarity_threshold=0.2
            )
            context["relevant_memories"] = [
                {
                    "text": m["text"],
                    "source_type": m["source_type"],
                    "similarity": m["similarity_score"]
                }
                for m in relevant_memories
            ]
        except Exception as e:
            # Gracefully handle memory lookup failures
            context["relevant_memories"] = []

    # Run Groq-powered ambiguity detection
    detector = LLMAmbiguityDetector()
    result = detector.analyze_and_generate_questions(user_input, context)

    ambiguities = result["ambiguities"]
    clarification_questions = result["clarification_questions"]
    clarity_score = result["clarity_score"]
    summary = result["summary"]
    needs_clarification = result["needs_clarification"]

    intent = result.get("intent", "requirement")

    # Build response message
    if needs_clarification:
        response = "I'd like to clarify a few points:\n\n"
        for i, q in enumerate(clarification_questions, 1):
            response += f"{i}. {q}\n"
    elif intent == "greeting":
        response = "Hello! How can I help you with your project requirements today?"
    elif intent == "question":
        response = "I am a Business Analyst AI assistant. I can help you define and clarify your project requirements. Please describe what you'd like to build."
    elif intent == "deferral":
        response = "Understood. We will skip those details for now."
    else:
        # Default for clear requirements
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