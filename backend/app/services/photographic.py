"""Diagnose deficits and excesses, then build an editable photographic recipe.

Inspired by source-derived, full-resolution local-transform pipelines in the
research record. These are explicit bounded decisions, not learned semantics.
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.schemas.images import Enhancement, EnhancementFinding, NaturalEnhancement
from app.services.enhancement import NEUTRAL, _extrema, _luminance, to_linear, to_srgb, transform
from app.services.detail import sample_detail


def _rounded(values: np.ndarray) -> list[float]:
    return [round(float(value), 5) for value in values.ravel()]


def _finding(area: str, issue: str, action: str, observation: str = "") -> EnhancementFinding:
    return EnhancementFinding(area=area, issue=issue, action=action, observation=observation)


def _detail_settings(stats: dict) -> tuple[float, float]:
    if stats["noise"] >= 0.022 or stats["structure"] < 0.0025:
        return 0.0, 0.0
    activity = min(1.0, max(0.0, (stats["structure"] - 0.0025) / 0.012))
    protection = max(0.2, 1 - stats["noise"] / 0.025)
    if stats["hard_edges"] > 0.18:
        protection *= 0.45
    texture, micro = 0.42 * activity * protection, 0.2 * activity * protection
    if not stats["noise_samples"]:
        texture, micro = min(texture, 0.12), min(micro, 0.05)
    return round(texture, 5), round(micro, 5)


def _regional_exposure(y: np.ndarray, enabled: bool) -> list[float]:
    if not enabled:
        return []
    height, width = y.shape
    field = np.zeros((8, 8), dtype=np.float32)
    for row in range(8):
        top = min(height - 1, row * height // 8)
        bottom = max(top + 1, (row + 1) * height // 8)
        for col in range(8):
            left = min(width - 1, col * width // 8)
            right = max(left + 1, (col + 1) * width // 8)
            q10, median, q90 = np.quantile(y[top:bottom, left:right], [0.1, 0.5, 0.9])
            if 0.065 < median < 0.3 and q90 > 0.2:
                field[row, col] = min(0.4, (0.3 - median) * 2.0)
            elif median > 0.7 and q10 > 0.42:
                field[row, col] = -min(0.35, (median - 0.7) * 2.1)
    field = cv2.GaussianBlur(field, (3, 3), 0.65, borderType=cv2.BORDER_REPLICATE)
    if float(np.max(np.abs(field))) < 0.025:
        return []
    return _rounded(field)


def _color_excess(hsv: np.ndarray, y: np.ndarray, warm_scene: bool) -> list[float]:
    hue, saturation = hsv[..., 0], hsv[..., 1]
    controls = np.zeros(6, dtype=np.float32)
    for index in range(6):
        distance = np.abs((hue - index * 60 + 180) % 360 - 180)
        mask = (distance < 35) & (y > 0.08) & (y < 0.92) & (saturation > 0.15)
        if np.count_nonzero(mask) < max(64, y.size * 0.06):
            continue
        median, upper = np.quantile(saturation[mask], [0.5, 0.9])
        if median > 0.6 and upper > 0.82:
            reduction = min(0.24, (median - 0.6) * 0.8 + (upper - 0.82) * 0.3)
            # Red/yellow may be skin or intentional warm light. No skin or sky
            # semantic label is inferred from a hue bin.
            if index in (0, 1):
                reduction = 0.0 if warm_scene else min(reduction, 0.045)
            controls[index] = -reduction
    return _rounded(controls) if np.any(controls) else []


def analyze_photograph(path: Path, *, detail_path: Path | None = None) -> Enhancement:
    with Image.open(path) as source:
        image = source.convert("RGB")
    try:
        image.thumbnail((768, 768), Image.Resampling.LANCZOS)
        rgb = np.asarray(image, dtype=np.float32) / 255
    finally:
        image.close()
    linear = to_linear(rgb)
    y = np.clip(to_srgb(_luminance(linear)), 0, 1).astype(np.float32)
    p02, p10, p25, median, p75, p90, p98 = np.quantile(y, [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98])
    spread = float(p98 - p02)
    detail_stats = sample_detail(detail_path or path)
    texture, microcontrast = _detail_settings(detail_stats)
    detail_fields = {"texture": texture, "microcontrast": microcontrast,
                     "detail_noise": round(detail_stats["noise"], 6),
                     "detail_reference_edge": detail_stats["reference_edge"]}
    if spread < 0.035:
        findings = [_finding("light", "Little tonal variation", "Kept the overall tonal balance instead of forcing a style.")]
        if texture:
            findings.append(_finding("detail", "Fine source texture", "Added restrained texture definition using source-resolution samples."))
        return Enhancement(adjustments=NEUTRAL, recipe=NaturalEnhancement(version="natural-v3", **detail_fields),
            assessment=findings, message=" ".join(f.action for f in findings))

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[..., 1]
    low_key = median < 0.16 and p90 < 0.48
    high_key = median > 0.78 and p10 > 0.4
    warm_fraction = float(np.mean((rgb[..., 0] > rgb[..., 2] * 1.3) & (rgb[..., 0] > rgb[..., 1] * 1.08)))
    warm_scene = warm_fraction > 0.25
    exposure = 0.0
    if median < 0.32:
        target = float(to_linear(np.array(0.4, dtype=np.float32)))
        current = float(to_linear(np.array(max(median, 0.02), dtype=np.float32)))
        exposure = float(np.clip(np.log2(target / current) * 0.38, 0, 0.85))
        if p98 > 0.9:
            exposure = min(exposure, 0.3)
        if low_key:
            exposure = min(exposure, 0.1)
    elif median > 0.63 and p90 > 0.9:
        exposure = float(np.clip(-np.log2(median / 0.6) * 0.65, -0.45, 0))
        if high_key:
            exposure = max(exposure, -0.06)

    shadows = float(np.clip((0.23 - p25) * 1.6, 0, 0.25)) if spread > 0.4 else 0.0
    if low_key:
        shadows = min(shadows, 0.025)
    highlights = float(np.clip((p90 - 0.76) * 1.65, 0, 0.34)) if not high_key else 0.0
    black_point = float(np.clip((p02 - 0.03) * 0.65, 0, 0.055)) if not (low_key or high_key) else 0.0
    white_lift = float(np.clip((0.86 - p98) * 0.6, 0, 0.07)) if 0.2 < median < 0.7 and p98 < 0.82 else 0.0
    interquartile = float(p75 - p25)
    contrast = float(np.clip((0.34 - interquartile) * 0.7, 0, 0.18)) if 0.2 < median < 0.7 else 0.0
    if interquartile > 0.55:
        contrast = -min(0.1, (interquartile - 0.55) * 0.5)
    full_range_balance = p02 < 0.035 and p98 > 0.965 and 0.43 < median < 0.57 and 0.43 < interquartile < 0.55
    if full_range_balance:
        # A well-distributed full tonal range is not evidence of excess light.
        shadows *= 0.1
        highlights *= 0.1
    vibrance = 0.08 if 0.08 < float(np.median(saturation)) < 0.3 and not low_key else 0.0
    hue_chroma = _color_excess(hsv, y, warm_scene)

    neutral = (saturation < 0.18) & (y > 0.2) & (y < 0.85)
    gains = np.ones(3, dtype=np.float32)
    if np.count_nonzero(neutral) >= max(64, y.size * 0.04) and not warm_scene:
        samples = linear[neutral]
        ratios = samples / np.maximum(samples.mean(axis=-1, keepdims=True), 1e-8)
        gains = np.clip((1 / np.maximum(np.median(ratios, axis=0), 1e-8)) ** 0.35, 0.95, 1.05)

    # This guide is frozen from the original, not recomputed per strip/crop.
    # Bilateral smoothing retains larger edges; the render's edge gate further
    # suppresses halos when a coarse guide and a sharp source edge disagree.
    base = cv2.bilateralFilter(y, 9, 0.1, 5, borderType=cv2.BORDER_REFLECT_101)
    detail = y - cv2.medianBlur(y, 3)
    gradient = cv2.magnitude(cv2.Sobel(y, cv2.CV_32F, 1, 0, ksize=3, scale=0.125),
                             cv2.Sobel(y, cv2.CV_32F, 0, 1, ksize=3, scale=0.125))
    flat = (gradient < 0.025) & (y > 0.08) & (y < 0.85)
    noise = float(np.median(np.abs(detail[flat])) / 0.6745) if np.count_nonzero(flat) >= 64 else 0.03
    if detail_stats["noise_samples"]:
        noise = max(noise, detail_stats["noise"])
    structure = float(np.std(y - base))
    clarity = 0.0
    if not (low_key or high_key) and spread > 0.35 and noise < 0.018 and structure > 0.003:
        clarity = 0.2 if structure < 0.04 else 0.1
        if noise > 0.01:
            clarity *= 0.35
    base_grid = _rounded(cv2.resize(base, (32, 32), interpolation=cv2.INTER_AREA)) if clarity else []
    local_exposure = _regional_exposure(y, spread > 0.45 and structure > 0.003 and not (low_key or high_key))
    if noise >= 0.018:
        shadows *= 0.45
        exposure = min(exposure, 0) + max(exposure, 0) * 0.75
        local_exposure = [round(value * 0.5 if value > 0 else value, 5) for value in local_exposure]

    recipe = NaturalEnhancement(version="natural-v3", exposure_ev=round(exposure, 5),
        shadows=round(shadows, 5), highlights=round(highlights, 5), vibrance=vibrance,
        red_gain=round(float(gains[0]), 5), green_gain=round(float(gains[1]), 5), blue_gain=round(float(gains[2]), 5),
        black_point=round(black_point, 5), white_lift=round(white_lift, 5), tone_contrast=round(contrast, 5),
        clarity=round(clarity, 5), hue_chroma=hue_chroma, local_exposure=local_exposure, base_luminance=base_grid,
        **detail_fields)
    original_clip = float(np.mean(_extrema(rgb)[1] >= 0.995))
    original_black = float(np.mean(y < 0.01))
    rendered = transform(rgb, recipe)
    for strength in (1.0, 0.8, 0.6, 0.4, 0.2, 0.0):
        candidate = rgb + (rendered - rgb) * strength
        new_clip = float(np.mean(_extrema(candidate)[1] >= 0.995))
        new_black = float(np.mean(to_srgb(_luminance(to_linear(candidate))) < 0.01))
        if new_clip <= original_clip + 0.004 and new_black <= original_black + 0.004:
            recipe = recipe.model_copy(update={"strength": strength})
            break

    findings = []
    if exposure > 0.03:
        findings.append(_finding("light", "Dark midtones", "Lifted exposure while retaining a smooth highlight shoulder."))
    elif exposure < -0.03:
        findings.append(_finding("light", "Bright overall exposure", "Reduced overall brightness while preserving the light's character."))
    if highlights > 0.04:
        findings.append(_finding("light", "Strong bright tones", "Pulled back highlights for clearer tonal separation."))
    if black_point > 0.012:
        findings.append(_finding("contrast", "Lifted darkest tones", "Deepened the black anchor to reduce a washed-out appearance."))
    if shadows > 0.04:
        findings.append(_finding("light", "Dense darker tones", "Opened shadow tones to make existing detail easier to see."))
    if any(local_exposure):
        findings.append(_finding("light", "Uneven regional brightness", "Balanced darker and brighter regions separately."))
    names = ("red", "yellow", "green", "cyan", "blue", "magenta")
    excessive = [names[i] for i, value in enumerate(hue_chroma) if value < -0.025]
    if excessive:
        findings.append(_finding("color", "Strong " + ", ".join(excessive) + " saturation", "Reduced the strongest color intensity while retaining hue and protecting warm colors."))
    elif vibrance:
        findings.append(_finding("color", "Subdued color separation", "Lifted restrained colors more gently than already saturated colors."))
    if abs(contrast) > 0.025:
        findings.append(_finding("contrast", "Limited midtone separation" if contrast > 0 else "Very wide midtone range",
            "Added a gentle contrast curve." if contrast > 0 else "Softened midtone contrast to balance the tonal range."))
    if clarity > 0.04:
        findings.append(_finding("detail", "Low local definition", "Added definition while limiting harsh edges and possible noise."))
    if texture:
        findings.insert(0, _finding("detail", "Fine texture separation", "Refined fine and medium texture while limiting noise, hard edges and warm midtones.",
            f"Reviewed {detail_stats['patches']} source-resolution patches; smooth areas receive less detail boost."))
    if max(abs(float(g) - 1) for g in gains) > 0.008:
        findings.append(_finding("color", "Slight neutral color cast", "Gently balanced neutral tones while retaining scene color."))
    if low_key:
        findings.insert(0, _finding("light", "Low-light atmosphere", "Preserved the low-light mood instead of forcing daylight brightness."))
    if noise >= 0.018:
        findings.insert(0, _finding("detail", "Fine-grain variation", "Limited local contrast and shadow lifting to avoid amplifying possible noise."))
    if recipe.strength == 0:
        findings = [_finding("light", "Correction exceeded protection limits", "Kept the original balance to protect bright colors and dark detail.")]
    if not findings:
        findings = [_finding("light", "No clear tonal or color deficit", "Kept corrections small instead of applying an arbitrary look.")]
    findings = findings[:8]
    message = " ".join(f.action for f in findings[:2])
    return Enhancement(adjustments=NEUTRAL, recipe=recipe, assessment=findings, message=message)
