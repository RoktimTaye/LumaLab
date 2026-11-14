"""Contract generation and CI drift checks against the actual API schema."""

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.contracts import generate, main, ts_type
from scripts.openapi import schema


class ContractTests(unittest.TestCase):
    def test_actual_schema_exports_without_opening_resources(self):
        with patch("app.lifespan.database_pool") as pool, patch("app.lifespan.temporary_storage") as storage:
            document = schema()
        pool.assert_not_called()
        storage.assert_not_called()
        generated = generate(document)
        self.assertIn('"file": Blob', generated)
        self.assertIn('"format"?: "jpeg"', generated)
        self.assertIn('"image/jpeg": Blob', generated)
        self.assertIn('content?: never', generated)
        self.assertEqual(sum(len(methods) for methods in document["paths"].values()), 8)
        changed = deepcopy(document)
        changed["components"]["schemas"]["Adjustments"]["properties"]["warmth"]["maximum"] = 49
        self.assertNotEqual(generate(changed), generated)

    def test_check_mode_reports_drift_without_rewriting_the_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "api.generated.ts"
            target.write_text(generate(schema()), encoding="utf-8")
            with patch("scripts.contracts.TARGET", target), patch("sys.argv", ["contracts", "--check"]):
                with redirect_stdout(StringIO()):
                    self.assertEqual(main(), 0)
                    target.write_text("// stale", encoding="utf-8")
                    self.assertEqual(main(), 1)
                self.assertEqual(target.read_text(encoding="utf-8"), "// stale")

    def test_unsupported_schema_shapes_fail_instead_of_silently_generating(self):
        for value in ({"anyOf": [{"type": "string"}, {"type": "null"}]},
                      {"type": "object", "additionalProperties": {"type": "string"}},
                      {"$ref": "https://example.invalid/schema.json"}, {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ts_type(value)


if __name__ == "__main__":
    unittest.main()
