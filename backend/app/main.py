import logging

from fastapi import FastAPI

from app.config import load_settings
from app.errors import EXCEPTION_HANDLERS
from app.lifespan import lifespan
from app.logging import configure_logging
from app.middleware import PrivateImageCache, with_cors
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

app.add_middleware(PrivateImageCache)
app.state.settings = settings
app.include_router(router)

# Server entry point; keep the FastAPI instance available for schema tooling.
application = with_cors(app, settings.allowed_origins)
