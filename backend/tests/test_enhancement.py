"""Photographic invariants independent of a learned-model quality claim."""

from io import BytesIO
from itertools import product
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageChops, ImageCms, ImageStat
from pydantic import ValidationError

from app.config import Settings
from app.schemas.images import Crop, NaturalEnhancement
from app.services.enhancement import NEUTRAL, analyze, apply, transform
from app.services.images import render


class EnhancementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name, "source.png")

    def analyze_rgb(self, rgb):
        with Image.fromarray(np.rint(np.clip(rgb, 0, 1) * 255).astype(np.uint8)) as image:
            image.save(self.path)
        return analyze(self.path)

    @staticmethod
    def ramp(low, high, *, color=(1, 1, 1)):
        gray = np.broadcast_to(np.linspace(low, high, 256, dtype=np.float32)[None, :, None], (64, 256, 3))
        return gray * np.array(color, dtype=np.float32)

    def test_underexposed_gradient_lifts_without_clipping_or_reversing_tones(self):
        rgb = self.ramp(0.04, 0.52)
        result = self.analyze_rgb(rgb)
        self.assertGreater(result.recipe.exposure_ev, 0.15)
        output = transform(rgb, result.recipe)
        self.assertGreater(float(np.median(output)), float(np.median(rgb)) + 0.025)
        self.assertLess(float(output.max()), 1)
        self.assertTrue(np.all(np.diff(output[0, :, 0]) > 0))

    def test_night_and_sunset_intent_and_dominant_scene_color(self):
        night = self.ramp(0.01, 0.17)
        result = self.analyze_rgb(night)
        self.assertLessEqual(float(np.median(transform(night, result.recipe))), 0.12)
        self.assertIn("low-light", result.message)
        for color in ((1, 0.42, 0.15), (0.2, 1, 0.12)):
            result = self.analyze_rgb(self.ramp(0.1, 0.9, color=color))
            self.assertEqual((result.recipe.red_gain, result.recipe.green_gain, result.recipe.blue_gain), (1, 1, 1))

    def test_neutral_cast_is_reduced_without_neutralizing_saturated_objects(self):
        rgb = self.ramp(0.2, 0.75, color=(1.06, 1, 0.95))
        result = self.analyze_rgb(rgb)
        output = transform(rgb, result.recipe)
        self.assertLess(float(np.mean(output[..., 0] - output[..., 2])), float(np.mean(rgb[..., 0] - rgb[..., 2])))
        self.assertLess(result.recipe.red_gain, result.recipe.blue_gain)

    def test_already_balanced_and_flat_images_need_no_aggressive_correction(self):
        rgb = self.ramp(0, 1)
        result = self.analyze_rgb(rgb)
        self.assertLess(float(np.mean(np.abs(transform(rgb, result.recipe) - rgb))), 0.015)
        for color in ((0, 0, 0), (1, 1, 1), (0.35, 0.35, 0.35), (1, 0, 0)):
            flat = np.full((8, 8, 3), color, dtype=np.float32)
            result = self.analyze_rgb(flat)
            np.testing.assert_array_equal(transform(flat, result.recipe), flat)

    def test_extreme_bounded_curves_are_monotone_finite_and_neutral(self):
        gray = self.ramp(0, 1)
        for exposure, shadows, highlights, contrast in product((-1.25, 1.25), (0, 0.6), (0, 0.6), (0, 0.2)):
            recipe = NaturalEnhancement(exposure_ev=exposure, shadows=shadows, highlights=highlights, contrast=contrast)
            output = transform(gray, recipe)
            self.assertTrue(np.isfinite(output).all())
            self.assertTrue(np.all(np.diff(output[0, :, 0]) >= 0))
            np.testing.assert_allclose(output[..., 0], output[..., 1], atol=1e-6)
            np.testing.assert_allclose(output[..., 1], output[..., 2], atol=1e-6)
            np.testing.assert_allclose(output[0, 0], 0, atol=1e-6)
            np.testing.assert_allclose(output[0, -1], 1, atol=1e-6)

    def test_strength_zero_is_exact_and_strip_boundaries_do_not_change_output(self):
        rng = np.random.default_rng(4)
        pixels = rng.integers(0, 256, (149, 65, 3), dtype=np.uint8)
        recipe = NaturalEnhancement(exposure_ev=0.7, shadows=0.3, highlights=0.2, vibrance=0.08,
                                    red_gain=1.05, green_gain=0.99, blue_gain=0.97)
        np.testing.assert_array_equal(transform(pixels / np.float32(255), recipe.model_copy(update={"strength": 0.0})), pixels / np.float32(255))
        with Image.fromarray(pixels) as image:
            apply(image, recipe)
            expected = np.rint(transform(pixels / np.float32(255), recipe) * 255).astype(np.uint8)
            np.testing.assert_array_equal(np.asarray(image), expected)

    def test_lifted_saturated_colors_keep_variation_instead_of_flattening_at_white(self):
        rgb = self.ramp(0.15, 0.95, color=(0.25, 1, 0.18))
        output = transform(rgb, NaturalEnhancement(exposure_ev=0.85, shadows=0.3))
        self.assertLess(float(output.max()), 0.995)
        self.assertTrue(np.all(np.diff(output[0, :, 1]) > 0))
        self.assertTrue(np.all(output[..., 1] > output[..., 0]))
        self.assertTrue(np.all(output[..., 1] > output[..., 2]))

    def test_strength_blends_the_whole_effect_continuously(self):
        rgb = self.ramp(0.1, 0.95, color=(0.25, 1, 0.18))
        recipe = NaturalEnhancement(exposure_ev=0.7, red_gain=0.98, blue_gain=1.04, vibrance=0.1)
        full = transform(rgb, recipe)
        for strength in (0.00001, 0.25, 0.5, 0.75):
            partial = transform(rgb, recipe.model_copy(update={"strength": strength}))
            np.testing.assert_allclose(partial, rgb + (full - rgb) * strength, atol=1e-7)

    def test_invalid_recipes_do_not_allow_nonfinite_values_versions_or_extras(self):
        for value in (float('nan'), float('inf'), float('-inf'), -2, 2, True, '0.5'):
            with self.assertRaises(ValidationError):
                NaturalEnhancement(strength=value)
        for data in ({"version": "untrusted"}, {"red_gain": 2.0}, {"shadows": -1.0}, {"path": "../source"}):
            with self.assertRaises(ValidationError):
                NaturalEnhancement.model_validate(data)

    def test_same_recipe_is_repeatable_crop_consistent_and_embeds_output_profile(self):
        rgb = self.ramp(0.04, 0.54)
        recipe = self.analyze_rgb(rgb).recipe
        settings = Settings(_env_file=None, database_url="postgresql://test:test@db.invalid/test?sslmode=require", preview_max_edge=512)
        before = self.path.read_bytes()
        first = render(self.path, NEUTRAL, settings, preview=True, enhancement=recipe)
        exported = render(self.path, NEUTRAL, settings, preview=False, enhancement=recipe)
        self.assertEqual(first, exported)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(analyze(self.path).recipe, recipe)
        zero = recipe.model_copy(update={"strength": 0.0})
        self.assertEqual(render(self.path, NEUTRAL, settings, preview=True, enhancement=zero), render(self.path, NEUTRAL, settings, preview=True))
        cropped = render(self.path, NEUTRAL, settings, preview=False, enhancement=recipe,
                         crop=Crop(x=128, y=0, width=128, height=64), original_size=(256, 64))
        with Image.open(BytesIO(first)) as full, Image.open(BytesIO(cropped)) as crop:
            ImageCms.ImageCmsProfile(BytesIO(full.info["icc_profile"]))
            self.assertFalse(full.getexif())
            # x=128 is aligned to JPEG's block grid: no changed global statistics.
            difference = ImageStat.Stat(ImageChops.difference(full.crop((128, 0, 256, 64)), crop)).mean
            self.assertLess(max(difference), 1)

    def test_preview_tracks_downsampled_export_at_a_different_resolution(self):
        rng = np.random.default_rng(12)
        gray = np.broadcast_to(np.linspace(0.03, 0.85, 1920, dtype=np.float32)[None, :, None], (1080, 1920, 3))
        pixels = np.rint(np.clip(gray + rng.normal(0, 0.015, gray.shape), 0, 1) * 255).astype(np.uint8)
        with Image.fromarray(pixels) as source:
            source.save(self.path)
            source.thumbnail((960, 960), Image.Resampling.LANCZOS)
            preview_source = Path(self.temp.name, "preview.png")
            source.save(preview_source)
        settings = Settings(_env_file=None, database_url="postgresql://test:test@db.invalid/test?sslmode=require", preview_max_edge=960)
        recipe = analyze(self.path).recipe
        preview = render(preview_source, NEUTRAL, settings, preview=True, enhancement=recipe)
        exported = render(self.path, NEUTRAL, settings, preview=False, enhancement=recipe)
        with Image.open(BytesIO(preview)) as small, Image.open(BytesIO(exported)) as full:
            reference = full.resize(small.size, Image.Resampling.LANCZOS)
            self.assertLess(max(ImageStat.Stat(ImageChops.difference(small, reference)).mean), 2)


if __name__ == "__main__":
    unittest.main()
