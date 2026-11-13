"""Application-owned synchronous pool for database work in threadpool handlers."""

from contextlib import contextmanager
from collections.abc import Iterator
import logging

from psycopg import Connection, Error
from psycopg_pool import ConnectionPool

from app.config import Settings

logger = logging.getLogger("lumalab")


@contextmanager
def database_pool(settings: Settings) -> Iterator[ConnectionPool]:
    pool = ConnectionPool(
        settings.database_url.get_secret_value(),
        name="lumalab",
        open=False,
        min_size=0,
        max_size=settings.database_pool_max_size,
        max_waiting=settings.database_pool_max_size * 2,
        timeout=settings.database_timeout_seconds,
        max_lifetime=1_800,
        max_idle=60,
        kwargs={"connect_timeout": settings.database_timeout_seconds},
    )
    try:
        try:
            pool.open()
        except Exception:
            logger.error("database_pool_start_failed")
            raise RuntimeError("Unable to initialize the database pool.") from None
        yield pool
    finally:
        try:
            pool.close()
        except Exception:
            logger.error("database_pool_close_failed")
            raise RuntimeError("Unable to close the database pool.") from None


@contextmanager
def database_connection(pool: ConnectionPool, timeout_seconds: int) -> Iterator[Connection]:
    """Borrow for one transaction; commit or roll back before returning to the pool."""
    with pool.connection(timeout=timeout_seconds) as connection:
        # Transaction-local settings work with Neon's transaction-mode pooler.
        connection.execute(
            "SELECT set_config('statement_timeout', %s, true)",
            (f"{timeout_seconds}s",),
        )
        yield connection


def database_available(pool: ConnectionPool | None, timeout_seconds: int) -> bool:
    if pool is None:
        return False
    try:
        with database_connection(pool, timeout_seconds) as connection:
            return connection.execute("SELECT 1").fetchone() == (1,)
    except Error:
        return False
