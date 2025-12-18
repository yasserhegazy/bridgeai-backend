"""
Memory utilities for AI workflows
Provides convenient helper functions for common memory operations
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.ai.memory_service import (
    create_memory,
    search_project_memories,
    get_project_memory_summary
)


def enrich_state_with_memories(
    db: Session,
    project_id: int,
    user_input: str,
    max_memories: int = 3,
    threshold: float = 0.25
) -> Dict[str, Any]:
    """
    Enrich agent state with relevant memories for a given input
    
    Args:
        db: Database session
        project_id: Project to search memories in
        user_input: User's input/query
        max_memories: Maximum memories to retrieve
        threshold: Minimum similarity threshold (0-1)
    
    Returns:
        Dictionary with relevant memories and summary
    """
    try:
        memories = search_project_memories(
            db=db,
            project_id=project_id,
            query=user_input,
            limit=max_memories,
            similarity_threshold=threshold
        )
        
        return {
            "has_context": len(memories) > 0,
            "context_count": len(memories),
            "memories": memories,
            "context_summary": _summarize_memories(memories)
        }
    except Exception as e:
        return {
            "has_context": False,
            "context_count": 0,
            "memories": [],
            "error": str(e)
        }


def _summarize_memories(memories: List[Dict[str, Any]]) -> str:
    """Create a text summary of memories for the AI"""
    if not memories:
        return "No relevant past context found."
    
    summary_parts = [f"Found {len(memories)} relevant past interactions:"]
    for i, mem in enumerate(memories, 1):
        source = mem.get("source_type", "unknown")
        similarity = mem.get("similarity_score", 0)
        text_preview = mem.get("text", "")[:100] + "..."
        summary_parts.append(
            f"{i}. [{source}] (relevance: {similarity:.0%}) {text_preview}"
        )
    
    return "\n".join(summary_parts)


def store_clarification_result(
    db: Session,
    project_id: int,
    user_input: str,
    clarification_questions: List[str],
    clarity_score: int
) -> Optional[str]:
    """
    Store the clarification interaction as a memory
    Useful for learning from past clarifications
    
    Args:
        db: Database session
        project_id: Project ID
        user_input: Original user input
        clarification_questions: Questions that were asked
        clarity_score: Score indicating how clear the requirement was
    
    Returns:
        Memory ID if successful, None otherwise
    """
    if clarity_score >= 70:  # Only store if clarity was questionable
        return None
    
    text = f"Clarification needed: {user_input}\nQuestions asked: {', '.join(clarification_questions)}"
    
    memory = create_memory(
        db=db,
        project_id=project_id,
        text=text,
        source_type="summary",
        source_id=0,
        metadata={
            "clarity_score": clarity_score,
            "question_count": len(clarification_questions),
            "original_input": user_input
        }
    )
    
    return memory.embedding_id if memory else None


def get_project_context_stats(
    db: Session,
    project_id: int
) -> Dict[str, Any]:
    """
    Get comprehensive statistics about a project's memory context
    
    Args:
        db: Database session
        project_id: Project ID
    
    Returns:
        Statistics dictionary
    """
    summary = get_project_memory_summary(db, project_id)
    
    return {
        "project_id": project_id,
        "total_memories": summary.get("total_memories", 0),
        "memory_sources": summary.get("by_source_type", {}),
        "date_range": {
            "oldest": summary.get("oldest_memory"),
            "newest": summary.get("newest_memory")
        },
        "coverage": {
            "has_crs_context": "crs" in summary.get("by_source_type", {}),
            "has_message_context": "message" in summary.get("by_source_type", {}),
            "has_comment_context": "comment" in summary.get("by_source_type", {}),
            "has_summary_context": "summary" in summary.get("by_source_type", {})
        }
    }
