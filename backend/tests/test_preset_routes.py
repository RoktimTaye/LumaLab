"""Preset API contracts with simulated database rows and failures."""

import asyncio
import json
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from fastapi import FastAPI
from psycopg import OperationalError
from psycopg.errors import QueryCanceled
from psycopg_pool import PoolClosed, PoolTimeout, TooManyRequests

from app.db.seed import PRESETS
from app.routes import router
from app.schemas.presets import Preset


class PresetRouteTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(zip(Preset.model_fields, row, strict=True)) for row in PRESETS]
        self.pool = MagicMock()
        self.connection = self.pool.connection.return_value.__enter__.return_value
        self.cursor = self.connection.cursor.return_value.__enter__.return_value
        self.cursor.fetchall.return_value = self.rows
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.state.settings = SimpleNamespace(database_timeout_seconds=1)
        self.app.state.db_pool = self.pool

    def request(self, method="GET"):
        async def run():
            messages = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            await self.app({
                "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                "method": method, "scheme": "http", "path": "/api/v1/presets",
                "raw_path": b"/api/v1/presets", "query_string": b"", "root_path": "",
                "headers": [], "server": ("localhost", 8000), "client": ("localhost", 12345),
            }, receive, send)
            start = next(message for message in messages if message["type"] == "http.response.start")
            if method == "GET":
                self.assertEqual(dict(start["headers"])[b"cache-control"], b"no-store")
            body = b"".join(message.get("body", b"") for message in messages)
            return start["status"], json.loads(body)

        return asyncio.run(run())

    def assert_unavailable(self):
        with self.assertLogs("lumalab", level="WARNING") as captured:
            self.assertEqual(self.request(), (503, {"error": {
                "code": "service_unavailable", "message": "Presets are temporarily unavailable.",
            }}))
        self.assertEqual(captured.output, ["WARNING:lumalab:presets_unavailable"])

    def test_complete_definitions_come_from_database_and_preserve_display_order(self):
        self.rows[1] = {**self.rows[1], "brightness": 99, "description": "Database definition"}
        self.assertEqual(self.request(), (200, self.rows))
        self.pool.connection.assert_called_once_with(timeout=1)
        self.pool.connection.return_value.__exit__.assert_called_once_with(None, None, None)
        self.cursor.execute.assert_called_once()

    def test_pool_failures_are_redacted_and_a_later_request_can_recover(self):
        for error_type in (PoolClosed, PoolTimeout, TooManyRequests, OperationalError):
            with self.subTest(error=error_type):
                self.pool.connection.side_effect = error_type("private-password private-host")
                self.assert_unavailable()
        self.pool.connection.side_effect = None
        self.assertEqual(self.request(), (200, self.rows))

    def test_query_failures_release_connection_and_hide_details(self):
        for error_type in (OperationalError, QueryCanceled):
            with self.subTest(error=error_type):
                self.cursor.execute.side_effect = error_type("private-query-detail")
                self.assert_unavailable()
                self.assertIs(self.pool.connection.return_value.__exit__.call_args.args[0], error_type)
        self.cursor.execute.side_effect = None
        self.assertEqual(self.request(), (200, self.rows))

    def test_missing_pool_or_incomplete_invalid_definitions_are_unavailable(self):
        self.app.state.db_pool = None
        self.assert_unavailable()
        self.app.state.db_pool = self.pool
        invalid_rows = [[], self.rows[:-1], [self.rows[0]] * 5,
                        [{**self.rows[0], "brightness": True}, *self.rows[1:]]]
        for rows in invalid_rows:
            with self.subTest(rows=rows):
                self.cursor.fetchall.return_value = rows
                self.assert_unavailable()

    def test_write_methods_are_not_exposed(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                self.assertEqual(self.request(method)[0], 405)
        self.pool.connection.assert_not_called()

    def test_openapi_documents_typed_list_and_service_unavailable(self):
        responses = self.app.openapi()["paths"]["/api/v1/presets"]["get"]["responses"]
        schema = responses["200"]["content"]["application/json"]["schema"]
        self.assertEqual(schema["type"], "array")
        self.assertEqual(schema["items"]["$ref"], "#/components/schemas/Preset")
        self.assertEqual(responses["503"]["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/UnavailableResponse")


if __name__ == "__main__":
    unittest.main()
