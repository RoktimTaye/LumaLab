"""Apply ordered SQL migrations explicitly, using the direct owner connection."""

import argparse
from hashlib import sha256
from pathlib import Path
import re

from psycopg import Error, connect
from psycopg.conninfo import conninfo_to_dict

from app.config import BACKEND_DIR, Settings, load_settings
from app.logging import configure_logging

MIGRATIONS_DIR = BACKEND_DIR / "migrations"


def read_migrations(directory: Path) -> list[tuple[str, str, str]]:
    migrations = []
    versions = set()
    for path in sorted(directory.glob("*.sql")):
        if not re.fullmatch(r"[0-9]{3}_[a-z0-9_]+\.sql", path.name):
            raise RuntimeError("Invalid migration filename.")
        version = path.name[:3]
        if version in versions:
            raise RuntimeError("Duplicate migration version.")
        versions.add(version)
        # Normalize line endings so Windows and Linux produce the same checksum.
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            raise RuntimeError("Empty migration file.")
        migrations.append((path.name, content, sha256(content.encode("utf-8")).hexdigest()))
    if not migrations or migrations[0][0] != "001_migration_history.sql":
        raise RuntimeError("Migration history definition is missing.")
    return migrations


def run_migrations(settings: Settings, directory: Path = MIGRATIONS_DIR) -> int:
    if settings.database_direct_url is None:
        raise RuntimeError("DATABASE_DIRECT_URL is required for migrations.")
    url = settings.database_direct_url.get_secret_value()
    hosts = conninfo_to_dict(url)["host"].split(",")
    if any("-pooler" in host.split(".")[0] for host in hosts):
        raise RuntimeError("Migrations require a direct connection.")
    migrations = read_migrations(directory)
    with connect(url, connect_timeout=settings.database_timeout_seconds) as connection:
        connection.execute(
            "SELECT set_config('statement_timeout', %s, true)",
            (f"{settings.database_timeout_seconds}s",),
        )
        # Transaction-scoped lock is released on commit, rollback or disconnect.
        if not connection.execute("SELECT pg_try_advisory_xact_lock(1279348033)").fetchone()[0]:
            raise RuntimeError("Another migration run is active.")
        exists = connection.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0]
        applied = connection.execute(
            "SELECT version, checksum FROM public.schema_migrations ORDER BY version"
        ).fetchall() if exists else []
        expected = [(name, checksum) for name, _, checksum in migrations]
        if applied != expected[:len(applied)]:
            raise RuntimeError("Applied migration history differs from local files.")
        for name, content, checksum in migrations[len(applied):]:
            connection.execute(content, prepare=False)
            connection.execute(
                "INSERT INTO public.schema_migrations (version, checksum) VALUES (%s, %s)",
                (name, checksum),
            )
    return len(migrations) - len(applied)


def main() -> int:
    argparse.ArgumentParser(description="Apply pending PostgreSQL migrations.").parse_args()
    configure_logging()
    try:
        count = run_migrations(load_settings())
    except (Error, OSError, RuntimeError, UnicodeError):
        print("Migration failed; check configuration, migration files and database availability.")
        return 1
    print(f"Applied {count} migration(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
