"""
CRS API Module.
Aggregates all CRS endpoint routers for backward compatibility.
"""
from fastapi import APIRouter

from .crud import router as crud_router
from .workflow import router as workflow_router
from .versioning import router as versioning_router
from .export import router as export_router

# Create main router that includes all sub-routers
router = APIRouter()

# Include all CRS sub-routers
# IMPORTANT: Include routers with specific routes (like /versions, /review-queue)
# BEFORE routers with path parameters (like /{crs_id}) to avoid route conflicts
router.include_router(workflow_router, tags=["CRS Workflow"])
router.include_router(versioning_router, tags=["CRS Versioning"])
router.include_router(export_router, tags=["CRS Export"])
router.include_router(crud_router, tags=["CRS"])

# Re-export schemas for backward compatibility
from .schemas import (
    CRSPatternEnum,
    CRSCreate,
    CRSStatusUpdate,
    CRSContentUpdate,
    CRSOut,
    AuditLogOut,
    CRSPreviewOut,
)

__all__ = [
    "router",
    "CRSPatternEnum",
    "CRSCreate",
    "CRSStatusUpdate",
    "CRSContentUpdate",
    "CRSOut",
    "AuditLogOut",
    "CRSPreviewOut",
]
