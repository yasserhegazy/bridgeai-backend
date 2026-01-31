"""
API endpoints for memory management
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.memory_service import (
    create_memory,
    delete_memory,
    get_project_memory_summary,
    retrieve_memory,
    search_project_memories,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/memory", tags=["memory"])


# ============= Schemas =============
class MemoryCreateRequest(BaseModel):
    project_id: int
    text: str
    source_type: str  # crs, message, comment, summary
    source_id: int
    metadata: Optional[Dict[str, Any]] = None


class MemorySearchRequest(BaseModel):
    project_id: int
    query: str
    limit: int = 5
    similarity_threshold: float = 0.3


# ============= Endpoints =============


@router.post("/create")
def create_memory_endpoint(
    request: MemoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Store a new memory (text + embedding)

    The memory is stored in:
    - MySQL: metadata and indexing
    - ChromaDB: actual text with embeddings for semantic search
    """
    try:
        memory = create_memory(
            db=db,
            project_id=request.project_id,
            text=request.text,
            source_type=request.source_type,
            source_id=request.source_id,
            metadata=request.metadata,
        )

        if not memory:
            raise HTTPException(status_code=500, detail="Failed to create memory")

        return {
            "status": "success",
            "memory_id": memory.id,
            "embedding_id": memory.embedding_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrieve/{embedding_id}")
def retrieve_memory_endpoint(
    embedding_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific memory by embedding ID
    """
    memory = retrieve_memory(db, embedding_id)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@router.post("/search")
def search_memories_endpoint(
    request: MemorySearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search project memories using semantic search

    Returns the most relevant memories based on semantic similarity
    to your query, ranked by similarity score.
    """
    results = search_project_memories(
        db=db,
        project_id=request.project_id,
        query=request.query,
        limit=request.limit,
        similarity_threshold=request.similarity_threshold,
    )

    return {
        "status": "success",
        "query": request.query,
        "results_count": len(results),
        "results": results,
    }


@router.get("/search")
def search_memories_query_endpoint(
    project_id: int,
    query: str,
    limit: int = Query(5, ge=1, le=50),
    similarity_threshold: float = Query(0.3, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search project memories using query parameters

    Query Parameters:
    - project_id: The project to search in
    - query: Search query text
    - limit: Max results (default 5, max 50)
    - similarity_threshold: Minimum similarity score (0-1)
    """
    results = search_project_memories(
        db=db,
        project_id=project_id,
        query=query,
        limit=limit,
        similarity_threshold=similarity_threshold,
    )

    return {
        "status": "success",
        "query": query,
        "results_count": len(results),
        "results": results,
    }


@router.delete("/delete/{embedding_id}")
def delete_memory_endpoint(
    embedding_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a memory from both MySQL and ChromaDB
    """
    success = delete_memory(db, embedding_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete memory")

    return {"status": "success", "message": f"Memory {embedding_id} deleted"}


@router.get("/stats/{project_id}")
def memory_stats_endpoint(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get memory statistics for a project

    Returns:
    - Total memories count
    - Breakdown by source type (crs, message, comment, summary)
    - Date range of memories
    """
    stats = get_project_memory_summary(db, project_id)
    return stats
