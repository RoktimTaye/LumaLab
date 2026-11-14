"""Migration file and command safeguards without a live database."""

from contextlib import redirect_stdout
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import SecretStr

from app.config import Settings
from app.db.migrate import main, read_migrations, run_migrations


class MigrationTests(unittest.TestCase):
    def test_files_have_stable_checksums_and_unique_ordered_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "001_migration_history.sql"
            first.write_bytes(b"SELECT 1;\r\n")
            checksum = read_migrations(root)[0][2]
            first.write_bytes(b"SELECT 1;\n")
            self.assertEqual(read_migrations(root)[0][2], checksum)
            duplicate = root / "001_duplicate.sql"
            duplicate.write_text("SELECT 2;", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Duplicate"):
                read_migrations(root)
            duplicate.unlink()
            (root / "002_next.sql").write_text("SELECT 2;", encoding="utf-8")
            self.assertEqual([row[0] for row in read_migrations(root)],
                             ["001_migration_history.sql", "002_next.sql"])

    def test_invalid_empty_or_missing_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(RuntimeError):
                read_migrations(root)
            for name, content in (("bad.sql", "SELECT 1;"), ("001_migration_history.sql", " ")):
                path = root / name
                path.write_text(content, encoding="utf-8")
                with self.subTest(name=name), self.assertRaises(RuntimeError):
                    read_migrations(root)
                path.unlink()

    def test_missing_or_pooled_direct_url_never_opens_connection(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None,
                                database_url="postgresql://app:secret@db.invalid/db?sslmode=require")
        with patch("app.db.migrate.connect") as connect:
            with self.assertRaisesRegex(RuntimeError, "DATABASE_DIRECT_URL"):
                run_migrations(settings)
            pooled = settings.model_copy(update={"database_direct_url": SecretStr(
                "postgresql://owner:secret@ep-test-pooler.neon.tech/db?sslmode=require")})
            with self.assertRaisesRegex(RuntimeError, "direct connection"):
                run_migrations(pooled)
            connect.assert_not_called()

    def test_cli_failure_is_nonzero_and_does_not_expose_exception(self):
        output = StringIO()
        with patch("sys.argv", ["migrate"]), patch("app.db.migrate.configure_logging"):
            with patch("app.db.migrate.load_settings", side_effect=RuntimeError("private-password")):
                with redirect_stdout(output):
                    self.assertEqual(main(), 1)
        self.assertNotIn("private-password", output.getvalue())
        self.assertIn("Migration failed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
