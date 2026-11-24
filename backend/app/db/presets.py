"""Read the full curated preset catalogue from Neon in display order."""

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolClosed

from app.db.pool import database_connection
from app.schemas.presets import Preset

PRESET_COUNT = 35
PRESET_SELECT = """
    SELECT preset_id, preset_name, description, brightness, contrast,
           saturation, warmth, sharpness, vignette, category, popular,
           display_order
    FROM public.presets
"""


def get_presets(pool: ConnectionPool | None, timeout_seconds: int) -> list[Preset]:
    if pool is None:
        raise PoolClosed("The database pool is unavailable.")
    with database_connection(pool, timeout_seconds) as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                PRESET_SELECT + " ORDER BY display_order, preset_id"
            )
            presets = [Preset.model_validate(row) for row in cursor.fetchall()]
    if len(presets) != PRESET_COUNT or [preset.display_order for preset in presets] != list(range(1, PRESET_COUNT + 1)):
        raise ValueError("The built-in preset catalogue is incomplete or out of order.")
    return presets


def get_preset(pool: ConnectionPool | None, timeout_seconds: int, preset_id: str) -> Preset | None:
    if pool is None:
        raise PoolClosed("The database pool is unavailable.")
    with database_connection(pool, timeout_seconds) as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(PRESET_SELECT + " WHERE preset_id = %s", (preset_id,))
            row = cursor.fetchone()
    return Preset.model_validate(row) if row is not None else None
