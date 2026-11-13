"""HTTP route modules, collected under the versioned API prefix."""

from fastapi import APIRouter

from app.routes.health import router as health_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
