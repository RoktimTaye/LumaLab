"""Source-scale detail improvement, protection and neighbourhood consistency."""

from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image
from pydantic import ValidationError

from app.schemas.images import NaturalEnhancement
from app.services.detail import sample_detail, texture_delta
from app.services.enhancement import analyze, apply, transform


class DetailTests(unittest.TestCase):
    @staticmethod
    def texture(height=160, width=256):
        x, y = np.meshgrid(np.arange(width), np.arange(height))
        return (0.45 + 0.06 * np.sin(x * 2 * np.pi / 9) + 0.035 * np.sin(y * 2 * np.pi / 17)).astype(np.float32)

    def test_real_texture_gains_separation_but_a_smooth_field_stays_smooth(self):
        gray = self.texture()
        rgb = np.repeat(gray[..., None], 3, axis=-1)
        recipe = NaturalEnhancement(version="natural-v3", texture=0.6, microcontrast=0.3, detail_reference_edge=256)
        output = transform(rgb, recipe)
        self.assertGreater(float(output[..., 0].std()), float(gray.std()) * 1.025)
        flat = np.full_like(rgb, 0.45)
        np.testing.assert_allclose(transform(flat, recipe), flat, atol=1e-7)
        ramp = np.broadcast_to(np.linspace(0.2, 0.7, 256, dtype=np.float32)[None, :, None], rgb.shape)
        np.testing.assert_allclose(transform(ramp, recipe)[:, 25:-25], ramp[:, 25:-25], atol=2e-6)

    def test_high_contrast_edges_do_not_get_large_halos_or_channel_clipping(self):
        rgb = np.full((100, 256, 3), 0.15, dtype=np.float32)
        rgb[:, 128:] = 0.85
        recipe = NaturalEnhancement(version="natural-v3", texture=0.6, microcontrast=0.35, detail_reference_edge=256)
        output = transform(rgb, recipe)
        self.assertGreater(float(output.min()), 0.14)
        self.assertLess(float(output.max()), 0.86)
        np.testing.assert_allclose(output[:, :90], rgb[:, :90], atol=1e-7)

    def test_warm_midtone_proxy_receives_less_texture_than_neutral_texture(self):
        gray = self.texture()
        neutral = np.repeat(gray[..., None], 3, axis=-1)
        warm = neutral + np.array([0.12, -0.03, -0.08], dtype=np.float32)
        recipe = NaturalEnhancement(version="natural-v3", texture=0.5, microcontrast=0.2)
        a, b = texture_delta(neutral, recipe, 1), texture_delta(warm, recipe, 1)
        self.assertLess(float(np.mean(np.abs(b))), float(np.mean(np.abs(a))) * 0.5)

    def test_halo_strips_match_whole_image_without_reprocessing_previous_rows(self):
        gray = self.texture(177, 256)
        rgb = np.stack([gray, gray * 0.9, gray * 0.7], axis=-1)
        pixels = np.rint(rgb * 255).astype(np.uint8)
        source = pixels.astype(np.float32) / 255
        recipe = NaturalEnhancement(version="natural-v3", texture=0.55, microcontrast=0.25,
            detail_reference_edge=256, shadows=0.12, clarity=0.1, base_luminance=[0.4] * 1024,
            local_exposure=np.linspace(-0.15, 0.15, 64).tolist())
        reference = np.rint(transform(source, recipe) * 255).astype(np.int16)
        with Image.fromarray(pixels) as image:
            apply(image, recipe)
            difference = np.asarray(image).astype(np.int16) - reference
            self.assertLessEqual(int(np.abs(difference).max()), 1)
            for row in (63, 64, 127, 128):
                self.assertLess(float(np.abs(difference[row]).mean()), 0.1)

    def test_zero_and_partial_strength_apply_to_the_whole_texture_result(self):
        rgb = np.repeat(self.texture()[..., None], 3, axis=-1)
        recipe = NaturalEnhancement(version="natural-v3", texture=0.5, microcontrast=0.2, detail_reference_edge=256)
        full = transform(rgb, recipe)
        np.testing.assert_array_equal(transform(rgb, recipe.model_copy(update={"strength": 0.0})), rgb)
        np.testing.assert_allclose(transform(rgb, recipe.model_copy(update={"strength": 0.5})), rgb + (full - rgb) * 0.5, atol=1e-7)

    def test_original_scale_samples_detect_texture_hidden_in_small_proxy(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path, proxy_path = Path(directory, "source.png"), Path(directory, "proxy.png")
            pixels = np.repeat(self.texture(512, 512)[..., None], 3, axis=-1)
            with Image.fromarray(np.rint(pixels * 255).astype(np.uint8)) as source:
                source.save(source_path)
            with Image.new("RGB", (64, 64), (115, 115, 115)) as proxy:
                proxy.save(proxy_path)
            stats = sample_detail(source_path)
            result = analyze(proxy_path, detail_path=source_path)
            self.assertEqual(result.recipe.detail_reference_edge, 512)
            self.assertGreater(result.recipe.texture, 0)
            self.assertEqual(stats["patches"], 5)
            self.assertTrue(any(f.area == "detail" for f in result.assessment))

    def test_source_noise_prevents_automatic_texture_amplification(self):
        rng = np.random.default_rng(20)
        gray = np.clip(0.45 + rng.normal(0, 0.055, (512, 512)), 0, 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "grain.png")
            with Image.fromarray(np.rint(gray * 255).astype(np.uint8)).convert("RGB") as image:
                image.save(path)
            recipe = analyze(path).recipe
            self.assertEqual(recipe.texture, 0)
            self.assertEqual(recipe.microcontrast, 0)
            self.assertGreater(recipe.detail_noise, 0.022)

    def test_old_versions_cannot_silently_change_to_the_new_detail_renderer(self):
        for version in ("natural-v1", "natural-v2"):
            with self.assertRaises(ValidationError):
                NaturalEnhancement(version=version, texture=0.1)
        for data in ({"texture": 0.7}, {"detail_noise": float("nan")}, {"detail_reference_edge": 0},
                     {"detail_reference_edge": True}, {"microcontrast": -0.1}):
            with self.assertRaises(ValidationError):
                NaturalEnhancement.model_validate({"version": "natural-v3", **data})


if __name__ == "__main__":
    unittest.main()
