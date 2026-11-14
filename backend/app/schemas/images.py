"""Contracts for temporary image editing."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Adjustments(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    brightness: int = Field(ge=0, le=200)
    contrast: int = Field(ge=0, le=200)
    saturation: int = Field(ge=0, le=200)
    warmth: int = Field(ge=-50, le=50)
    sharpness: int = Field(ge=0, le=100)
    vignette: int = Field(ge=0, le=100)


class PreviewRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    revision: int = Field(ge=0, description="Client revision echoed in the X-Image-Revision response header.")
    adjustments: Adjustments


class ExportRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    adjustments: Adjustments
    format: Literal["jpeg"] = "jpeg"
    quality: Literal[92] = 92


class UploadedImage(BaseModel):
    image_id: str = Field(pattern=r"^[0-9a-f]{32}$", description="Opaque session identifier; not a storage path.")
    access_token: str = Field(min_length=1, description="Private bearer token for this image; send only in Authorization headers.")
    filename: str = Field(description="Display filename, without submitted directory components.")
    format: Literal["JPEG", "PNG", "WEBP"]
    width: int = Field(gt=0, description="Width in pixels after EXIF orientation.")
    height: int = Field(gt=0, description="Height in pixels after EXIF orientation.")
    expires_at: AwareDatetime = Field(description="Fixed session expiry as a timezone-aware timestamp.")


class Enhancement(BaseModel):
    adjustments: Adjustments
    message: str
