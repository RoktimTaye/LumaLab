"""Source-scale diagnostics and bounded, multiscale luminance texture."""

from math import ceil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.schemas.images import NaturalEnhancement


def detail_sigmas(scale: float) -> tuple[float, float]:
    return max(0.25, min(1.2, 0.7 * scale)), max(0.4, min(3.0, 1.8 * scale))


def _blur(values: np.ndarray, sigma: float) -> np.ndarray:
    radius = ceil(3 * sigma)
    return cv2.GaussianBlur(values, (2 * radius + 1, 2 * radius + 1), sigma,
                            borderType=cv2.BORDER_REFLECT_101)


def detail_halo(scale: float) -> int:
    fine, medium = detail_sigmas(scale)
    # The medium band includes a fine blur followed by a medium-band activity
    # blur. Cover their summed support, plus Sobel's one-pixel neighbourhood.
    return ceil(3 * fine) + 2 * ceil(3 * medium) + 2


def sample_detail(path: Path) -> dict[str, float | int]:
    """Inspect up to five source-pixel patches; never resize the samples."""
    noise_values, structure_values, edge_values = [], [], []
    with Image.open(path) as source:
        width, height = source.size
        edge = max(width, height)
        side = min(256, width, height)
        boxes = set()
        for cx, cy in ((0.5, 0.5), (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
            left = min(width - side, max(0, round(cx * width - side / 2)))
            top = min(height - side, max(0, round(cy * height - side / 2)))
            boxes.add((left, top, left + side, top + side))
        for box in sorted(boxes):
            with source.crop(box) as patch, patch.convert("RGB") as rgb_patch:
                rgb = np.asarray(rgb_patch, dtype=np.float32) / 255
            y = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
            fine = y - _blur(y, 0.7)
            medium = _blur(y, 0.7) - _blur(y, 1.8)
            gradient = cv2.magnitude(cv2.Sobel(y, cv2.CV_32F, 1, 0, ksize=3, scale=0.125),
                                    cv2.Sobel(y, cv2.CV_32F, 0, 1, ksize=3, scale=0.125))
            flat = (gradient < 0.018) & (y > 0.1) & (y < 0.85)
            residual = y - cv2.medianBlur(y, 3)
            if np.count_nonzero(flat) >= 64:
                noise_values.append(float(np.median(np.abs(residual[flat])) / 0.6745))
            structure_values.append(float(np.sqrt(np.mean(medium * medium))))
            edge_values.append(float(np.mean(gradient > 0.09)))
    return {"reference_edge": edge, "patches": len(boxes),
            # Prefer the quieter credible samples: a median across sky and
            # foliage patches can mistake real fine texture for sensor noise.
            "noise": min(0.1, float(np.quantile(noise_values, 0.25))) if noise_values else 0.012,
            "noise_samples": len(noise_values),
            "structure": float(np.median(structure_values)), "hard_edges": float(np.mean(edge_values))}


def texture_delta(rgb: np.ndarray, recipe: NaturalEnhancement, scale: float) -> np.ndarray:
    """Return a luminance-only offset with no new per-channel clipping."""
    y = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    fine_sigma, medium_sigma = detail_sigmas(scale)
    smooth = _blur(y, fine_sigma)
    fine = y - smooth
    medium = smooth - _blur(y, medium_sigma)
    noise = recipe.detail_noise * min(1.0, scale)
    activity = np.sqrt(np.maximum(_blur(medium * medium, medium_sigma), 0))
    structure_mask = np.clip((activity - noise * 1.3 - 0.001) / 0.018, 0, 1)
    gradient = cv2.magnitude(cv2.Sobel(y, cv2.CV_32F, 1, 0, ksize=3, scale=0.125),
                            cv2.Sobel(y, cv2.CV_32F, 0, 1, ksize=3, scale=0.125))
    edge_mask = 1 / (1 + (gradient / 0.075) ** 4)
    edge_radius = ceil(3 * medium_sigma)
    strong_edges = cv2.dilate((gradient > 0.15).astype(np.float32),
        np.ones((2 * edge_radius + 1, 2 * edge_radius + 1), dtype=np.uint8))
    # Protect the neighbourhood of a hard edge as well as the edge pixel;
    # otherwise a Gaussian band can put a dark/bright ring beside the boundary.
    edge_mask *= 1 - strong_edges * 0.97
    tone_mask = np.clip((y - 0.06) / 0.2, 0, 1) * np.clip((0.96 - y) / 0.2, 0, 1)
    hsv = cv2.cvtColor(np.ascontiguousarray(rgb, dtype=np.float32), cv2.COLOR_RGB2HSV)
    warm_midtones = (hsv[..., 0] < 50) & (hsv[..., 1] > 0.08) & (hsv[..., 1] < 0.65) & (y > 0.15)
    # A conservative hue proxy, not a face/skin semantic detector.
    protection = np.where(warm_midtones, 0.3, 1.0)
    floor = noise * 1.3 + 1 / 1024
    fine_signal = np.sign(fine) * np.maximum(np.abs(fine) - floor, 0)
    medium_signal = np.sign(medium) * np.maximum(np.abs(medium) - floor * 0.65, 0)
    delta = (recipe.texture * fine_signal + recipe.microcontrast * medium_signal)
    delta *= structure_mask * edge_mask * tone_mask * protection
    delta = np.clip(delta, -0.025, 0.025)
    minimum = np.minimum(np.minimum(rgb[..., 0], rgb[..., 1]), rgb[..., 2])
    maximum = np.maximum(np.maximum(rgb[..., 0], rgb[..., 1]), rgb[..., 2])
    return np.clip(delta, -minimum * 0.8, (1 - maximum) * 0.8).astype(np.float32)
