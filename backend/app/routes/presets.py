"""Public, read-only preset retrieval."""

import logging

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from psycopg import Error

from app.db.presets import get_presets
from app.schemas.errors import UnavailableError, UnavailableResponse
from app.schemas.presets import Preset

router = APIRouter()
logger = logging.getLogger("lumalab")


@router.get(
    "/presets",
    response_model=list[Preset],
    responses={503: {"model": UnavailableResponse, "description": "Preset definitions unavailable"}},
    summary="List the five built-in presets in studio display order",
)
def presets(request: Request, response: Response):
    headers = {"Cache-Control": "no-store"}
    try:
        definitions = get_presets(
            getattr(request.app.state, "db_pool", None),
            request.app.state.settings.database_timeout_seconds,
        )
    except (Error, ValueError):
        logger.warning("presets_unavailable")
        return JSONResponse(
            status_code=503,
            content=UnavailableResponse(error=UnavailableError(
                message="Presets are temporarily unavailable.",
            )).model_dump(),
            headers=headers,
        )
    response.headers.update(headers)
    return definitions
