"""Shape-preserving cubic point curves in encoded sRGB (master, then channel)."""

import numpy as np

from app.schemas.images import PointCurve, RGBCurves


def curve_table(curve: PointCurve) -> np.ndarray:
    x = np.array([p.x for p in curve.points], dtype=np.float64)
    y = np.array([p.y for p in curve.points], dtype=np.float64)
    h = np.diff(x)
    d = np.diff(y) / h
    slopes = np.zeros(len(x))
    slopes[0], slopes[-1] = d[0], d[-1]
    for i in range(1, len(x) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            slopes[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    values = np.arange(256)
    i = np.clip(np.searchsorted(x, values, side="right") - 1, 0, len(x) - 2)
    t = (values - x[i]) / h[i]
    result = ((2*t**3 - 3*t**2 + 1)*y[i] + (t**3 - 2*t**2 + t)*h[i]*slopes[i]
              + (-2*t**3 + 3*t**2)*y[i+1] + (t**3 - t**2)*h[i]*slopes[i+1])
    return np.floor(np.clip(result, 0, 255) + 0.5).astype(np.uint8)


def rgb_table(curves: RGBCurves) -> list[int]:
    master = curve_table(curves.rgb)
    return np.concatenate([curve_table(getattr(curves, channel))[master]
                           for channel in ("red", "green", "blue")]).tolist()
