from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict, total=False):
    # User input and conversation
    user_input: str
    output: Optional[str]
    conversation_history: List[str]
    
    # Clarification agent fields
    clarification_questions: List[str]
    ambiguities: List[Dict[str, Any]]
    needs_clarification: bool
    
    # Extracted information
    extracted_fields: Dict[str, Any]
    
    # Workflow tracking
    last_node: Optional[str]
    next_action: Optional[str]
