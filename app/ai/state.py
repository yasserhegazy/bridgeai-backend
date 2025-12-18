from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict, total=False):
    user_input: str
    output: Optional[str]
    conversation_history: List[str]

    # Clarification Agent fields
    clarification_questions: List[str]
    ambiguities: List[Dict[str, Any]]
    needs_clarification: bool

    clarity_score: int
    quality_summary: str

    extracted_fields: Dict[str, Any]

    # Template Filler Agent fields (CRS)
    crs_content: Optional[str]  # JSON string of filled CRS template
    crs_template: Optional[Dict[str, Any]]  # Dictionary representation of CRS
    summary_points: Optional[List[str]]  # Key summary points from CRS
    crs_is_complete: bool  # Whether CRS has sufficient information

    # Workflow control
    last_node: Optional[str]
    next_action: Optional[str]
    
    # Memory and context
    project_id: Optional[int]
    db: Optional[Any]  # SQLAlchemy Session for memory queries
    message_id: Optional[int]
    intent: Optional[str]
