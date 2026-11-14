"""Own resources for exactly one application startup/shutdown cycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI

from app.db.pool import database_pool
from app.storage.runtime import temporary_storage
from app.storage.images import ImageStore

logger = logging.getLogger("lumalab")


async def clean_expired(store: ImageStore, interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        worker = asyncio.create_task(asyncio.to_thread(store.purge_expired))
        try:
            await asyncio.shield(worker)
        except asyncio.CancelledError:
            await worker
            raise
        except Exception:
            logger.error("session_cleanup_failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = app.state.settings
    app.state.db_pool = None
    app.state.storage_dir = None
    app.state.image_store = None
    started = False
    logger.info("startup_started")
    try:
        with temporary_storage(settings.temp_image_dir, settings.image_ttl_seconds) as directory:
            with database_pool(settings) as pool:
                app.state.db_pool = pool
                app.state.storage_dir = directory
                app.state.image_store = ImageStore(directory, settings)
                started = True
                logger.info("startup_complete")
                cleanup = asyncio.create_task(clean_expired(app.state.image_store, settings.cleanup_interval_seconds))
                try:
                    yield
                finally:
                    cleanup.cancel()
                    try:
                        await cleanup
                    except asyncio.CancelledError:
                        pass
                    logger.info("shutdown_started")
    except asyncio.CancelledError:
        logger.warning("lifecycle_cancelled")
        raise
    except Exception:
        logger.error("lifecycle_failed" if started else "startup_failed")
        raise
    else:
        logger.info("shutdown_complete")
    finally:
        app.state.db_pool = None
        app.state.storage_dir = None
        app.state.image_store = None
