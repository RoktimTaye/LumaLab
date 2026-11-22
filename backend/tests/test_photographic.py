"""Deficit/excess decisions, source coordinates and real-photo regressions."""

from io import BytesIO
from itertools import product
from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageStat
from pydantic import ValidationError

from app.config import PROJECT_DIR, Settings
from app.schemas.images import Crop, NaturalEnhancement
from app.services.enhancement import NEUTRAL, analyze, analyze_v1, apply, to_linear, to_srgb, transform, _luminance
from app.services.images import render


class PhotographicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name, "source.png")

    def analyze_pixels(self, pixels):
        with Image.fromarray(np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8)) as image:
            image.save(self.path)
        return analyze(self.path)

    def test_regional_tone_can_treat_the_same_color_differently_by_location(self):
        pixels = np.full((64, 128, 3), 0.35, dtype=np.float32)
        grid = np.zeros((8, 8), dtype=np.float32)
        grid[:, :4], grid[:, 4:] = 0.4, -0.4
        recipe = NaturalEnhancement(version="natural-v2", local_exposure=grid.ravel().tolist())
        result = transform(pixels, recipe)
        self.assertGreater(float(result[:, 16].mean()), float(result[:, 112].mean()) + 0.035)
        self.assertLess(float(np.max(np.abs(np.diff(result, axis=1)))), 0.008)

    def test_saturated_greens_are_reduced_and_warm_hues_do_not_receive_the_green_adjustment(self):
        gradient = np.linspace(0.25, 0.95, 256, dtype=np.float32)[None, :, None]
        pixels = np.broadcast_to(gradient * [0.35, 1, 0.1], (96, 256, 3)).astype(np.float32).copy()
        pixels[:24] = np.array([0.7, 0.46, 0.35], dtype=np.float32)
        result = self.analyze_pixels(pixels)
        self.assertLess(result.recipe.hue_chroma[2], -0.04)
        hue_only = NaturalEnhancement(version="natural-v2", hue_chroma=result.recipe.hue_chroma)
        output = transform(pixels, hue_only)
        before, after = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV), cv2.cvtColor(output, cv2.COLOR_RGB2HSV)
        self.assertLess(float(np.median(after[32:, :, 1])), float(np.median(before[32:, :, 1])) - 0.025)
        np.testing.assert_allclose(after[:24, :, 0], before[:24, :, 0], atol=0.05)
        self.assertTrue(any("saturation" in f.issue for f in result.assessment))

    def test_noisy_input_does_not_receive_clarity_amplification(self):
        rng = np.random.default_rng(9)
        gradient = np.broadcast_to(np.linspace(0.08, 0.85, 256, dtype=np.float32)[None, :], (128, 256))
        gray = np.clip(gradient + rng.normal(0, 0.065, gradient.shape), 0, 1)
        result = self.analyze_pixels(np.repeat(gray[..., None], 3, axis=-1))
        self.assertEqual(result.recipe.clarity, 0)
        self.assertEqual(result.recipe.base_luminance, [])
        self.assertTrue(any("grain" in f.issue for f in result.assessment))

    def test_flat_low_contrast_input_and_overbright_input_get_different_edit_plans(self):
        flat = np.broadcast_to(np.linspace(0.3, 0.62, 256, dtype=np.float32)[None, :, None], (64, 256, 3))
        result = self.analyze_pixels(flat)
        self.assertGreater(result.recipe.tone_contrast, 0.03)
        self.assertGreater(result.recipe.black_point, 0.02)
        self.assertGreater(result.recipe.white_lift, 0)
        output = transform(flat, result.recipe)
        self.assertGreater(float(np.ptp(output)), float(np.ptp(flat)) + 0.015)
        high = np.broadcast_to(np.linspace(0.75, 1, 256, dtype=np.float32)[None, :, None], (64, 256, 3))
        high_result = self.analyze_pixels(high)
        self.assertEqual(high_result.recipe.black_point, 0)
        self.assertGreater(float(np.median(transform(high, high_result.recipe))), 0.8)

    def test_spatial_fields_are_repeatable_across_strips_crops_and_strength(self):
        rng = np.random.default_rng(5)
        pixels = rng.integers(8, 240, (160, 256, 3), dtype=np.uint8)
        grid = np.linspace(-0.3, 0.3, 64).tolist()
        base = np.tile(np.linspace(0.2, 0.8, 32), (32, 1)).ravel().tolist()
        recipe = NaturalEnhancement(version="natural-v2", local_exposure=grid, base_luminance=base,
            clarity=0.2, black_point=0.03, highlights=0.15, hue_chroma=[0, 0, -0.1, 0, 0, 0])
        rgb = pixels.astype(np.float32) / 255
        whole = transform(rgb, recipe)
        with Image.fromarray(pixels) as image:
            apply(image, recipe)
            difference = np.asarray(image).astype(np.int16) - np.rint(whole * 255).astype(np.int16)
            self.assertLessEqual(int(np.max(np.abs(difference))), 1)
            image.save(self.path)
        cropped = transform(rgb[32:128, 64:192], recipe, region=(0.25, 0.2, 0.75, 0.8))
        np.testing.assert_allclose(cropped, whole[32:128, 64:192], atol=2e-6)
        np.testing.assert_array_equal(transform(rgb, recipe.model_copy(update={"strength": 0.0})), rgb)
        np.testing.assert_allclose(transform(rgb, recipe.model_copy(update={"strength": 0.5})), rgb + (whole - rgb) * 0.5, atol=1e-7)

    def test_spatial_crop_render_uses_full_source_coordinates(self):
        gray = np.broadcast_to(np.linspace(0.12, 0.8, 256, dtype=np.float32)[None, :, None], (160, 256, 3))
        with Image.fromarray(np.rint(gray * 255).astype(np.uint8)) as image:
            image.save(self.path)
        recipe = NaturalEnhancement(version="natural-v2", local_exposure=np.linspace(-0.3, 0.3, 64).tolist(),
            clarity=0.2, base_luminance=np.tile(np.linspace(0.2, 0.8, 32), (32, 1)).ravel().tolist())
        settings = Settings(_env_file=None, database_url="postgresql://test:test@db.invalid/test?sslmode=require")
        full_bytes = render(self.path, NEUTRAL, settings, preview=False, enhancement=recipe)
        crop_bytes = render(self.path, NEUTRAL, settings, preview=False, enhancement=recipe,
            crop=Crop(x=64, y=32, width=128, height=96), original_size=(256, 160))
        with Image.open(BytesIO(full_bytes)) as full, Image.open(BytesIO(crop_bytes)) as cropped:
            self.assertLess(max(ImageStat.Stat(ImageChops.difference(full.crop((64, 32, 192, 128)), cropped)).mean), 1)

    def test_invalid_field_lengths_nonfinite_values_and_mixed_versions_are_rejected(self):
        for fields in ({"local_exposure": [0.1] * 63}, {"local_exposure": [0.1] * 65},
            {"base_luminance": [0.5] * 1023}, {"hue_chroma": [0] * 7}, {"clarity": 0.1},
            {"hue_chroma": [0, 0, float("nan"), 0, 0, 0]}, {"local_exposure": [float("inf")] * 64},
            {"base_luminance": [True] * 1024}):
            with self.assertRaises(ValidationError, msg=str(fields)[:90]):
                NaturalEnhancement.model_validate({"version": "natural-v2", **fields})
        with self.assertRaises(ValidationError):
            NaturalEnhancement(version="natural-v1", black_point=0.03)

    def test_v2_tonal_extremes_remain_monotone_and_preserve_neutral_endpoints(self):
        rgb = np.broadcast_to(np.linspace(0, 1, 512, dtype=np.float32)[None, :, None], (2, 512, 3))
        for exposure, shadows, highlights, contrast, black, white in product(
                (-1.25, 1.25), (0, 0.6), (0, 0.6), (-0.2, 0.3), (0, 0.08), (0, 0.12)):
            recipe = NaturalEnhancement(version="natural-v2", exposure_ev=exposure, shadows=shadows,
                highlights=highlights, tone_contrast=contrast, black_point=black, white_lift=white)
            output = transform(rgb, recipe)
            self.assertTrue(np.isfinite(output).all())
            self.assertTrue(np.all(np.diff(output[0, :, 0]) >= -1e-6))
            np.testing.assert_allclose(output[..., 0], output[..., 1], atol=1e-6)
            np.testing.assert_allclose(output[0, 0], 0, atol=1e-6)
            np.testing.assert_allclose(output[0, -1], 1, atol=1e-6)

    def test_tea_garden_receives_specific_visible_corrections_not_just_white_balance(self):
        path = PROJECT_DIR / "frontend/public/images/tea-garden-background.jpg"
        result = analyze(path)
        self.assertEqual(result.recipe.version, "natural-v3")
        self.assertGreater(result.recipe.strength, 0)
        self.assertGreater(result.recipe.black_point, 0.02)
        self.assertLess(result.recipe.hue_chroma[2], -0.08)
        self.assertTrue(result.recipe.local_exposure)
        self.assertTrue(any("green" in f.issue for f in result.assessment))
        with Image.open(path) as source:
            source = source.convert("RGB")
            source.thumbnail((768, 768))
            rgb = np.asarray(source, dtype=np.float32) / 255
        previous = transform(rgb, analyze_v1(path).recipe)
        enhanced = transform(rgb, result.recipe)
        previous_change = float(np.mean(np.abs(previous - rgb)))
        current_change = float(np.mean(np.abs(enhanced - rgb)))
        # Regression for the reported near-invisible correction, not a metric
        # claiming greater aesthetic preference just because more pixels change.
        self.assertGreater(current_change, previous_change * 1.8)
        self.assertGreater(current_change * 255, 5)
        old_y = to_srgb(_luminance(to_linear(rgb)))
        new_y = to_srgb(_luminance(to_linear(enhanced)))
        self.assertLess(float(np.mean(new_y[old_y > 0.8])), float(np.mean(old_y[old_y > 0.8])) - 0.015)


if __name__ == "__main__":
    unittest.main()
