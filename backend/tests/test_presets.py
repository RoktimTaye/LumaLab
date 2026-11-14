"""Preset validation contracts; no database access."""

import json
import unittest

from pydantic import ValidationError

from app.db.seed import PRESETS
from app.schemas.presets import Preset

BOUNDS = {
    "brightness": (0, 200), "contrast": (0, 200), "saturation": (0, 200),
    "warmth": (-50, 50), "sharpness": (0, 100), "vignette": (0, 100),
}


class PresetTests(unittest.TestCase):
    def setUp(self):
        self.preset = dict(zip(Preset.model_fields, PRESETS[0], strict=True))

    def test_seed_values_and_inclusive_boundaries_are_preserved(self):
        for row in PRESETS:
            model = Preset.model_validate(dict(zip(Preset.model_fields, row, strict=True)))
            self.assertEqual(tuple(model.model_dump().values()), row)
            self.assertEqual(Preset.model_validate_json(model.model_dump_json()), model)
        for field, bounds in BOUNDS.items():
            for value in bounds:
                with self.subTest(field=field, value=value):
                    self.assertEqual(getattr(Preset.model_validate({**self.preset, field: value}), field), value)

    def test_out_of_range_and_noninteger_adjustments_are_rejected(self):
        for field, (minimum, maximum) in BOUNDS.items():
            for value in (minimum - 1, maximum + 1, True, False, 1.0, 1.5, "1", None, float("nan")):
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    Preset.model_validate({**self.preset, field: value})
            with self.subTest(field=field, source="json"), self.assertRaises(ValidationError):
                Preset.model_validate_json(json.dumps({**self.preset, field: "1"}))

    def test_complete_definition_and_strict_text_fields_are_required(self):
        for field in self.preset:
            data = self.preset.copy()
            del data[field]
            with self.subTest(missing=field), self.assertRaises(ValidationError):
                Preset.model_validate(data)
        for field in ("preset_id", "preset_name", "description"):
            for value in (None, 123):
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    Preset.model_validate({**self.preset, field: value})
        with self.assertRaises(ValidationError):
            Preset.model_validate({**self.preset, "unexpected": 1})


if __name__ == "__main__":
    unittest.main()
