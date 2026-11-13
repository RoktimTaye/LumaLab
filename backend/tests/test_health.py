"""Readiness contracts and resource probes without a live database."""

import asyncio
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from psycopg import OperationalError
from psycopg.errors import QueryCanceled
from psycopg_pool import PoolClosed, PoolTimeout, TooManyRequests

from app.config import RUNTIME_DIR
from app.db.pool import database_available, database_connection
from app.routes import router
from app.storage.runtime import storage_available


class HealthTests(unittest.TestCase):
    def setUp(self):
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self.directory = Path(tempfile.mkdtemp(prefix="test-a07-", dir=RUNTIME_DIR)).resolve()
        self.addCleanup(self.remove_test_directory)
        self.pool = MagicMock()
        self.connection = self.pool.connection.return_value.__enter__.return_value
        self.connection.execute.return_value.fetchone.return_value = (1,)
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.state.settings = SimpleNamespace(database_timeout_seconds=1)
        self.app.state.db_pool = self.pool
        self.app.state.storage_dir = self.directory

    def remove_test_directory(self):
        if self.directory.resolve().parent != RUNTIME_DIR.resolve():
            raise RuntimeError("Refusing cleanup outside the test directory.")
        shutil.rmtree(self.directory)

    def request(self):
        async def run():
            messages = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            await self.app({
                "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                "method": "GET", "scheme": "http", "path": "/api/v1/health",
                "raw_path": b"/api/v1/health", "query_string": b"", "root_path": "",
                "headers": [], "server": ("localhost", 8000), "client": ("localhost", 12345),
            }, receive, send)
            start = next(message for message in messages if message["type"] == "http.response.start")
            body = b"".join(message.get("body", b"") for message in messages)
            self.assertEqual(dict(start["headers"])[b"cache-control"], b"no-store")
            return start["status"], json.loads(body)

        return asyncio.run(run())

    def assert_unavailable(self):
        self.assertEqual(self.request(), (503, {"error": {
            "code": "service_unavailable", "message": "Database or temporary storage is unavailable.",
        }}))

    def test_ready_response_queries_database_and_cleans_probe(self):
        self.assertEqual(self.request(), (200, {"status": "ready"}))
        self.assertEqual(list(self.directory.iterdir()), [])
        self.pool.connection.assert_called_once_with(timeout=1)
        self.connection.execute.assert_any_call("SELECT set_config('statement_timeout', %s, true)", ("1s",))
        self.connection.execute.assert_any_call("SELECT 1")
        self.pool.connection.return_value.__exit__.assert_called_once()

    def test_pool_failures_are_unavailable_and_recover_on_next_request(self):
        for error_type in (PoolClosed, PoolTimeout, TooManyRequests, OperationalError):
            with self.subTest(error=error_type):
                self.pool.connection.side_effect = error_type("private-password host.private")
                self.assert_unavailable()
        self.pool.connection.side_effect = None
        self.assertEqual(self.request(), (200, {"status": "ready"}))

    def test_query_errors_and_unexpected_results_are_unavailable(self):
        for error_type in (OperationalError, QueryCanceled):
            with self.subTest(error=error_type):
                self.connection.execute.side_effect = error_type("private-database-detail")
                self.assert_unavailable()
        self.connection.execute.side_effect = None
        self.connection.execute.return_value.fetchone.return_value = None
        self.assert_unavailable()

    def test_absent_resources_are_unavailable(self):
        self.app.state.db_pool = None
        self.assert_unavailable()
        self.assertFalse(database_available(None, 1))
        self.app.state.db_pool = self.pool
        self.app.state.storage_dir = None
        self.assert_unavailable()
        self.app.state.storage_dir = self.directory / "missing"
        self.assert_unavailable()

    def test_connection_scope_passes_query_failure_to_pool_and_can_be_reused(self):
        error = QueryCanceled("private-query-detail")
        with self.assertRaises(QueryCanceled):
            with database_connection(self.pool, 1) as connection:
                self.assertIs(connection, self.connection)
                raise error
        release = self.pool.connection.return_value.__exit__
        self.assertIs(release.call_args.args[0], QueryCanceled)
        self.assertIs(release.call_args.args[1], error)
        with database_connection(self.pool, 1) as connection:
            self.assertIs(connection, self.connection)
        release.assert_called_with(None, None, None)

    def test_timeout_setup_failure_releases_connection_without_yielding(self):
        error = OperationalError("private-connection-detail")
        self.connection.execute.side_effect = error
        with self.assertRaises(OperationalError):
            with database_connection(self.pool, 1):
                self.fail("A connection without its timeout must not be used")
        release = self.pool.connection.return_value.__exit__
        self.assertIs(release.call_args.args[0], OperationalError)
        self.assertIs(release.call_args.args[1], error)

    def test_storage_failure_is_redacted_and_skips_database(self):
        for error in (PermissionError("private/path"), OSError("disk full")):
            with self.subTest(error=type(error)):
                with patch("app.storage.runtime.tempfile.NamedTemporaryFile", side_effect=error):
                    self.assert_unavailable()
        self.pool.connection.assert_not_called()
        self.assertEqual(self.request(), (200, {"status": "ready"}))

    def test_storage_probe_detects_failed_read_or_delete(self):
        with patch("app.storage.runtime.tempfile.NamedTemporaryFile") as factory:
            factory.return_value.__enter__.return_value.read.return_value = b"wrong"
            self.assertFalse(storage_available(self.directory))
            factory.return_value.__enter__.return_value.read.return_value = b"ok"
            factory.return_value.__exit__.side_effect = PermissionError("private/path")
            self.assertFalse(storage_available(self.directory))

    def test_openapi_documents_both_response_contracts(self):
        responses = self.app.openapi()["paths"]["/api/v1/health"]["get"]["responses"]
        self.assertEqual(responses["200"]["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/HealthResponse")
        self.assertEqual(responses["503"]["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/UnavailableResponse")

    def test_readiness_logs_only_the_failed_resource_category(self):
        self.pool.connection.side_effect = OperationalError("private-password private-host")
        with self.assertLogs("lumalab", level="WARNING") as captured:
            self.assert_unavailable()
        self.assertEqual(captured.output, ["WARNING:lumalab:readiness_database_unavailable"])
        self.app.state.storage_dir = None
        with self.assertLogs("lumalab", level="WARNING") as captured:
            self.assert_unavailable()
        self.assertEqual(captured.output, ["WARNING:lumalab:readiness_storage_unavailable"])


if __name__ == "__main__":
    unittest.main()
