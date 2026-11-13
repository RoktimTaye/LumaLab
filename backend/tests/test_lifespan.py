"""Resource lifecycle checks with real local storage and no database connections."""

import asyncio
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI

from app.config import RUNTIME_DIR, Settings
from app.lifespan import lifespan
from app.storage.runtime import temporary_storage


class LifespanTests(unittest.TestCase):
    def setUp(self):
        environment = {key: value for key, value in os.environ.items() if key.lower() not in Settings.model_fields}
        self.environment = patch.dict(os.environ, environment, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self.test_root = Path(tempfile.mkdtemp(prefix="test-a06-", dir=RUNTIME_DIR)).resolve()
        self.addCleanup(self.remove_test_directory)
        self.settings = Settings(
            _env_file=None,
            database_url="postgresql://test:private-test-password@db.invalid/lumalab?sslmode=require",
            temp_image_dir=self.test_root / "images",
        )
        self.app = FastAPI(lifespan=lifespan)
        self.app.state.settings = self.settings

    def remove_test_directory(self):
        if self.test_root.resolve().parent != RUNTIME_DIR.resolve():
            raise RuntimeError("Refusing cleanup outside the test directory.")
        shutil.rmtree(self.test_root)

    def test_startup_and_shutdown_release_only_owned_resources(self):
        root = self.settings.temp_image_dir
        root.mkdir()
        unrelated = root / "keep.txt"
        unrelated.write_text("unrelated", encoding="utf-8")

        async def check():
            async with self.app.router.lifespan_context(self.app):
                pool = self.app.state.db_pool
                directory = self.app.state.storage_dir
                self.assertFalse(pool.closed)
                self.assertEqual(pool.get_stats()["pool_size"], 0)
                self.assertEqual(pool.max_size, self.settings.database_pool_max_size)
                self.assertEqual(pool.max_waiting, self.settings.database_pool_max_size * 2)
                self.assertEqual(pool.timeout, self.settings.database_timeout_seconds)
                self.assertEqual(pool.max_lifetime, 1_800)
                self.assertEqual(pool.max_idle, 60)
                self.assertEqual(directory.parent, root)
                (directory / "probe.txt").write_text("temporary", encoding="utf-8")
                if os.name != "nt":
                    self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertTrue(pool.closed)
            self.assertFalse(directory.exists())
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "unrelated")
            self.assertIsNone(self.app.state.db_pool)
            self.assertIsNone(self.app.state.storage_dir)
            async with self.app.router.lifespan_context(self.app):
                self.assertNotEqual(self.app.state.storage_dir, directory)
                self.assertFalse(self.app.state.db_pool.closed)

        asyncio.run(check())

    def test_application_error_or_cancellation_still_cleans_resources(self):
        async def check():
            for error in (RuntimeError("application error"), asyncio.CancelledError()):
                with self.assertRaises(type(error)):
                    async with self.app.router.lifespan_context(self.app):
                        pool = self.app.state.db_pool
                        directory = self.app.state.storage_dir
                        raise error
                self.assertTrue(pool.closed)
                self.assertFalse(directory.exists())
                self.assertIsNone(self.app.state.db_pool)
                self.assertIsNone(self.app.state.storage_dir)

        asyncio.run(check())

    def test_failed_pool_startup_closes_pool_and_removes_directory(self):
        async def check():
            with patch("app.db.pool.ConnectionPool", autospec=True) as factory:
                pool = factory.return_value
                pool.open.side_effect = RuntimeError("private-test-password")
                with self.assertRaisesRegex(RuntimeError, "Unable to initialize the database pool") as caught:
                    async with self.app.router.lifespan_context(self.app):
                        self.fail("Startup must fail")
                self.assertNotIn("private-test-password", str(caught.exception))
                pool.close.assert_called_once()
                self.assertEqual(list(self.settings.temp_image_dir.iterdir()), [])
                self.assertIsNone(self.app.state.db_pool)
                self.assertIsNone(self.app.state.storage_dir)

        asyncio.run(check())

    def test_pool_close_failure_still_cleans_storage(self):
        async def check():
            with patch("app.db.pool.ConnectionPool", autospec=True) as factory:
                factory.return_value.close.side_effect = RuntimeError("private-test-password")
                with self.assertRaisesRegex(RuntimeError, "Unable to close the database pool"):
                    async with self.app.router.lifespan_context(self.app):
                        directory = self.app.state.storage_dir
                self.assertFalse(directory.exists())
                self.assertIsNone(self.app.state.db_pool)
                self.assertIsNone(self.app.state.storage_dir)

        asyncio.run(check())

    def test_unwritable_storage_does_not_open_pool(self):
        async def check():
            with patch("app.storage.runtime.tempfile.mkdtemp", side_effect=PermissionError("private/path")):
                with patch("app.db.pool.ConnectionPool", autospec=True) as factory:
                    with self.assertRaisesRegex(RuntimeError, "Unable to initialize private temporary storage") as caught:
                        async with self.app.router.lifespan_context(self.app):
                            self.fail("Startup must fail")
                    self.assertNotIn("private/path", str(caught.exception))
                    factory.assert_not_called()

        asyncio.run(check())

    def test_cleanup_rejects_substituted_path(self):
        storage = temporary_storage(self.settings.temp_image_dir)
        directory = storage.__enter__()
        with patch.object(Path, "resolve", return_value=self.test_root):
            with self.assertRaisesRegex(RuntimeError, "cleanup refused"):
                storage.__exit__(None, None, None)
        self.assertTrue(directory.exists())


if __name__ == "__main__":
    unittest.main()
