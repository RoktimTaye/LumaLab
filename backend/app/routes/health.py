import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.db.pool import database_available
from app.schemas.errors import UnavailableError, UnavailableResponse
from app.schemas.health import HealthResponse
from app.storage.runtime import storage_available

router = APIRouter()
logger = logging.getLogger("lumalab")


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": UnavailableResponse, "description": "A required resource is unavailable"}},
    summary="Check database and temporary-storage readiness",
)
def health(request: Request, response: Response):
    state = request.app.state
    headers = {"Cache-Control": "no-store"}
    failure = None
    if not storage_available(getattr(state, "storage_dir", None)):
        failure = "readiness_storage_unavailable"
    elif not database_available(
        getattr(state, "db_pool", None), state.settings.database_timeout_seconds
    ):
        failure = "readiness_database_unavailable"
    if failure:
        logger.warning(failure)
        return JSONResponse(
            status_code=503,
            content=UnavailableResponse(error=UnavailableError()).model_dump(),
            headers=headers,
        )
    response.headers.update(headers)
    return HealthResponse()

