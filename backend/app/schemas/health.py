from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ready"] = "ready"


class UnavailableError(BaseModel):
    code: Literal["service_unavailable"] = "service_unavailable"
    message: str = "Database or temporary storage is unavailable."


class UnavailableResponse(BaseModel):
    error: UnavailableError
