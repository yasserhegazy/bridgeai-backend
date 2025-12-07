from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict, total=False):
    user_input: str
    output: Optional[str]
    conversation_history: List[str]

    clarification_questions: List[str]
    ambiguities: List[Dict[str, Any]]
    needs_clarification: bool

    clarity_score: int
    quality_summary: str

    extracted_fields: Dict[str, Any]

    last_node: Optional[str]
    next_action: Optional[str]
