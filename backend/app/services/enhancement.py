"""Conservative photographic analysis and a versioned, float32 SDR transform.

This is a deterministic controller, not a pretrained retouching model. Analysis
always uses the original; rendering applies the frozen recipe at either size.
"""

from pathlib import Path

import numpy as np
from PIL import Image

from app.schemas.images import Adjustments, Enhancement, NaturalEnhancement

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
NEUTRAL = Adjustments(brightness=100, contrast=100, saturation=100, warmth=0, sharpness=0, vignette=0)


def _luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * LUMA[0] + rgb[..., 1] * LUMA[1] + rgb[..., 2] * LUMA[2]


def _extrema(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Three fixed channels: avoid the generic strided axis-reduction overhead
    # on every full-resolution strip (measured in benchmark_enhancement).
    low = np.minimum(np.minimum(rgb[..., 0], rgb[..., 1]), rgb[..., 2])
    high = np.maximum(np.maximum(rgb[..., 0], rgb[..., 1]), rgb[..., 2])
    return low, high


def to_linear(rgb: np.ndarray) -> np.ndarray:
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def to_srgb(rgb: np.ndarray) -> np.ndarray:
    return np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.maximum(rgb, 0) ** (1 / 2.4) - 0.055)


def is_identity(recipe: NaturalEnhancement) -> bool:
    return recipe.strength == 0 or (
        not any((recipe.exposure_ev, recipe.shadows, recipe.highlights, recipe.contrast, recipe.vibrance))
        and recipe.red_gain == recipe.green_gain == recipe.blue_gain == 1
        and not any((recipe.black_point, recipe.white_lift, recipe.tone_contrast, recipe.clarity))
        and not any((recipe.texture, recipe.microcontrast))
        and not any(recipe.hue_chroma) and not any(recipe.local_exposure)
    )


def _transform_v1(rgb: np.ndarray, recipe: NaturalEnhancement) -> np.ndarray:
    """Transform encoded sRGB [0,1]; retain precision until final encoding.

    All operators are pointwise with fixed source-derived parameters: no tile
    statistics, histogram equalization, or per-preview re-estimation. Luminance
    curves are monotone under the schema bounds and retain black/white endpoints.
    """
    if is_identity(recipe):
        return rgb.copy()
    amount = recipe.strength
    linear = to_linear(rgb)
    gains = np.array([recipe.red_gain, recipe.green_gain, recipe.blue_gain], dtype=np.float32)
    gains /= gains @ LUMA  # white-balance gains must not double as exposure
    linear *= gains
    luminance = _luminance(linear)
    y = np.clip(luminance, 0, 1)
    gain = 2 ** recipe.exposure_ev
    # Exposure with a smooth shoulder instead of hard channel clipping.
    mapped = gain * y / (1 + (gain - 1) * y)
    mapped += recipe.shadows * mapped * (1 - mapped) ** 3
    mapped -= recipe.highlights * mapped ** 3 * (1 - mapped)
    mapped += recipe.contrast * mapped * (1 - mapped) * (mapped - 0.18)
    mapped = np.clip(mapped, 0, 1)
    adjusted = linear * (mapped / np.maximum(luminance, 1e-8))[..., None]
    chroma = adjusted - mapped[..., None]
    low, high = _extrema(rgb)
    saturation = (high - low) / np.maximum(high, 1e-8)
    chroma *= (1 + recipe.vibrance * (1 - saturation) ** 2)[..., None]
    # A smooth gamut shoulder compresses chroma toward the same luminance.
    # Hard min/max clipping would flatten bright colored detail at the boundary.
    low, high = _extrema(chroma)
    upper = (1 - mapped) / np.maximum(high, 1e-8)
    lower = mapped / np.maximum(-low, 1e-8)
    ratio = 1 / np.maximum(np.minimum(upper, lower), 1e-8)
    compressed = np.where(ratio > 0.8, 1 - 0.04 / np.maximum(ratio - 0.6, 1e-8), ratio)
    scale = np.minimum(1, compressed / np.maximum(ratio, 1e-8))
    result = mapped[..., None] + chroma * scale[..., None]
    rendered = np.clip(to_srgb(np.clip(result, 0, 1)), 0, 1).astype(np.float32)
    # Blend the complete encoded-sRGB transform. Scaling only some operators
    # would leave a gamut-compression jump between zero and a tiny strength.
    return rgb + (rendered - rgb) * amount


def sample_field(values: list[float], edge: int, shape: tuple[int, int],
                 region: tuple[float, float, float, float]) -> np.ndarray:
    """Bilinearly sample a frozen full-source field at pixel centers."""
    height, width = shape
    left, top, right, bottom = region
    x = np.clip((left + (np.arange(width, dtype=np.float32) + 0.5) / width * (right - left)) * edge - 0.5, 0, edge - 1)
    y = np.clip((top + (np.arange(height, dtype=np.float32) + 0.5) / height * (bottom - top)) * edge - 0.5, 0, edge - 1)
    x0, y0 = x.astype(np.int32), y.astype(np.int32)
    x1, y1 = np.minimum(x0 + 1, edge - 1), np.minimum(y0 + 1, edge - 1)
    fx, fy = x - x0, (y - y0)[:, None]
    grid = np.asarray(values, dtype=np.float32).reshape(edge, edge)
    a = grid[y0[:, None], x0] * (1 - fx) + grid[y0[:, None], x1] * fx
    b = grid[y1[:, None], x0] * (1 - fx) + grid[y1[:, None], x1] * fx
    return (a * (1 - fy) + b * fy).astype(np.float32)


def _transform_v2(rgb: np.ndarray, recipe: NaturalEnhancement,
                  region: tuple[float, float, float, float]) -> np.ndarray:
    import cv2

    if is_identity(recipe):
        return rgb.copy()
    linear = to_linear(rgb)
    gains = np.array([recipe.red_gain, recipe.green_gain, recipe.blue_gain], dtype=np.float32)
    linear *= gains / (gains @ LUMA)
    luminance = _luminance(linear)
    original_y = np.clip(to_srgb(np.clip(luminance, 0, 1)), 0, 1)
    local = np.zeros_like(luminance)
    if any(recipe.local_exposure):
        field = sample_field(recipe.local_exposure, 8, luminance.shape, region)
        # Luminance guidance prevents a bright object in a dark spatial cell
        # receiving the shadow lift, and a dark branch receiving sky darkening.
        shadow_weight = np.clip((0.75 - original_y) / 0.5, 0, 1)
        highlight_weight = np.clip((original_y - 0.3) / 0.45, 0, 1)
        local = field * np.where(field >= 0, shadow_weight, highlight_weight)
    gain = np.exp2(recipe.exposure_ev + local)
    y = np.clip(luminance, 0, 1)
    y = gain * y / (1 + (gain - 1) * y)
    y = np.clip(to_srgb(y), 0, 1)
    # Photographic tone controls operate on perceptual luminance. The previous
    # linear-luminance-only controls were almost invisible on broad-range scenes.
    y += recipe.shadows * 2.5 * y * (1 - y) ** 3
    y -= recipe.highlights * 2.8 * y ** 3 * (1 - y)
    y += recipe.tone_contrast * 4 * y * (1 - y) * (y - 0.5)
    if recipe.black_point:
        y -= recipe.black_point * (1 - y) ** 3 * y / np.maximum(y + recipe.black_point, 1e-8)
    if recipe.white_lift:
        y += recipe.white_lift * y ** 3 * (1 - y) / np.maximum(1 - y + recipe.white_lift, 1e-8)
    if recipe.clarity:
        base = sample_field(recipe.base_luminance, 32, y.shape, region)
        difference = original_y - base
        # Suppress halos at strong boundaries and restrict the detail change.
        detail = difference * np.exp(-(difference / 0.16) ** 2)
        y += np.clip(recipe.clarity * detail * 4 * original_y * (1 - original_y), -0.025, 0.025)
    target = to_linear(np.clip(y, 0, 1))
    adjusted = linear * (target / np.maximum(luminance, 1e-8))[..., None]
    chroma = adjusted - target[..., None]
    hsv = cv2.cvtColor(np.ascontiguousarray(rgb, dtype=np.float32), cv2.COLOR_RGB2HSV)
    saturation = hsv[..., 1]
    color_gain = 1 + recipe.vibrance * (1 - saturation) ** 2
    if any(recipe.hue_chroma):
        phase = hsv[..., 0] / 60
        index = np.floor(phase).astype(np.int32) % 6
        fraction = phase - np.floor(phase)
        controls = np.asarray(recipe.hue_chroma, dtype=np.float32)
        hue_gain = controls[index] * (1 - fraction) + controls[(index + 1) % 6] * fraction
        color_gain += hue_gain * np.clip((saturation - 0.15) / 0.5, 0, 1)
    chroma *= color_gain[..., None]
    low, high = _extrema(chroma)
    upper = (1 - target) / np.maximum(high, 1e-8)
    lower = target / np.maximum(-low, 1e-8)
    ratio = 1 / np.maximum(np.minimum(upper, lower), 1e-8)
    compressed = np.where(ratio > 0.8, 1 - 0.04 / np.maximum(ratio - 0.6, 1e-8), ratio)
    scale = np.minimum(1, compressed / np.maximum(ratio, 1e-8))
    result = target[..., None] + chroma * scale[..., None]
    rendered = np.clip(to_srgb(np.clip(result, 0, 1)), 0, 1).astype(np.float32)
    return rgb + (rendered - rgb) * recipe.strength


def transform(rgb: np.ndarray, recipe: NaturalEnhancement, *,
              region: tuple[float, float, float, float] = (0, 0, 1, 1)) -> np.ndarray:
    if recipe.version == "natural-v3":
        from app.services.detail import texture_delta

        if is_identity(recipe):
            return rgb.copy()
        base_recipe = recipe.model_copy(update={"strength": 1.0, "texture": 0.0, "microcontrast": 0.0, "detail_noise": 0.0})
        toned = _transform_v2(rgb, base_recipe, region)
        if recipe.texture or recipe.microcontrast:
            height, width = rgb.shape[:2]
            scale = max(width / (region[2] - region[0]), height / (region[3] - region[1])) / recipe.detail_reference_edge
            toned = toned + texture_delta(toned, recipe, scale)[..., None]
        return rgb + (toned - rgb) * recipe.strength
    if recipe.version == "natural-v2":
        return _transform_v2(rgb, recipe, region)
    return _transform_v1(rgb, recipe)


def apply(image: Image.Image, recipe: NaturalEnhancement, *,
          region: tuple[float, float, float, float] = (0, 0, 1, 1)) -> None:
    """Bound temporary allocations to strips rather than full 24 MP floats."""
    if is_identity(recipe):
        return
    from app.services.detail import detail_halo

    left, start, right, stop = region
    scale = max(image.width / (right - left), image.height / (stop - start)) / recipe.detail_reference_edge
    halo = detail_halo(scale) if recipe.version == "natural-v3" and (recipe.texture or recipe.microcontrast) else 0
    carry = None
    try:
        for top in range(0, image.height, 64):
            bottom = min(image.height, top + 64)
            source_top, source_bottom = max(0, top - halo), min(image.height, bottom + halo)
            with image.crop((0, source_top, image.width, source_bottom)) as tile:
                if carry is not None:
                    tile.paste(carry, (0, 0))
                    carry.close()
                    carry = None
                if halo and bottom < image.height:
                    carry = tile.crop((0, max(0, bottom - halo) - source_top, image.width, bottom - source_top))
                pixels = np.asarray(tile, dtype=np.float32) / 255
                strip_region = (left, start + (stop - start) * source_top / image.height,
                                right, start + (stop - start) * source_bottom / image.height)
                transformed = transform(pixels, recipe, region=strip_region)
                result = np.rint(transformed[top - source_top:bottom - source_top] * 255).astype(np.uint8)
            with Image.fromarray(result) as rendered:
                image.paste(rendered, (0, top))
    finally:
        if carry is not None:
            carry.close()


def analyze_v1(path: Path) -> Enhancement:
    with Image.open(path) as source:
        image = source.convert("RGB")
    try:
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        rgb = np.asarray(image, dtype=np.float32) / 255
    finally:
        image.close()
    linear = to_linear(rgb)
    y = to_srgb(_luminance(linear))
    p02, p10, p25, median, p90, p98 = np.quantile(y, [0.02, 0.1, 0.25, 0.5, 0.9, 0.98])
    spread = float(p98 - p02)
    minimum, maximum = _extrema(rgb)
    saturation = (maximum - minimum) / np.maximum(maximum, 1e-8)
    recipe = NaturalEnhancement()
    if spread < 0.035:
        return Enhancement(adjustments=NEUTRAL, recipe=recipe,
                           message="Kept this photograph unchanged: there is too little tonal variation for a reliable automatic correction.")

    low_key = median < 0.16 and p90 < 0.48
    high_key = median > 0.78 and p10 > 0.4
    exposure = 0.0
    if median < 0.32:
        target = float(to_linear(np.array(0.4, dtype=np.float32)))
        current = float(to_linear(np.array(max(median, 0.02), dtype=np.float32)))
        exposure = float(np.clip(np.log2(target / current) * 0.38, 0, 0.85))
        if p98 > 0.9:
            exposure = min(exposure, 0.35)
        if low_key:
            exposure = min(exposure, 0.12)
    elif median > 0.63 and p90 > 0.9:
        exposure = float(np.clip(-np.log2(median / 0.6) * 0.6, -0.45, 0))
        if high_key:
            exposure = max(exposure, -0.08)

    shadows = float(np.clip((0.27 - p25) * 1.8, 0, 0.38)) if spread > 0.45 else 0.0
    if low_key:
        shadows = min(shadows, 0.08)
    highlights = float(np.clip((p90 - 0.78) * 1.7, 0, 0.35)) if not high_key else 0.0
    contrast = float(np.clip((0.5 - spread) * 0.45, 0, 0.14)) if 0.2 < median < 0.7 else 0.0
    vibrance = 0.04 if 0.08 < float(np.median(saturation)) < 0.3 and not low_key else 0.0

    # Only plausible midtone neutrals contribute WB evidence. Dominant scene
    # colors and warm evening light are not evidence of a camera color cast.
    neutral = (saturation < 0.18) & (y > 0.2) & (y < 0.85)
    warm_fraction = float(np.mean((rgb[..., 0] > rgb[..., 2] * 1.3) & (rgb[..., 0] > rgb[..., 1] * 1.08)))
    gains = np.ones(3, dtype=np.float32)
    if np.count_nonzero(neutral) >= max(64, rgb.shape[0] * rgb.shape[1] * 0.04) and warm_fraction < 0.25:
        samples = linear[neutral]
        # Normalize each sample before aggregation, so a bright patch cannot
        # dominate WB. Pull only part way toward neutral and cap correction.
        ratios = samples / np.maximum(samples.mean(axis=-1, keepdims=True), 1e-8)
        cast = np.median(ratios, axis=0)
        gains = np.clip((1 / np.maximum(cast, 1e-8)) ** 0.35, 0.95, 1.05)

    recipe = NaturalEnhancement(exposure_ev=round(exposure, 5), shadows=round(shadows, 5),
        highlights=round(highlights, 5), contrast=round(contrast, 5), vibrance=vibrance,
        red_gain=round(float(gains[0]), 5), green_gain=round(float(gains[1]), 5), blue_gain=round(float(gains[2]), 5))
    # Back off extreme corrections rather than introduce new clipped channels.
    # This checks the exact renderer, not a different thumbnail-only operator.
    original_clipping = float(np.mean(maximum >= 0.995))
    rendered = transform(rgb, recipe)
    for strength in (1.0, 0.5, 0.25, 0.0):
        candidate = recipe.model_copy(update={"strength": strength})
        candidate_pixels = rgb + (rendered - rgb) * strength
        if float(np.mean(_extrema(candidate_pixels)[1] >= 0.995)) <= original_clipping + 0.002:
            recipe = candidate
            break

    changes = []
    if recipe.exposure_ev > 0.02 or recipe.shadows > 0.02:
        changes.append("Lifted darker tones")
    if recipe.highlights > 0.02 or recipe.exposure_ev < -0.02:
        changes.append("balanced bright tones")
    if max(abs(float(g) - 1) for g in gains) > 0.005:
        changes.append("gently corrected neutral colors")
    if recipe.contrast > 0.02 or recipe.vibrance:
        changes.append("refined contrast and color")
    if low_key:
        changes.append("preserved low-light atmosphere")
    if changes and recipe.strength:
        message = "; ".join(changes) + ". Adjust Auto Enhance strength to taste."
    elif recipe.strength == 0:
        message = "Kept the original balance to protect bright colors. You can adjust the enhancement strength to taste."
    else:
        message = "This photograph needs little automatic correction. Your original balance was preserved."
    message = message[0].upper() + message[1:]
    return Enhancement(adjustments=NEUTRAL, recipe=recipe, message=message)


def analyze(path: Path, *, detail_path: Path | None = None) -> Enhancement:
    from app.services.photographic import analyze_photograph

    return analyze_photograph(path, detail_path=detail_path)
