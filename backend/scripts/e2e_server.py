"""Isolated browser-test server. Never imported by a production entry point."""

from contextlib import asynccontextmanager
import os
import tempfile
from unittest.mock import patch
from datetime import datetime, timezone

from starlette.responses import Response
from starlette.routing import Route

# Set before importing the app: tests never need real Neon credentials.
os.environ["DATABASE_URL"] = "postgresql://test:test@db.invalid/test?sslmode=require"

from app.main import app, application
from app.db.seed import PRESETS
from app.schemas.presets import Preset
from app.storage.images import ImageStore
from app.rate_limit import UploadRateLimit


@asynccontextmanager
async def test_lifespan(app):
    with tempfile.TemporaryDirectory(prefix="lumalab-e2e-") as directory:
        from pathlib import Path
        app.state.image_store = ImageStore(Path(directory), app.state.settings)
        app.state.db_pool = None
        app.state.storage_dir = None
        # All browser engines share one loopback address. Production's 12/min
        # bucket would throttle the suite itself; backend unit tests cover it.
        app.state.upload_rate_limit = UploadRateLimit(1000)
        catalogue = [Preset.model_validate(dict(zip(Preset.model_fields, row, strict=True))) for row in PRESETS]
        with (patch("app.routes.presets.get_presets", return_value=catalogue),
              patch("app.routes.presets.get_preset", side_effect=lambda pool, timeout, preset_id: next((item for item in catalogue if item.preset_id == preset_id), None)),
              patch("app.routes.health.database_available", return_value=True),
              patch("app.routes.health.storage_available", return_value=True)):
            yield


def main():
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    def reset(request):
        store = app.state.image_store
        with store.lock:
            for session in store.sessions.values():
                session.expires_at = datetime.now(timezone.utc)
            store.purge_expired()
        app.state.upload_rate_limit = UploadRateLimit(1000)
        return Response(status_code=204)

    # This route exists only in this loopback-only test process, ahead of the
    # production SPA mount. It never appears in app.main or app.deploy.
    app.router.routes.insert(0, Route("/__test/reset", reset, methods=["POST"]))
    app.router.lifespan_context = test_lifespan
    uvicorn.run(application, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
