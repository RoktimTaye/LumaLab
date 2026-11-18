import logging
from pathlib import Path

from fastapi import FastAPI

from app.config import load_settings
from app.errors import EXCEPTION_HANDLERS
from app.lifespan import lifespan
from app.logging import configure_logging
from app.middleware import PrivateImageCache, SecurityHeaders, with_cors
from app.static import FrontendStaticFiles
from app.rate_limit import UploadRateLimit
from app.routes import router

configure_logging()
try:
    settings = load_settings()
except RuntimeError:
    logging.getLogger("lumalab").error("configuration_invalid")
    raise SystemExit(1) from None

app = FastAPI(
    lifespan=lifespan,
    title="LumaLab API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    exception_handlers=EXCEPTION_HANDLERS,
)

app.state.settings = settings
app.state.upload_rate_limit = UploadRateLimit(settings.uploads_per_minute)
app.include_router(router)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (frontend_dist / "index.html").is_file():
    app.mount("/", FrontendStaticFiles(directory=frontend_dist, html=True), name="frontend")

# Server entry point; keep the FastAPI instance available for schema tooling.
application = SecurityHeaders(
    with_cors(app, settings.allowed_origins) if settings.allowed_origins else PrivateImageCache(app)
)
