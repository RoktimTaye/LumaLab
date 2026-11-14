"""Safe JSON errors for request validation, routing and unexpected failures."""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas.errors import ErrorDetail, ErrorResponse


def error_response(status: int, code: str, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, headers={**(headers or {}), "Cache-Control": "no-store"},
        content=ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump(),
    )


async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    return error_response(422, "invalid_request", "Check the request fields and values.")


async def http_error(request: Request, error: HTTPException) -> JSONResponse:
    code, message = {
        400: ("invalid_request", "Unable to parse the request."),
        401: ("unauthorized", "Valid authorization is required."),
        403: ("forbidden", "This request is not allowed."),
        404: ("not_found", "The requested resource is unavailable."),
        405: ("method_not_allowed", "This HTTP method is not allowed."),
        413: ("request_too_large", "The request exceeds the supported limits."),
        415: ("unsupported_media_type", "The request media type is not supported."),
        422: ("invalid_request", "Check the request fields and values."),
        429: ("capacity_exceeded", "The service is busy. Try again shortly."),
        500: ("internal_error", "Unable to complete the request."),
        503: ("service_unavailable", "The service is temporarily unavailable."),
    }.get(error.status_code, ("request_failed", "Unable to complete the request."))
    headers = {name: value for name, value in (error.headers or {}).items()
               if name.lower() in {"allow", "www-authenticate", "retry-after"}}
    return error_response(error.status_code, code, message, headers)


async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logging.getLogger("lumalab").error("request_failed")
    return error_response(500, "internal_error", "Unable to complete the request.")


EXCEPTION_HANDLERS = {
    RequestValidationError: validation_error,
    HTTPException: http_error,
    Exception: unexpected_error,
}
