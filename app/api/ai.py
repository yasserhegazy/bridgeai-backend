from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.ai.state import AgentState
from app.ai.nodes.echo_node import echo_node
from app.ai.graph import create_graph

router = APIRouter()

graph = create_graph()


class RequirementInput(BaseModel):
    """Request model for requirement analysis."""
    user_input: str
    conversation_history: Optional[List[str]] = []
    extracted_fields: Optional[Dict[str, Any]] = {}


class ClarificationResponse(BaseModel):
    """Response model for clarification results."""
    output: str
    clarification_questions: List[str]
    ambiguities: List[Dict[str, Any]]
    needs_clarification: bool
    last_node: Optional[str]


@router.post("/echo")
def echo(state: AgentState):
    """Legacy echo endpoint for backward compatibility."""
    result = graph.invoke(state)
    return result


@router.post("/analyze-requirements", response_model=ClarificationResponse)
def analyze_requirements(req: RequirementInput):
    """
    Analyze user requirements and detect ambiguities.
    
    This endpoint:
    1. Takes user input and conversation context
    2. Runs it through the clarification agent
    3. Returns detected ambiguities and clarification questions
    
    Args:
        req: RequirementInput containing user input and context
        
    Returns:
        ClarificationResponse with questions and ambiguities
    """
    # Prepare state
    state: AgentState = {
        "user_input": req.user_input,
        "conversation_history": req.conversation_history or [],
        "extracted_fields": req.extracted_fields or {}
    }
    
    # Run through graph
    result = graph.invoke(state)
    
    # Return structured response
    return ClarificationResponse(
        output=result.get("output", ""),
        clarification_questions=result.get("clarification_questions", []),
        ambiguities=result.get("ambiguities", []),
        needs_clarification=result.get("needs_clarification", False),
        last_node=result.get("last_node")
    )


@router.post("/process-requirement")
def process_requirement(req: RequirementInput):
    """
    Process a complete requirement through the full workflow.
    
    This endpoint runs the complete LangGraph workflow including
    clarification detection and other processing nodes.
    
    Args:
        req: RequirementInput containing user input and context
        
    Returns:
        Complete workflow result
    """
    state: AgentState = {
        "user_input": req.user_input,
        "conversation_history": req.conversation_history or [],
        "extracted_fields": req.extracted_fields or {}
    }
    
    result = graph.invoke(state)
    return result

