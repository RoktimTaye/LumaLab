"""Typed API error envelopes."""

from typing import Literal

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class UnavailableError(BaseModel):
    code: Literal["service_unavailable"] = "service_unavailable"
    message: str = "Database or temporary storage is unavailable."


class UnavailableResponse(BaseModel):
    error: UnavailableError
