"""Public, read-only preset retrieval."""

import logging

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from psycopg import Error

from app.db.presets import get_preset, get_presets
from app.schemas.errors import ErrorResponse, UnavailableError, UnavailableResponse
from app.schemas.presets import Preset

router = APIRouter()
logger = logging.getLogger("lumalab")


@router.get(
    "/presets",
    response_model=list[Preset],
    responses={503: {"model": UnavailableResponse, "description": "Preset definitions unavailable"}},
    summary="List the complete curated preset catalogue in studio display order",
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


@router.get(
    "/presets/{preset_id}",
    response_model=Preset,
    responses={404: {"model": ErrorResponse, "description": "Preset not found"},
                422: {"model": ErrorResponse, "description": "Invalid preset ID"},
                503: {"model": UnavailableResponse, "description": "Preset definition unavailable"}},
    summary="Load one saved preset by ID",
)
def preset(preset_id: str, request: Request, response: Response):
    headers = {"Cache-Control": "no-store"}
    try:
        definition = get_preset(
            getattr(request.app.state, "db_pool", None),
            request.app.state.settings.database_timeout_seconds,
            preset_id,
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
    if definition is None:
        raise HTTPException(status_code=404)
    response.headers.update(headers)
    return definition
