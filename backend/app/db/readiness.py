"""Validate the application role can read a complete, valid preset catalogue."""

from psycopg import Error

from app.db.presets import get_presets


def validate_database(pool, timeout_seconds: int) -> None:
    try:
        get_presets(pool, timeout_seconds)
    except (Error, ValueError):
        raise RuntimeError(
            "Database is not ready. Check DATABASE_URL and network access; "
            "apply python -m app.db.migrate and python -m app.db.seed with "
            "DATABASE_DIRECT_URL on the same database, then restart."
        ) from None
