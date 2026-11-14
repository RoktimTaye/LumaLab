"""Configuration checks without database access or real credentials."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.config import BACKEND_DIR, Settings, load_settings

DATABASE_URL = "postgresql://test:private-test-password@db.invalid/lumalab?sslmode=require"


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.system_environment = {
            key: value for key, value in os.environ.items()
            if key.upper() in {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "PATH", "TEMP", "TMP"}
        }
        self.environment = patch.dict(os.environ, self.system_environment, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.env_file = patch.dict(Settings.model_config, {"env_file": None})
        self.env_file.start()
        self.addCleanup(self.env_file.stop)

    def test_defaults_and_secret_masking(self):
        settings = Settings(database_url=DATABASE_URL)
        self.assertEqual(settings.temp_image_dir, BACKEND_DIR / ".runtime" / "images")
        self.assertEqual(settings.max_upload_bytes, 10_000_000)
        self.assertEqual(settings.max_image_pixels, 24_000_000)
        self.assertEqual(settings.max_image_side, 10_000)
        self.assertEqual(settings.preview_max_edge, 1_600)
        self.assertEqual(settings.image_ttl_seconds, 3_600)
        self.assertEqual(settings.cleanup_interval_seconds, 300)
        self.assertEqual(settings.jpeg_quality, 92)
        self.assertEqual(settings.allowed_origins, ())
        self.assertIsNone(settings.database_direct_url)
        self.assertEqual(settings.database_pool_max_size, 4)
        self.assertEqual(settings.database_timeout_seconds, 5)
        self.assertNotIn("private-test-password", repr(settings))
        self.assertNotIn("private-test-password", settings.model_dump_json())

    def test_database_urls_require_complete_postgresql_url_and_ssl(self):
        for field in ("database_url", "database_direct_url"):
            for value in ("", "not-a-url", "postgresql://db.invalid/lumalab?sslmode=require",
                          DATABASE_URL.replace("?sslmode=require", ""),
                          DATABASE_URL.replace("sslmode=require", "sslmode=prefer"),
                          DATABASE_URL.replace("sslmode=require", "sslmode=disable"),
                          DATABASE_URL + "&sslmode=disable"):
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    Settings(**{"database_url": DATABASE_URL, field: value})
            for mode in ("require", "verify-ca", "verify-full"):
                settings = Settings(**{"database_url": DATABASE_URL, field: DATABASE_URL.replace("require", mode)})
                self.assertIsNotNone(getattr(settings, field))

    def test_invalid_limits_and_private_storage(self):
        invalid = {
            "max_upload_bytes": 0, "max_image_pixels": -1, "max_image_side": 0,
            "preview_max_edge": 10_001, "image_ttl_seconds": 299,
            "cleanup_interval_seconds": 301, "jpeg_quality": 101,
            "database_pool_max_size": 0, "database_timeout_seconds": 61,
        }
        for field, value in invalid.items():
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Settings(database_url=DATABASE_URL, **{field: value})
        for path in (".", "..", "../public/images", "../dist", "../src", ".runtime/../../public",
                     "../frontend/public/images", "../frontend/dist"):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                Settings(database_url=DATABASE_URL, temp_image_dir=path)
        settings = Settings(database_url=DATABASE_URL, temp_image_dir=".runtime/custom")
        self.assertEqual(settings.temp_image_dir, BACKEND_DIR / ".runtime" / "custom")

    def test_origins_and_environment_parsing(self):
        os.environ.update(DATABASE_URL=DATABASE_URL, MAX_UPLOAD_BYTES="5000000",
                          ALLOWED_ORIGINS='["http://localhost:5173/","https://studio.example.com"]')
        settings = load_settings()
        self.assertEqual(settings.max_upload_bytes, 5_000_000)
        self.assertEqual(settings.allowed_origins, ("http://localhost:5173", "https://studio.example.com"))
        for origin in ("*", "https://*.example.com", "file://localhost", "https://user:pass@host",
                       "https://host/path", "https://host?query=1", "https://host#fragment", "http://host:bad"):
            with self.subTest(origin=origin), self.assertRaises(ValidationError):
                Settings(database_url=DATABASE_URL, allowed_origins=(origin,))
        os.environ["ALLOWED_ORIGINS"] = "invalid-json-private-value"
        with self.assertRaises(RuntimeError) as caught:
            load_settings()
        self.assertNotIn("invalid-json-private-value", str(caught.exception))

    def test_dotenv_precedence_example_and_unknown_keys(self):
        example = Settings(_env_file=BACKEND_DIR / ".env.example")
        self.assertEqual(example.jpeg_quality, 92)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8") as file:
            file.write(f"DATABASE_URL={DATABASE_URL}\nJPEG_QUALITY=80\n")
            path = Path(file.name)
        self.addCleanup(path.unlink)
        os.environ["JPEG_QUALITY"] = "90"
        self.assertEqual(Settings(_env_file=path).jpeg_quality, 90)
        path.write_text(f"DATABASE_URL={DATABASE_URL}\nMISSPELLED_SETTING=1\n", encoding="utf-8")
        with self.assertRaises(ValidationError):
            Settings(_env_file=path)

    def test_startup_accepts_valid_settings_and_redacts_invalid_values(self):
        code = (
            "from app.config import Settings; Settings.model_config['env_file'] = None; "
            "from app.main import app; assert app.state.settings.jpeg_quality == 92; "
            "assert app.openapi()['info']['title'] == 'LumaLab API'"
        )
        for value, success in ((DATABASE_URL, True), (None, False),
                               (DATABASE_URL.replace("sslmode=require", "sslmode=disable"), False)):
            environment = dict(self.system_environment)
            if value is not None:
                environment["DATABASE_URL"] = value
            result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR,
                                    env=environment, capture_output=True, text=True, timeout=15)
            with self.subTest(success=success, missing=value is None):
                self.assertEqual(result.returncode == 0, success)
                self.assertNotIn("private-test-password", result.stdout + result.stderr)
                if not success:
                    self.assertIn('"event": "configuration_invalid"', result.stderr)
                    self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
