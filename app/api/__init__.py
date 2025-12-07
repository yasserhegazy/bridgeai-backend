from fastapi import APIRouter
from . import auth, projects, crs, teams, invitations, notifications, ai, memory


router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(crs.router, prefix="/crs", tags=["crs"])
router.include_router(teams.router, prefix="/teams", tags=["teams"])
router.include_router(invitations.router, prefix="/invitation", tags=["invitations"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
router.include_router(memory.router, tags=["memory"])