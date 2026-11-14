# PostgreSQL migrations

From `backend/`, run `uv run --locked python -m app.db.migrate`.
Set `DATABASE_DIRECT_URL` to the direct schema-owner URL for the intended branch
and database. The command never falls back to the pooled application URL and
does not run during API startup.

Add files as `NNN_description.sql`, in increasing three-digit version order.
`001_migration_history.sql` creates the migration ledger; `002_presets.sql`
creates the constrained presets table and grants the application role SELECT.
Applied filenames and SHA-256 checksums are recorded in
`public.schema_migrations`. Line endings are normalized before hashing.
Never edit, rename or remove an applied file; add a new migration instead.

Each run holds a transaction-scoped advisory lock and applies all pending files
in one transaction. A failed statement rolls back that run, including its
history entries. A concurrent run fails immediately. Repeating a successful run
skips recorded files; changed, missing or out-of-order history is rejected.

Use ordinary transactional SQL. Do not include `BEGIN`, `COMMIT`, `ROLLBACK`,
`VACUUM`, `CREATE DATABASE` or other commands requiring separate transaction
control. Statements use `DATABASE_TIMEOUT_SECONDS`; long-running migrations
need a deliberate timeout adjustment in their execution environment.
