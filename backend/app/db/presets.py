"""Read the five built-in definitions from Neon in studio display order."""

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolClosed

from app.db.pool import database_connection
from app.schemas.presets import Preset

PRESET_IDS = ("original", "cinematic", "golden-hour", "monochrome", "vivid")


def get_presets(pool: ConnectionPool | None, timeout_seconds: int) -> list[Preset]:
    if pool is None:
        raise PoolClosed("The database pool is unavailable.")
    with database_connection(pool, timeout_seconds) as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT preset_id, preset_name, description, brightness, contrast,
                       saturation, warmth, sharpness, vignette
                FROM public.presets
                WHERE preset_id = ANY(%s)
                ORDER BY array_position(%s::text[], preset_id)
                """,
                (list(PRESET_IDS), list(PRESET_IDS)),
            )
            presets = [Preset.model_validate(row) for row in cursor.fetchall()]
    if tuple(preset.preset_id for preset in presets) != PRESET_IDS:
        raise ValueError("The built-in preset definitions are incomplete.")
    return presets
