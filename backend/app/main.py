import logging

from fastapi import FastAPI

from app.config import load_settings
from app.lifespan import lifespan
from app.logging import configure_logging
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
)

app.state.settings = settings
app.include_router(router)
