"""Decode once; render previews and exports from the normalized original."""

from io import BytesIO
from pathlib import Path
import struct
import warnings
from math import ceil

import numpy as np
from PIL import Image, ImageCms, ImageEnhance, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from app.config import Settings
from app.schemas.images import Adjustments, Crop, Enhancement, NaturalEnhancement, RGBCurves
from app.services.curves import rgb_table
from app.services.manual import tone_table, transform, add_structure
from app.services.enhancement import analyze, apply as apply_enhancement

SRGB_PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


class ImageError(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: int | None = None):
        self.status, self.code, self.message = status, code, message
        self.retry_after = retry_after
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


def render(path: Path, adjustments: Adjustments | None, settings: Settings, *, preview: bool, quality: int | None = None,
           crop: Crop | None = None, original_size: tuple[int, int] | None = None,
           enhancement: NaturalEnhancement | None = None, curves: RGBCurves | None = None) -> bytes:
    # Validate before decoding or allocating cropped pixels. Never allow Pillow
    # to pad out-of-bounds requests or allocate a caller-selected larger image.
    if crop is not None:
        if original_size is None or crop.x + crop.width > original_size[0] or crop.y + crop.height > original_size[1]:
            raise ImageError(422, "invalid_crop", "Crop must stay inside the original photograph.")
    image = Image.open(path)
    image.load()
    if image.mode != "RGB":
        source = image
        image = source.convert("RGB")
        source.close()
    region = (0.0, 0.0, 1.0, 1.0)
    if crop is not None:
        width, height = original_size
        left = min(image.width - 1, round(crop.x * image.width / width))
        top = min(image.height - 1, round(crop.y * image.height / height))
        right = min(image.width, max(left + 1, round((crop.x + crop.width) * image.width / width)))
        bottom = min(image.height, max(top + 1, round((crop.y + crop.height) * image.height / height)))
        region = (left / image.width, top / image.height, right / image.width, bottom / image.height)
        if (left, top, right, bottom) != (0, 0, image.width, image.height):
            source = image
            image = source.crop((left, top, right, bottom))
            source.close()
    if preview:
        image.thumbnail((settings.preview_max_edge, settings.preview_max_edge), Image.Resampling.LANCZOS)
    if enhancement is not None:
        apply_enhancement(image, enhancement, region=region)
    if adjustments is not None:
        # Match Pillow's blend rounding using tiny lookup tables. Contrast uses
        # the same global luminance mean as ImageEnhance.Contrast.
        if adjustments.exposure or adjustments.highlights or adjustments.shadows or adjustments.ambience:
            image = image.point(tone_table(adjustments.exposure, adjustments.highlights, adjustments.shadows, adjustments.ambience) * 3)
        ramp = Image.frombytes("L", (256, 1), bytes(range(256)))
        if adjustments.brightness != 100:
            table = list(ImageEnhance.Brightness(ramp).enhance(adjustments.brightness / 100).get_flattened_data())
            image = image.point(table * 3)
        if adjustments.contrast != 100:
            with image.convert("L") as gray:
                mean = int(ImageStat.Stat(gray).mean[0] + .5)
            table = list(Image.blend(Image.new("L", ramp.size, mean), ramp, adjustments.contrast / 100).get_flattened_data())
            image = image.point(table * 3)
        if adjustments.saturation != 100:
            for top in range(0, image.height, 64):
                with image.crop((0, top, image.width, min(top + 64, image.height))) as tile:
                    image.paste(ImageEnhance.Color(tile).enhance(adjustments.saturation / 100), (0, top))
        if adjustments.warmth and adjustments.saturation:
            shift = adjustments.warmth * 0.4
            values = np.arange(256, dtype=np.float32)
            red = np.clip(values + shift, 0, 255).astype(np.uint8).tolist()
            blue = np.clip(values - shift, 0, 255).astype(np.uint8).tolist()
            image = image.point(red + list(range(256)) + blue)
        if adjustments.tint:
            # Positive tint adds magenta; negative tint adds green.
            shift = adjustments.tint * 0.4
            values = np.arange(256, dtype=np.float32)
            red_blue = np.clip(values + shift * 0.5, 0, 255).astype(np.uint8).tolist()
            green = np.clip(values - shift, 0, 255).astype(np.uint8).tolist()
            image = image.point(red_blue + green + red_blue)
        if curves is not None:
            image = image.point(rgb_table(curves))
        image = add_structure(image, adjustments.structure)
        if adjustments.sharpness:
            radius = max(0.5, max(image.size) / 1600)
            # Read overlapping source tiles into a separate destination so each
            # blur sees unchanged neighbours, including across tile boundaries.
            halo = ceil(radius * 4) + 8
            sharpened = Image.new("RGB", image.size)
            for top in range(0, image.height, 64):
                bottom = min(top + 64, image.height)
                start, stop = max(0, top - halo), min(image.height, bottom + halo)
                with image.crop((0, start, image.width, stop)) as tile:
                    filtered = tile.filter(ImageFilter.UnsharpMask(radius=radius, percent=adjustments.sharpness * 2, threshold=3))
                    sharpened.paste(filtered.crop((0, top - start, image.width, bottom - start)), (0, top))
            image.close()
            image = sharpened
        if adjustments.vignette:
            width, height = image.size
            # Preserve global coordinates and float64 rounding, but bound the
            # working arrays to 64 rows instead of allocating full-frame floats.
            x = np.linspace(-1, 1, width)[None, :]
            y = np.linspace(-1, 1, height)[:, None]
            for top in range(0, height, 64):
                bottom = min(top + 64, height)
                mask = 1 - (adjustments.vignette / 100) * np.clip((x*x + y[top:bottom]*y[top:bottom]) / 2, 0, 1) * 0.7
                with image.crop((0, top, width, bottom)) as tile:
                    pixels = np.asarray(tile, dtype=np.float32) * mask[:, :, None]
                    image.paste(Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)), (0, top))
    if adjustments is not None:
        image = transform(image, adjustments)
    output = BytesIO()
    image.save(output, format="JPEG", quality=settings.jpeg_quality if quality is None else quality,
               icc_profile=SRGB_PROFILE)
    image.close()
    return output.getvalue()


def enhance(path: Path, *, detail_path: Path | None = None) -> Enhancement:
    return analyze(path, detail_path=detail_path)
