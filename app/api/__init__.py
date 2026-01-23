from fastapi import APIRouter

from . import (
    ai,
    auth,
    chats,
    comments,
    crs,
    exports,
    invitations,
    memory,
    notifications,
    projects,
    suggestions,
    teams,
)

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(crs.router, prefix="/crs", tags=["crs"])
router.include_router(comments.router, prefix="/comments", tags=["comments"])
router.include_router(teams.router, prefix="/teams", tags=["teams"])
router.include_router(invitations.router, prefix="/invitation", tags=["invitations"])
router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)
router.include_router(ai.router, prefix="/ai", tags=["ai"])
# Chat endpoints are nested under projects: /api/projects/{project_id}/chats
router.include_router(chats.router, prefix="/projects", tags=["chats"])
router.include_router(exports.router, prefix="/projects", tags=["exports"])
router.include_router(memory.router, tags=["memory"])
router.include_router(suggestions.router, tags=["suggestions"])
router.include_router(comments.router, tags=["comments"])
