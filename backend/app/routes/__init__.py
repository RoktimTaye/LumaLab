"""HTTP route modules, collected under the versioned API prefix."""

from fastapi import APIRouter

from app.routes.health import router as health_router
from app.routes.presets import router as presets_router
from app.routes.images import router as images_router
from app.schemas.errors import ErrorResponse

router = APIRouter(prefix="/api/v1", responses={
    500: {"model": ErrorResponse, "description": "Unexpected server failure; private details are omitted."},
})
router.include_router(health_router)
router.include_router(presets_router)
router.include_router(images_router)
