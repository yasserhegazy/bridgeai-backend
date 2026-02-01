"""
API endpoints for creative suggestions
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.memory_service import search_project_memories
from app.ai.nodes.suggestions.llm_suggestions_generator import (
    generate_creative_suggestions,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


# ============= Schemas =============
class SuggestionsRequest(BaseModel):
    project_id: int
    context: Optional[str] = None  # Additional context from user
    categories: Optional[List[str]] = None  # Specific categories to focus on


class SuggestionResponse(BaseModel):
    category: str
    title: str
    description: str
    value_proposition: str
    complexity: str
    priority: str


# ============= Endpoints =============


@router.post("/generate", response_model=List[SuggestionResponse])
def generate_suggestions_endpoint(
    request: SuggestionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate creative suggestions for additional features and scenarios

    Analyzes project context and proposes:
    - Additional features that complement existing requirements
    - Alternative scenarios and use cases
    - Integration possibilities
    - Enhancement opportunities
    """
    try:
        # Gather project context
        project_context = _gather_project_context(
            db=db, project_id=request.project_id, user_context=request.context or ""
        )

        # Generate suggestions
        suggestions = generate_creative_suggestions(
            project_context=project_context,
            current_input=request.context
            or "Generate creative suggestions for this project",
        )

        # Filter by categories if specified
        if request.categories:
            suggestions = [
                s
                for s in suggestions
                if s.get("category", "").upper()
                in [c.upper() for c in request.categories]
            ]

        return suggestions

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate suggestions: {str(e)}"
        )


@router.get("/categories")
def get_suggestion_categories():
    """
    Get available suggestion categories
    """
    return {
        "categories": [
            {
                "name": "ADDITIONAL_FEATURES",
                "description": "New functionality that complements existing requirements",
            },
            {
                "name": "ALTERNATIVE_SCENARIOS",
                "description": "Different ways users might interact with the system",
            },
            {
                "name": "INTEGRATION_OPPORTUNITIES",
                "description": "Ways to connect with other systems or services",
            },
            {
                "name": "ENHANCEMENT_IDEAS",
                "description": "Improvements to existing functionality",
            },
            {
                "name": "FUTURE_CONSIDERATIONS",
                "description": "Features for potential future phases",
            },
        ]
    }


def _gather_project_context(
    db: Session, project_id: int, user_context: str
) -> Dict[str, Any]:
    """Gather comprehensive project context for suggestion generation"""
    context = {
        "project_id": project_id,
        "current_input": user_context,
        "existing_requirements": [],
        "features": [],
        "use_cases": [],
        "technical_details": [],
    }

    try:
        # Search for existing CRS documents
        crs_memories = search_project_memories(
            db=db,
            project_id=project_id,
            query="requirements specification functional non-functional",
            limit=10,
            similarity_threshold=0.2,
        )

        # Search for feature-related memories
        feature_memories = search_project_memories(
            db=db,
            project_id=project_id,
            query="feature functionality capability module component",
            limit=10,
            similarity_threshold=0.2,
        )

        # Search for use case memories
        usecase_memories = search_project_memories(
            db=db,
            project_id=project_id,
            query="use case scenario workflow process user story",
            limit=10,
            similarity_threshold=0.2,
        )

        # Categorize memories
        context["existing_requirements"] = [m["text"] for m in crs_memories]
        context["features"] = [m["text"] for m in feature_memories]
        context["use_cases"] = [m["text"] for m in usecase_memories]

        # Get technical context
        tech_memories = search_project_memories(
            db=db,
            project_id=project_id,
            query="technology stack architecture database API integration",
            limit=5,
            similarity_threshold=0.3,
        )
        context["technical_details"] = [m["text"] for m in tech_memories]

    except Exception:
        # Continue with empty context if memory search fails
        pass

    return context
