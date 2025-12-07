from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.ai.state import AgentState
from app.ai.graph import create_graph

router = APIRouter()
graph = create_graph()


class RequirementInput(BaseModel):
    user_input: str
    conversation_history: Optional[List[str]] = []
    extracted_fields: Optional[Dict[str, Any]] = {}


class ClarificationResponse(BaseModel):
    output: str
    clarification_questions: List[str]
    ambiguities: List[Dict[str, Any]]
    needs_clarification: bool
    clarity_score: Optional[int] = None
    quality_summary: Optional[str] = None
    last_node: Optional[str] = None


@router.post("/analyze-requirements", response_model=ClarificationResponse)
def analyze_requirements(req: RequirementInput):
    try:
        state: AgentState = {
            "user_input": req.user_input,
            "conversation_history": req.conversation_history,
            "extracted_fields": req.extracted_fields
        }

        result = graph.invoke(state)

        return ClarificationResponse(
            output=result.get("output", ""),
            clarification_questions=result.get("clarification_questions", []),
            ambiguities=result.get("ambiguities", []),
            needs_clarification=result.get("needs_clarification", False),
            clarity_score=result.get("clarity_score"),
            quality_summary=result.get("quality_summary"),
            last_node=result.get("last_node")
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error analyzing requirements: {str(e)}", exc_info=True)
        
        # Return a graceful error response
        return ClarificationResponse(
            output=f"Sorry, there was an error analyzing your requirements: {str(e)}",
            clarification_questions=[],
            ambiguities=[],
            needs_clarification=False,
            clarity_score=0,
            quality_summary=f"Error: {str(e)}",
            last_node="error"
        )
