"""Decode once; render previews and exports from the normalized original."""

from io import BytesIO
from pathlib import Path
import struct
import warnings

import numpy as np
from PIL import Image, ImageCms, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError

from app.config import Settings
from app.schemas.images import Adjustments, Enhancement


class ImageError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
        super().__init__(message)


def normalize(data: bytes, filename: str, settings: Settings) -> tuple[Image.Image, str]:
    expected = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}.get(Path(filename).suffix.lower())
    if expected is None:
        raise ImageError(415, "unsupported_format", "Choose a still JPG, PNG or WebP.")
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("error", category=UserWarning, module=r"PIL\.")
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                detected = source.format
                if detected != expected or getattr(source, "n_frames", 1) != 1:
                    raise ImageError(415, "unsupported_format", "Choose a still image with a matching file extension.")
                width, height = source.size
                if width * height > settings.max_image_pixels or max(width, height) > settings.max_image_side:
                    raise ImageError(413, "image_too_large", "Image dimensions exceed the supported limits.")
                source.verify()
            with Image.open(BytesIO(data)) as source:
                source.load()
                image = ImageOps.exif_transpose(source)
                alpha = image.convert("RGBA").getchannel("A") if image.mode in {"RGBA", "LA", "P"} else None
                profile = source.info.get("icc_profile")
                if profile:
                    image = ImageCms.profileToProfile(image, ImageCms.ImageCmsProfile(BytesIO(profile)), ImageCms.createProfile("sRGB"), outputMode="RGB")
                else:
                    image = image.convert("RGB")
                if alpha is not None:
                    background = Image.new("RGB", image.size, "white")
                    background.paste(image, mask=alpha)
                    image = background
                image.info.clear()
                return image, detected
    except ImageError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ImageError(413, "image_too_large", "Image dimensions exceed the supported limits.") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, struct.error, UserWarning, ImageCms.PyCMSError):
        raise ImageError(422, "invalid_image", "Unable to decode this photograph.") from None


def render(path: Path, adjustments: Adjustments | None, settings: Settings, *, preview: bool, quality: int | None = None) -> bytes:
    with Image.open(path) as source:
        image = source.convert("RGB")
    if preview:
        image.thumbnail((settings.preview_max_edge, settings.preview_max_edge), Image.Resampling.LANCZOS)
    if adjustments is not None:
        image = ImageEnhance.Brightness(image).enhance(adjustments.brightness / 100)
        image = ImageEnhance.Contrast(image).enhance(adjustments.contrast / 100)
        image = ImageEnhance.Color(image).enhance(adjustments.saturation / 100)
        if adjustments.warmth and adjustments.saturation:
            pixels = np.asarray(image, dtype=np.float32).copy()
            shift = adjustments.warmth * 0.4
            pixels[:, :, 0] += shift
            pixels[:, :, 2] -= shift
            image = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
        if adjustments.sharpness:
            image = image.filter(ImageFilter.UnsharpMask(
                radius=max(0.5, max(image.size) / 1600), percent=adjustments.sharpness * 2, threshold=3,
            ))
        if adjustments.vignette:
            width, height = image.size
            y, x = np.ogrid[-1:1:complex(height), -1:1:complex(width)]
            mask = 1 - (adjustments.vignette / 100) * np.clip((x*x + y*y) / 2, 0, 1) * 0.7
            pixels = np.asarray(image, dtype=np.float32) * mask[:, :, None]
            image = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
    output = BytesIO()
    image.save(output, format="JPEG", quality=settings.jpeg_quality if quality is None else quality)
    return output.getvalue()


def enhance(path: Path) -> Enhancement:
    with Image.open(path) as source:
        image = source.convert("RGB")
        image.thumbnail((512, 512))
    import cv2

    pixels = np.asarray(image)
    gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV)
    mean, spread = float(gray.mean()), float(gray.std())
    channels = pixels.mean(axis=(0, 1))
    values = Adjustments(
        brightness=int(np.clip(100 + (128 - mean) * 0.25, 80, 125)),
        contrast=int(np.clip(100 + (50 - spread) * 0.4, 90, 120)),
        saturation=int(np.clip(100 + (90 - float(hsv[:, :, 1].mean())) * 0.15, 90, 115)),
        warmth=int(np.clip((channels[2] - channels[0]) * 0.1, -15, 15)),
        sharpness=0, vignette=0,
    )
    return Enhancement(adjustments=values, message="Suggested light and colour adjustments are ready for preview.")
