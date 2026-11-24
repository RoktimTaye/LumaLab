"""Curve validation, interpolation, composition and actual render regressions."""
from io import BytesIO

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from app.config import Settings
from app.schemas.images import Adjustments, PointCurve, RGBCurves
from app.services.curves import curve_table, rgb_table
from app.services.images import render


def curve(points):
    return PointCurve.model_validate({"points": [dict(x=x, y=y) for x, y in points]})


@pytest.mark.parametrize("points", [[], [(0, 0)], [(1, 0), (255, 255)], [(0, 0), (254, 255)],
    [(0, 0), (128, 100), (128, 200), (255, 255)], [(0, 0), (200, 100), (100, 200), (255, 255)],
    [(0, -1), (255, 255)], [(0, 0), (255, 256)], [(0, 0), (128.5, 90), (255, 255)],
    [(0, 0), (True, 90), (255, 255)], [(i, i) for i in range(16)] + [(255, 255)]])
def test_invalid_points_rejected(points):
    with pytest.raises(ValidationError):
        curve(points)


def test_identity_and_smooth_interpolation():
    np.testing.assert_array_equal(curve_table(RGBCurves().rgb), np.arange(256))
    points = [(0, 0), (64, 35), (128, 170), (192, 220), (255, 255)]
    table = curve_table(curve(points)).astype(int)
    assert all(table[x] == y for x, y in points)
    assert np.all(np.diff(table) >= 0)
    # Each segment stays within its anchors, including curves that reverse direction.
    points = [(0, 220), (64, 20), (128, 240), (255, 0)]
    table = curve_table(curve(points))
    for (x, y), (xx, yy) in zip(points, points[1:]):
        assert table[x:xx+1].min() >= min(y, yy)
        assert table[x:xx+1].max() <= max(y, yy)


def test_master_then_channel_composition():
    curves = RGBCurves(rgb=curve([(0, 20), (255, 230)]), red=curve([(0, 0), (128, 190), (255, 255)]))
    table = np.array(rgb_table(curves)).reshape(3, 256)
    master = curve_table(curves.rgb)
    np.testing.assert_array_equal(table[0], curve_table(curves.red)[master])
    np.testing.assert_array_equal(table[1], master)
    np.testing.assert_array_equal(table[2], master)


def test_render_identity_channel_isolation_and_preview_export_parity(tmp_path):
    path = tmp_path / 'source.png'
    Image.new('RGB', (64, 64), (100, 100, 100)).save(path)
    source_bytes = path.read_bytes()
    settings = Settings(database_url='postgresql://test:test@localhost/test?sslmode=require')
    neutral = Adjustments(brightness=100, contrast=100, saturation=100, warmth=0, sharpness=0, vignette=0)
    original = render(path, neutral, settings, preview=False)
    assert render(path, neutral, settings, preview=False, curves=RGBCurves()) == original
    curves = RGBCurves(red=curve([(0, 0), (100, 180), (255, 255)]))
    output = render(path, neutral, settings, preview=False, curves=curves)
    assert render(path, neutral, settings, preview=True, curves=curves) == output
    with Image.open(BytesIO(output)) as image:
        r, g, b = image.getpixel((32, 32))
        assert abs(r - 180) <= 3 and abs(g - 100) <= 3 and abs(b - 100) <= 3
    assert path.read_bytes() == source_bytes
