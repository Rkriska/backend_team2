from fastapi import APIRouter
from app.api.v1.endpoints import projects,documents,screening
router=APIRouter(prefix='/api/v1');router.include_router(projects.router);router.include_router(documents.router);router.include_router(screening.router)
