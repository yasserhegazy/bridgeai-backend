from typing import Dict, Any
from app.ai.state import AgentState
from app.ai.memory_service import create_memory
import logging

logger = logging.getLogger(__name__)

def memory_node(state: AgentState) -> Dict[str, Any]:
    """
    Node to store clear requirements into long-term memory.
    """
    intent = state.get("intent")
    needs_clarification = state.get("needs_clarification")
    
    # We only store if it's a requirement and fully clear (needs_clarification=False)
    if intent == "requirement" and not needs_clarification:
        db = state.get("db")
        project_id = state.get("project_id")
        user_input = state.get("user_input")
        message_id = state.get("message_id")
        
        if db and project_id and message_id:
            try:
                # Store in memory
                create_memory(
                    db=db,
                    project_id=project_id,
                    text=user_input,
                    source_type="message",
                    source_id=message_id,
                    metadata={
                        "clarity_score": state.get("clarity_score"),
                        "intent": intent
                    }
                )
                logger.info(f"Stored requirement in memory for project {project_id}")
                
                # Append confirmation to the output
                current_output = state.get("output", "")
                return {
                    "output": f"{current_output}\n\n(This requirement has been saved to project memory.)",
                    "last_node": "memory"
                }
                
            except Exception as e:
                logger.error(f"Failed to store memory: {str(e)}")
                # Don't fail the request, just log it
                return {"last_node": "memory"}
    
    # If not a requirement (greeting/question), just pass through
    return {"last_node": "memory"}
