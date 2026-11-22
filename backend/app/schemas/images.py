"""Contracts for temporary image editing."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Adjustments(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    brightness: int = Field(ge=0, le=200)
    contrast: int = Field(ge=0, le=200)
    saturation: int = Field(ge=0, le=200)
    warmth: int = Field(ge=-50, le=50)
    sharpness: int = Field(ge=0, le=100)
    vignette: int = Field(ge=0, le=100)


class Crop(BaseModel):
    """Rectangle in oriented original-image pixels; bounds checked against the session."""
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    x: int = Field(ge=0, le=10_000)
    y: int = Field(ge=0, le=10_000)
    width: int = Field(ge=1, le=10_000)
    height: int = Field(ge=1, le=10_000)


class NaturalEnhancement(BaseModel):
    """Bounded, source-derived photographic transform; manual controls follow it."""
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, allow_inf_nan=False)

    version: Literal["natural-v1", "natural-v2", "natural-v3"] = "natural-v1"
    strength: float = Field(default=1.0, ge=0, le=1)
    exposure_ev: float = Field(default=0.0, ge=-1.25, le=1.25)
    shadows: float = Field(default=0.0, ge=0, le=0.6)
    highlights: float = Field(default=0.0, ge=0, le=0.6)
    contrast: float = Field(default=0.0, ge=0, le=0.2)
    vibrance: float = Field(default=0.0, ge=0, le=0.15)
    red_gain: float = Field(default=1.0, ge=0.9, le=1.1)
    green_gain: float = Field(default=1.0, ge=0.9, le=1.1)
    blue_gain: float = Field(default=1.0, ge=0.9, le=1.1)
    black_point: float = Field(default=0.0, ge=0, le=0.08)
    white_lift: float = Field(default=0.0, ge=0, le=0.12)
    tone_contrast: float = Field(default=0.0, ge=-0.2, le=0.3)
    clarity: float = Field(default=0.0, ge=0, le=0.3)
    texture: float = Field(default=0.0, ge=0, le=0.6)
    microcontrast: float = Field(default=0.0, ge=0, le=0.35)
    detail_noise: float = Field(default=0.0, ge=0, le=0.1)
    detail_reference_edge: int = Field(default=1600, ge=1, le=10_000)
    hue_chroma: list[Annotated[float, Field(ge=-0.3, le=0.2)]] = Field(default_factory=list, max_length=6)
    local_exposure: list[Annotated[float, Field(ge=-0.6, le=0.6)]] = Field(default_factory=list, max_length=64)
    base_luminance: list[Annotated[float, Field(ge=0, le=1)]] = Field(default_factory=list, max_length=1024)

    @model_validator(mode="after")
    def validate_photographic_fields(self) -> "NaturalEnhancement":
        for name, length in (("hue_chroma", 6), ("local_exposure", 64), ("base_luminance", 1024)):
            if len(getattr(self, name)) not in (0, length):
                raise ValueError(f"{name} must be empty or contain exactly {length} values")
        active = (self.black_point or self.white_lift or self.tone_contrast or self.clarity
                  or self.hue_chroma or self.local_exposure or self.base_luminance)
        if self.version == "natural-v1" and active:
            raise ValueError("spatial and photographic controls require natural-v2")
        if self.clarity and not self.base_luminance:
            raise ValueError("clarity requires the source-derived luminance guide")
        if self.version != "natural-v3" and (self.texture or self.microcontrast or self.detail_noise):
            raise ValueError("source-scale texture controls require natural-v3")
        return self


class EnhancementFinding(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    area: Literal["light", "contrast", "color", "detail"]
    issue: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=200)
    observation: str = Field(default="", max_length=180)


class PreviewRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    revision: int = Field(ge=0, description="Client revision echoed in the X-Image-Revision response header.")
    adjustments: Adjustments
    crop: Crop | None = None
    enhancement: NaturalEnhancement | None = None


class ExportRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    adjustments: Adjustments
    crop: Crop | None = None
    enhancement: NaturalEnhancement | None = None
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
    recipe: NaturalEnhancement | None = None
    assessment: list[EnhancementFinding] = Field(default_factory=list, max_length=8)
