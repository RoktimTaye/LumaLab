"""Regression checks for audit fixes without connecting to an external database."""

import asyncio
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from fastapi import FastAPI
from PIL import Image, ImageEnhance, ImageFilter
from psycopg import OperationalError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config import Settings
from app.deploy import main as deploy
from app.db.readiness import validate_database
from app.middleware import PrivateImageCache, SecurityHeaders, with_cors
from app.rate_limit import UploadRateLimit
from app.schemas.images import Adjustments
from app.services.images import render
from app.static import FrontendStaticFiles


def request(app, path, method="GET", headers=(), client="10.0.0.2"):
    async def run():
        messages = []
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        async def send(message):
            messages.append(message)
        try:
            await app({"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"}, "http_version": "1.1",
                       "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
                       "query_string": b"", "root_path": "", "headers": list(headers),
                       "server": ("localhost", 8000), "client": (client, 12345)}, receive, send)
        except RuntimeError:
            if not any(item.get("status") == 500 for item in messages):
                raise
        start = next(item for item in messages if item["type"] == "http.response.start")
        return start["status"], dict(start["headers"]), b"".join(item.get("body", b"") for item in messages)
    return asyncio.run(run())


class HardeningTests(unittest.TestCase):
    def test_deploy_bootstraps_only_with_owner_url_and_stops_on_failure(self):
        from types import SimpleNamespace
        for direct in (None, "owner-url"):
            with (patch("app.deploy.load_settings", return_value=SimpleNamespace(database_direct_url=direct)),
                  patch("app.deploy.run_migrations") as migrate,
                  patch("app.deploy.run_seed") as seed,
                  patch("app.deploy.configure_logging"),
                  patch("app.deploy.uvicorn.run") as server,
                  patch.dict("os.environ", {"PORT": "8123", "FORWARDED_ALLOW_IPS": "10.0.0.2"})):
                self.assertEqual(deploy(), 0)
                self.assertEqual(migrate.call_count, int(direct is not None))
                self.assertEqual(seed.call_count, int(direct is not None))
                self.assertEqual(server.call_args.kwargs["forwarded_allow_ips"], "10.0.0.2")
                self.assertEqual(server.call_args.kwargs["port"], 8123)
                if direct:
                    server.reset_mock()
                    seed.reset_mock()
                    migrate.side_effect = RuntimeError("migration failed")
                    self.assertEqual(deploy(), 1)
                    seed.assert_not_called()
                    server.assert_not_called()

    def test_spa_navigation_keeps_missing_api_and_assets_as_404(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "index.html").write_text("<html>studio</html>")
            app = FastAPI()
            app.mount("/", FrontendStaticFiles(directory=directory, html=True))
            for path in ("/studio", "/studio/", "/unknown/nested-route"):
                self.assertEqual(request(app, path)[0], 200)
                self.assertEqual(request(app, path, "HEAD")[2], b"")
            for path in ("/api", "/api/missing", "/assets/missing.js", "/images/missing", "/missing.css", "/.env"):
                self.assertEqual(request(app, path)[0], 404)
            self.assertEqual(request(app, "/unknown", "POST")[0], 405)

    def test_security_and_private_headers_cover_errors_and_preflight(self):
        app = FastAPI()
        @app.get("/api/v1/images/crash")
        def crash():
            raise RuntimeError("private")
        wrapped = SecurityHeaders(PrivateImageCache(with_cors(app, ("https://studio.example",))))
        for path, method, headers in (
            ("/missing", "GET", ()),
            ("/api/v1/images/crash", "GET", ((b"origin", b"https://studio.example"),)),
            ("/api/v1/images", "OPTIONS", ((b"origin", b"https://studio.example"),
                                           (b"access-control-request-method", b"POST"))),
        ):
            status, result, _ = request(wrapped, path, method, headers)
            self.assertEqual(result[b"x-content-type-options"], b"nosniff")
            self.assertEqual(result[b"x-frame-options"], b"DENY")
            self.assertEqual(result[b"referrer-policy"], b"strict-origin-when-cross-origin")
            if path.startswith("/api/v1/images"):
                self.assertEqual(result[b"cache-control"], b"no-store")
                self.assertEqual(result[b"access-control-allow-origin"], b"https://studio.example")

    def test_forwarded_ips_are_used_only_from_trusted_peers(self):
        clients = []
        async def capture(scope, receive, send):
            clients.append(scope["client"][0])
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})
        app = ProxyHeadersMiddleware(capture, trusted_hosts="10.0.0.2")
        request(app, "/", headers=((b"x-forwarded-for", b"198.51.100.1"),))
        request(app, "/", headers=((b"x-forwarded-for", b"198.51.100.2"),))
        request(app, "/", headers=((b"x-forwarded-for", b"spoofed"),), client="203.0.113.2")
        self.assertEqual(clients, ["198.51.100.1", "198.51.100.2", "203.0.113.2"])

    def test_limiter_does_not_evict_live_buckets_when_full(self):
        limiter = UploadRateLimit(1, max_clients=2)
        with patch("app.rate_limit.monotonic", return_value=0):
            self.assertTrue(limiter.allow("a"))
            self.assertTrue(limiter.allow("b"))
            self.assertFalse(limiter.allow("c"))
            self.assertFalse(limiter.allow("a"))
        with patch("app.rate_limit.monotonic", return_value=60):
            self.assertTrue(limiter.allow("c"))
            self.assertTrue(limiter.allow("a"))

    def test_database_readiness_checks_catalogue_and_redacts_errors(self):
        with patch("app.db.readiness.get_presets") as presets:
            validate_database(MagicMock(), 1)
            presets.assert_called_once()
            for error in (OperationalError("password host"), ValueError("missing preset")):
                presets.side_effect = error
                with self.assertRaisesRegex(RuntimeError, "app.db.migrate") as caught:
                    validate_database(MagicMock(), 1)
                self.assertNotIn("password", str(caught.exception))

    def test_bounded_renderer_matches_previous_pixels_and_filter_order(self):
        rng = np.random.default_rng(42)
        for size in ((97, 151), (1, 73), (75, 1), (2001, 97), (8001, 3)):
            pixels = rng.integers(0, 256, (*size, 3), dtype=np.uint8)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory, "source.png")
                Image.fromarray(pixels).save(path)
                settings = Settings(_env_file=None, database_url="postgresql://test:secret@db.invalid/db?sslmode=require")
                for warmth in (-31, 0, 27):
                    values = Adjustments(brightness=112, contrast=87, saturation=124,
                                         warmth=warmth, sharpness=28, vignette=73)
                    image = ImageEnhance.Brightness(Image.fromarray(pixels)).enhance(1.12)
                    image = ImageEnhance.Contrast(image).enhance(.87)
                    image = ImageEnhance.Color(image).enhance(1.24)
                    if warmth:
                        data = np.asarray(image, dtype=np.float32).copy()
                        data[:, :, 0] += warmth * .4
                        data[:, :, 2] -= warmth * .4
                        image = Image.fromarray(np.clip(data, 0, 255).astype(np.uint8))
                    image = image.filter(ImageFilter.UnsharpMask(radius=max(.5, max(image.size) / 1600), percent=56, threshold=3))
                    width, height = image.size
                    y, x = np.ogrid[-1:1:complex(height), -1:1:complex(width)]
                    mask = 1 - .73 * np.clip((x*x + y*y) / 2, 0, 1) * .7
                    image = Image.fromarray(np.clip(np.asarray(image, dtype=np.float32) * mask[:, :, None], 0, 255).astype(np.uint8))
                    expected = BytesIO()
                    image.save(expected, "JPEG", quality=settings.jpeg_quality)
                    self.assertEqual(render(path, values, settings, preview=False), expected.getvalue())
