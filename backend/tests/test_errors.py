"""Shared error envelopes redact input and exception details across the application."""

import asyncio
import json
import unittest

from fastapi import FastAPI
from starlette.exceptions import HTTPException

from app.errors import EXCEPTION_HANDLERS
from app.middleware import with_cors
from app.schemas.images import PreviewRequest

PRIVATE = "private-token private-password C:/private/photo.jpg"


class ErrorTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI(exception_handlers=EXCEPTION_HANDLERS)

        @self.app.get("/query")
        def query(count: int):
            return {"count": count}

        @self.app.post("/body")
        def body(value: PreviewRequest):
            return value

        @self.app.get("/http/{status}")
        def http(status: int):
            raise HTTPException(status, detail={"private": PRIVATE}, headers={
                "Retry-After": "5", "WWW-Authenticate": "Bearer", "X-Private": PRIVATE,
            })

        @self.app.get("/crash")
        def crash():
            raise RuntimeError(PRIVATE)

        @self.app.get("/invalid-response", response_model=dict[str, int])
        def invalid_response():
            return {"value": PRIVATE}

    def request(self, path, method="GET", body=b"", query=b""):
        async def run():
            messages = []
            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            async def send(message):
                messages.append(message)
            try:
                await getattr(self, "asgi_app", self.app)({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                    "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
                    "query_string": query, "root_path": "", "headers": [(b"content-type", b"application/json"), *getattr(self, "headers", [])],
                    "server": ("localhost", 8000), "client": ("localhost", 12345)}, receive, send)
            except Exception:
                # Starlette re-raises server exceptions after sending its handled 500.
                if not any(item.get("status") == 500 for item in messages):
                    raise
            start = next(item for item in messages if item["type"] == "http.response.start")
            headers = dict(start["headers"])
            data = b"".join(item.get("body", b"") for item in messages)
            self.assertEqual(headers[b"cache-control"], b"no-store")
            self.assertEqual(headers[b"content-type"], b"application/json")
            self.assertNotIn(b"private", data)
            payload = json.loads(data)
            self.assertEqual(set(payload), {"error"})
            self.assertEqual(set(payload["error"]), {"code", "message"})
            return start["status"], headers, payload["error"]
        return asyncio.run(run())

    def test_request_validation_and_malformed_json_are_generic(self):
        for path, method, body, query in (("/query", "GET", b"", b"count=private-token"),
                ("/body", "POST", b'{"private":"private-token"}', b""),
                ("/body", "POST", b'{"private":', b"")):
            with self.subTest(path=path, body=body):
                status, _, error = self.request(path, method, body, query)
                self.assertEqual(status, 422)
                self.assertEqual(error["code"], "invalid_request")

    def test_router_404_405_and_protocol_headers(self):
        self.assertEqual(self.request("/private-token")[2]["code"], "not_found")
        status, headers, error = self.request("/query", "DELETE")
        self.assertEqual((status, error["code"]), (405, "method_not_allowed"))
        self.assertIn(b"GET", headers[b"allow"])
        for status in (400, 401, 403, 413, 415, 429, 503):
            with self.subTest(status=status):
                actual, headers, _ = self.request(f"/http/{status}")
                self.assertEqual(actual, status)
                self.assertEqual(headers[b"retry-after"], b"5")
                self.assertEqual(headers[b"www-authenticate"], b"Bearer")
                self.assertNotIn(b"x-private", headers)

    def test_unexpected_and_response_validation_errors_are_safe_500(self):
        for path in ("/crash", "/invalid-response"):
            with self.subTest(path=path), self.assertLogs("lumalab", level="ERROR") as logs:
                status, _, error = self.request(path)
                self.assertEqual((status, error["code"]), (500, "internal_error"))
            self.assertEqual(logs.output, ["ERROR:lumalab:request_failed"])

    def test_outer_cors_also_covers_unexpected_500_responses(self):
        self.asgi_app = with_cors(self.app, ("http://localhost:5173",))
        self.headers = [(b"origin", b"http://localhost:5173")]
        with self.assertLogs("lumalab", level="ERROR"):
            status, headers, _ = self.request("/crash")
        self.assertEqual(status, 500)
        self.assertEqual(headers[b"access-control-allow-origin"], b"http://localhost:5173")
        self.assertIn(b"Content-Disposition", headers[b"access-control-expose-headers"])


if __name__ == "__main__":
    unittest.main()
