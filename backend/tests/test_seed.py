"""Seed command connection and error-output safeguards without a live database."""

from contextlib import redirect_stdout
from io import StringIO
import os
import unittest
from unittest.mock import MagicMock, patch

from psycopg import OperationalError
from pydantic import SecretStr, ValidationError

from app.config import Settings
from app.db.seed import PRESETS, main, run_seed, seed_presets
from app.schemas.presets import Preset


class SeedTests(unittest.TestCase):
    def test_missing_or_pooled_owner_url_never_uses_application_connection(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None,
                                database_url="postgresql://app:secret@db.invalid/db?sslmode=require")
        with patch("app.db.seed.connect") as connect:
            with self.assertRaisesRegex(RuntimeError, "DATABASE_DIRECT_URL"):
                run_seed(settings)
            pooled = settings.model_copy(update={"database_direct_url": SecretStr(
                "postgresql://owner:secret@ep-test-pooler.neon.tech/db?sslmode=require")})
            with self.assertRaisesRegex(RuntimeError, "direct owner connection"):
                run_seed(pooled)
            connect.assert_not_called()

    def test_invalid_final_seed_is_rejected_before_any_upsert(self):
        connection = MagicMock()
        for row in ((*PRESETS[-1][:-1], 101), PRESETS[-1][:-1], (*PRESETS[-1], 0)):
            with self.subTest(length=len(row)), patch("app.db.seed.PRESETS", (*PRESETS[:-1], row)):
                with self.assertRaises(ValueError):
                    seed_presets(connection)
        connection.cursor.assert_not_called()

    def test_cli_database_and_validation_failures_hide_private_details(self):
        with self.assertRaises(ValidationError) as caught:
            Preset.model_validate({"private-field": "private-value"})
        for error in (OperationalError("private-password private-host"), caught.exception):
            output = StringIO()
            with patch("sys.argv", ["seed"]), patch("app.db.seed.configure_logging"):
                with patch("app.db.seed.load_settings"):
                    with patch("app.db.seed.run_seed", side_effect=error):
                        with redirect_stdout(output):
                            self.assertEqual(main(), 1)
            self.assertIn("Seeding failed", output.getvalue())
            self.assertNotIn("private-", output.getvalue())


if __name__ == "__main__":
    unittest.main()
