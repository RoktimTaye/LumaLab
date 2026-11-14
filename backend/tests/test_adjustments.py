"""Strict adjustment contracts shared by preview, export and enhancement."""

import json
import unittest

from pydantic import ValidationError

from app.schemas.images import Adjustments

BOUNDS = {
    "brightness": (0, 200), "contrast": (0, 200), "saturation": (0, 200),
    "warmth": (-50, 50), "sharpness": (0, 100), "vignette": (0, 100),
}
NEUTRAL = dict(brightness=100, contrast=100, saturation=100, warmth=0, sharpness=0, vignette=0)


class AdjustmentTests(unittest.TestCase):
    def test_inclusive_boundaries_are_preserved_and_documented(self):
        schema = Adjustments.model_json_schema()
        self.assertEqual(set(schema["required"]), set(BOUNDS))
        self.assertFalse(schema["additionalProperties"])
        for field, (minimum, maximum) in BOUNDS.items():
            documented = schema["properties"][field]
            self.assertEqual((documented["type"], documented["minimum"], documented["maximum"]),
                             ("integer", minimum, maximum))
            for value in (minimum, maximum):
                data = {**NEUTRAL, field: value}
                self.assertEqual(Adjustments.model_validate(data).model_dump(), data)
                self.assertEqual(Adjustments.model_validate_json(json.dumps(data)).model_dump(), data)

    def test_no_coercion_clamping_missing_fields_or_extras(self):
        for field, (minimum, maximum) in BOUNDS.items():
            for value in (minimum - 1, maximum + 1, 1.5, 1.0, "1", True, False, None):
                data = {**NEUTRAL, field: value}
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValidationError):
                        Adjustments.model_validate(data)
                    with self.assertRaises(ValidationError):
                        Adjustments.model_validate_json(json.dumps(data))
            incomplete = NEUTRAL.copy()
            del incomplete[field]
            with self.subTest(missing=field), self.assertRaises(ValidationError):
                Adjustments.model_validate(incomplete)
        with self.assertRaises(ValidationError):
            Adjustments.model_validate({**NEUTRAL, "unexpected": 1})


if __name__ == "__main__":
    unittest.main()
