from fastapi import APIRouter
from . import auth, projects, crs


router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(crs.router, prefix="/crs", tags=["crs"])