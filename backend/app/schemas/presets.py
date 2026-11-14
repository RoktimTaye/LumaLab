"""Complete preset definitions with the same numeric bounds as PostgreSQL."""

from pydantic import BaseModel, ConfigDict, Field


class Preset(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    preset_id: str
    preset_name: str
    description: str
    brightness: int = Field(ge=0, le=200)
    contrast: int = Field(ge=0, le=200)
    saturation: int = Field(ge=0, le=200)
    warmth: int = Field(ge=-50, le=50)
    sharpness: int = Field(ge=0, le=100)
    vignette: int = Field(ge=0, le=100)
