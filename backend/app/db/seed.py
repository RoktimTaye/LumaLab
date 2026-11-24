"""Repeatable, explicit seeding of the complete built-in preset catalogue."""

import argparse
import json
from pathlib import Path

from psycopg import Connection, Error, connect
from psycopg.conninfo import conninfo_to_dict

from app.config import Settings, load_settings
from app.logging import configure_logging
from app.schemas.presets import Preset

CATALOG_PATH = Path(__file__).with_name("preset_catalog.json")
CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
PRESETS = tuple(tuple(record[field] for field in Preset.model_fields) for record in CATALOG)

UPSERT = """
    INSERT INTO public.presets (
        preset_id, preset_name, description, brightness, contrast,
        saturation, warmth, sharpness, vignette, category, popular,
        display_order
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (preset_id) DO UPDATE SET
        preset_name = EXCLUDED.preset_name,
        description = EXCLUDED.description,
        brightness = EXCLUDED.brightness,
        contrast = EXCLUDED.contrast,
        saturation = EXCLUDED.saturation,
        warmth = EXCLUDED.warmth,
        sharpness = EXCLUDED.sharpness,
        vignette = EXCLUDED.vignette,
        category = EXCLUDED.category,
        popular = EXCLUDED.popular,
        display_order = EXCLUDED.display_order
"""


def seed_presets(connection: Connection) -> None:
    """Upsert built-ins in the caller's transaction without deleting other rows."""
    # Model fields follow the explicit INSERT column order; validate the full batch first.
    presets = [Preset.model_validate(dict(zip(Preset.model_fields, row, strict=True))) for row in PRESETS]
    with connection.cursor() as cursor:
        cursor.executemany(UPSERT, [tuple(preset.model_dump().values()) for preset in presets])


def run_seed(settings: Settings) -> int:
    if settings.database_direct_url is None:
        raise RuntimeError("DATABASE_DIRECT_URL is required for seeding.")
    url = settings.database_direct_url.get_secret_value()
    hosts = conninfo_to_dict(url)["host"].split(",")
    if any("-pooler" in host.split(".")[0] for host in hosts):
        raise RuntimeError("Seeding requires a direct owner connection.")
    with connect(url, connect_timeout=settings.database_timeout_seconds) as connection:
        connection.execute(
            "SELECT set_config('statement_timeout', %s, true)",
            (f"{settings.database_timeout_seconds}s",),
        )
        seed_presets(connection)
    return len(PRESETS)


def main() -> int:
    argparse.ArgumentParser(description="Upsert the built-in preset catalogue.").parse_args()
    configure_logging()
    try:
        count = run_seed(load_settings())
    except (Error, OSError, RuntimeError, ValueError):
        print("Seeding failed; check configuration, migrations and database availability.")
        return 1
    print(f"Seeded {count} preset(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
