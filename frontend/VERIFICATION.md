# Frontend verification

## Backend B04 verification — 13 November 2026

- Added the direct development migration-owner URL to ignored `backend/.env`, preserving the pooled application URL. Updated `.env.example` to use a distinct migration-owner placeholder. No application code, dependencies or frontend files changed.
- Parsed both URLs without displaying their credentials and confirmed they target database `lumalab` on the same development endpoint: the application host has `-pooler`, the migration host does not. Both require SSL.
- Read-only live Psycopg checks confirmed active TLS for both connections. The direct connection authenticated as `lumalab_owner`, which owns the database and has public-schema CREATE permission. The application pool still authenticated as `lumalab_app`, without that permission. Connections closed after verification; no schema or data changes were performed.
- All 27 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`, including the updated example and existing URL/SSL validation. Migration execution is not implemented or claimed here; B05 adds the versioned migration command.

## Backend B03 verification — 13 November 2026

- Explicitly configured Psycopg connection lifetime to 1,800 seconds and idle shrink to 60 seconds. Preserved zero initial connections, the configurable maximum (default four), a wait queue bounded to twice that maximum, and the existing connection/acquisition timeout.
- Extracted `database_connection` in `app/db/pool.py` to apply a transaction-local statement timeout before yielding a connection. Readiness uses this scope; successful scopes commit and exceptional scopes roll back through Psycopg before releasing the connection. No session-level settings or new dependencies were added.
- All 27 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Added coverage for query exceptions reaching the pool context and connection release when timeout setup fails; lifecycle checks cover the explicit retirement settings. Tests ran outside the Windows sandbox for asynchronous support.
- A separate read-only live check used the development application role over TLS and a temporary one-connection pool limit. `SHOW statement_timeout` returned `1s` within the shared scope; `SELECT pg_sleep(3)` raised `QueryCanceled` before three seconds. The connection returned to IDLE, was reused successfully, and its previous statement timeout was restored. A second acquisition while the only connection was held raised `PoolTimeout` at approximately one second. A subsequent database readiness probe succeeded and the pool closed.
- The live check did not modify persistent data or local environment settings. Lifetime/idle values were checked on the constructed pool; the smoke check did not wait through their retirement intervals. These limits do not impose an overall request deadline. Frontend integration and B04 onward remain pending.

## Backend B02 verification — 13 November 2026

- Configured the ignored local `backend/.env` with the development branch's pooled `DATABASE_URL`, using `lumalab_app` and `sslmode=require`. Reused existing environment loading, environment-over-dotenv precedence, secret masking and SSL validation; no application code or dependencies changed.
- A live local Psycopg connection through the actual application pool confirmed `PGconn.ssl_in_use` is true, the pooled hostname, database `lumalab`, and role `lumalab_app`. A read-only identity query and `SELECT 1` succeeded.
- With the actual application lifespan active, an ASGI request to `/api/v1/health` returned 200, `{"status":"ready"}`, and `Cache-Control: no-store`, exercising live Neon and temporary-storage probes. Shutdown closed the pool and removed the owned run directory. This check did not exercise a browser or frontend integration.
- `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q` passed all 25 tests on Windows/Python 3.11.9, outside the sandbox for Windows asynchronous-test support.
- `git check-ignore backend/.env` confirmed the credential file is ignored. A scan of all tracked and nonignored untracked files found neither the connection URL nor its password. No credentials were printed. B03 and subsequent database steps remain pending.

## Backend B01 verification — 13 November 2026

- Created a separate `LumaLab` project (`shy-field-11180671`) in AWS Singapore, PostgreSQL 18, on the existing Free organization. Configured 0.25 CU computes with plan-default suspension. The existing `Durga Ma` project was not changed.
- Confirmed `main` (`br-sweet-salad-b38p818v`) and its `development` child (`br-small-frost-b3yx6xrk`) both reached `ready`. Confirmed development database `lumalab` is owned by `lumalab_owner`; its endpoint is `ep-holy-star-b31tsy2i`.
- Created `lumalab_app` only on the development branch using SQL and a server-generated random password. Granted CONNECT and public-schema USAGE. Removed PUBLIC CREATE/TEMPORARY database rights and public-schema CREATE rights in this fresh development database.
- A live Neon query using `role_name=lumalab_app` returned `current_database=lumalab`, `current_user=lumalab_app`, and `SELECT 1=1`. Catalog checks confirmed CONNECT/USAGE are true; superuser, database/role creation, replication, RLS bypass, inherited roles, neon_superuser membership, database CREATE/TEMPORARY and schema CREATE are false.
- This was a Neon-tool connection, not a local Psycopg connection. The server-side `pg_stat_ssl.ssl` value for the tool session was false; it does not establish client transport security. Local backend connection and client SSL verification are still pending B02. No `.env` was created and no credential was printed or placed in tracked files.
- No application code, dependencies or frontend files changed. Runtime tests were not rerun for infrastructure-only provisioning; `git diff --check` passed. Migrations, presets and application SELECT grants remain pending their scheduled steps.

## Backend A08 verification — 12 November 2026

- Added a restricted JSON formatter and shared logging configuration for the application, Uvicorn and Psycopg. Application events cover lifecycle and resource/readiness failures; request access logs are disabled. The module entry point supports `--reload` with the same configuration, and configuration rejection exits without a traceback.
- `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -v` passed all 25 tests on Windows/Python 3.11.9, outside the sandbox due to the previously observed asynchronous-test stalls.
- Six additional tests cover exclusion of synthetic bearer tokens, database credentials, paths and image metadata from messages/arguments/exceptions/stacks/extra fields; fixed third-party categories; disabled access logs; repeated setup without duplicate output; reload launch arguments; lifecycle success/failure events; and readiness failure categories. Existing configuration tests also verify traceback-free rejection.
- Subprocesses exercised logging and lifecycle behavior with simulated resources. The reload launch test intercepted `uvicorn.run` to inspect configuration; it did not launch a live reload supervisor. No live Neon connection or external hosting logs were tested.
- `git diff --check` and offline lockfile consistency checks passed. Temporary test directories were removed. No dependencies or frontend source changed; frontend tests were not rerun.
- Phase A code is locally verified, but successful live database readiness and the project's completion gates remain pending Neon setup and subsequent phases.

## Backend A07 verification — 12 November 2026

- Implemented `/api/v1/health` using the existing pool and current run directory. The storage probe writes, reads and deletes a small file; the database probe sets a transaction-local statement timeout and executes `SELECT 1` through a connection context manager.
- `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -v` passed all 19 tests on Windows/Python 3.11.9. The suite ran outside the sandbox because asynchronous tests previously stalled inside it.
- Seven new tests exercise ASGI responses and OpenAPI schemas, 200/503 statuses, `Cache-Control: no-store`, pool errors/exhaustion, query errors/timeouts, missing resources, storage permission/disk/read/delete failures, recovery, error redaction, and successful probe cleanup. Database interactions were mocked; successful storage probes used real temporary files.
- No Neon credentials are configured and no live database was contacted. Real connection success, server-side timeout behavior, and remote-database recovery still require verification when Neon is configured. This step does not claim a hard end-to-end deadline for network or filesystem stalls.
- `git diff --check` and offline lockfile consistency checks passed. Temporary test directories were removed. No dependencies or frontend source changed; frontend tests were not rerun.

## Backend A06 verification — 12 November 2026

- Added FastAPI lifespan ownership, a synchronous Psycopg pool with zero initial connections and bounded size/waiting/acquisition/connect timeouts, and one temporary child directory per run. No dependency changes.
- `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -v` passed all 12 tests on Windows/Python 3.11.9. Six new lifecycle tests cover initialization/shutdown/restart, application errors, cancellation, pool startup failure, pool close failure, unwritable storage, preservation of unrelated files, and rejection of substituted cleanup paths.
- Tests used real temporary directories and a real lazy pool for normal lifecycle cases; failure cases used mocks. No database connections were made. Validated resource references are cleared and the pool closes after shutdown. The POSIX permission assertion is conditional and was not exercised on Windows.
- The asynchronous suite stalled in the restricted sandbox and was stopped; it passed outside the sandbox. Removed the empty test directory left by the interrupted run. The verification environment contains no retained test image files.
- `git diff --check` and offline lockfile consistency checks passed. Frontend source and dependencies were unchanged; frontend tests were not rerun.
- Live Neon connectivity, readiness, Windows deployment ACL configuration, query execution, expiry scheduling, and cleanup after abrupt termination remain unverified or deferred to their scheduled checklist items.

## Backend A05 verification — 12 November 2026

- Added validated settings in `backend/app/config.py`, startup loading in `main.py`, and a secret-free `.env.example`. No dependencies were added or upgraded.
- `python -m unittest discover -s tests -v` passed all six test groups on Windows/Python 3.11.9. Coverage includes defaults, URL and SSL validation (including a repeated SSL parameter), secret masking, numeric/related bounds, storage-path traversal rejection, origins/JSON parsing, `.env` precedence, unknown keys, and example-file parsing.
- Subprocess checks verified application import/OpenAPI generation with valid settings, startup rejection of missing or insecure database configuration, and absence of the synthetic password in stdout/stderr. Tests isolate application environment variables and ignore any real `.env`.
- The initial subprocess test lacked Windows system environment variables and failed to load Psycopg's native library. Preserving those OS variables while isolating application settings fixed the test; the full suite then passed.
- `git diff --check` and the lockfile consistency check passed. Confirmed `.env` and runtime files remain ignored while `.env.example` is available to version control.
- Validation performs no database connection or directory creation. Neon availability, directory permissions, cleanup, resource initialization, CORS enforcement, and image operations are still pending. Frontend code was unchanged and frontend tests were not rerun.

## Backend A04 verification — 12 November 2026

- Reused the existing `pyproject.toml`, `uv.lock`, and `.python-version`; no application code, dependency versions, or dependency configuration changed.
- `uv lock --check --offline --cache-dir .uv-cache` passed from `backend/` using Python 3.11.9 and uv 0.10.10 on Windows.
- Set `UV_PROJECT_ENVIRONMENT` only for the verification command to a new unique directory beneath `backend/.uv-cache/`, then ran `uv sync --locked --offline --cache-dir .uv-cache`. All 24 packages installed successfully from the existing cache. This verifies a fresh environment, not an empty download cache.
- `uv pip check` against the fresh environment passed. Compared the complete installed package name/version inventory with the existing `.venv`; they matched. All runtime libraries imported and the application generated its expected OpenAPI schema.
- SHA-256 hashes of `pyproject.toml` and `uv.lock` were unchanged after verification. Restored the prior environment variable and removed only the temporary verification environment after checking its resolved path.
- Documented the CPython 3.11 development baseline and the distinction between the declared Python minimum and tested platforms. `git diff --check` passed. Other Python versions, other operating systems, and frontend integration were not tested in A04.

## Backend A03 verification — 12 November 2026

- Resolved stable packages from PyPI using uv 0.10.10 on Windows/Python 3.11.9. Direct versions: FastAPI 0.162.4, Uvicorn 0.54.0, Pydantic 2.14.3, pydantic-settings 2.16.2, python-multipart 0.0.33, Pillow 13.0.0, opencv-python-headless 5.0.0.93, NumPy 2.4.6, and psycopg[binary,pool] 3.3.9. The pool extra resolved psycopg-pool 3.3.3.
- `uv sync --locked --offline --cache-dir .uv-cache` passed from `backend/` after installation. `uv pip check --python .venv/Scripts/python.exe --cache-dir .uv-cache` reported all 24 installed packages compatible. Prereleases are disabled in project configuration.
- A disposable in-memory smoke check passed: imports, application OpenAPI generation, FastAPI multipart upload registration, Pydantic model/settings construction, JPEG/PNG/WebP encode/decode, Pillow WebP/JPEG/LittleCMS support, NumPy/OpenCV colour conversion, and Psycopg binary client/pool loading. No test endpoints or files were added to the application.
- `git diff --check` passed. No application logic or frontend source changed in A03; frontend tests were not rerun. Neon connectivity and the image-processing workflow remain unimplemented and unverified. Cross-platform installation has not been tested.

## Backend A02 verification — 12 November 2026

- Added module boundaries for routes, schemas, image services, temporary storage, database access, and configuration; registered the shared `/api/v1` router.
- On the existing Python 3.11.9 environment, all new modules imported successfully and the router prefix and empty OpenAPI endpoint map were verified.
- An in-process ASGI smoke check passed: OpenAPI and Swagger UI returned 200; `/` and the still-unimplemented `/api/v1/health` returned 404. This response check stalled inside the sandbox and was stopped; it passed outside the sandbox.
- `git diff --check` passed. Dependency files and frontend code were unchanged by A02. No frontend tests were rerun for this structural backend step.
- This verifies module structure and router registration only; schemas, image services, storage, database access, and settings implementations remain scheduled for later checklist items.

## Backend A01 verification — 12 November 2026

- Windows with Python 3.11.9 and uv 0.10.10.
- Resolved dependencies from PyPI and installed successfully with `uv sync --locked --cache-dir .uv-cache` from `backend/`. FastAPI 0.162.4, Uvicorn 0.54.0, and all transitive packages are recorded in `backend/uv.lock`.
- Launched the documented module entry point through `uv run --locked --offline --cache-dir .uv-cache python` and a standard-library subprocess/HTTP smoke check. `/api/openapi.json` returned 200 with the expected application title and empty endpoint map; `/api/docs` returned 200 referencing the schema; `/` returned 404. The smoke-check server was stopped afterward.
- The restricted sandbox startup check timed out; the same HTTP smoke check passed outside the sandbox. Package downloads also required network access outside the sandbox.
- Confirmed Git ignores the backend virtual environment, uv cache, `.env`, and `.runtime` image directory. `git diff --check` passed.
- Scope: application startup only. Database readiness, configuration validation, business endpoints, image processing, and frontend integration are not implemented or verified. Existing frontend source was not changed by A01, so frontend tests were not rerun for this step.

## Previous frontend verification

Verified on 11 November 2026, Windows, using Node.js 24.9.0 and Google Chrome 157.0.8103.39 through Playwright. This report covers the frontend preview only.

## Passed checks

- `npm run build`: strict TypeScript checks and production Vite build pass.
- `npm test`: 5 unit tests pass (detected formats, mismatched extensions, precise byte limit, APNG/WebP animation rejection and complete preset values).
- `npm run test:e2e`: all 6 browser test groups pass.
- Both `/` and `/studio` render without page-level horizontal overflow at all 12 viewports listed below.
- Home-to-studio navigation and direct studio refresh work. Refresh returns to the empty state as intended.
- JPEG, transparent PNG and WebP uploads render; corrupt replacement preserves the current photograph and settings.
- Presets replace complete settings, Monochrome sets saturation to zero, manual keyboard changes mark the look Custom, reset restores defaults, and comparison leaves adjustments intact.
- Export dialog discloses the unavailable service; Escape dismisses it and restores focus to the triggering control.
- Phone menu opens and closes with Escape; focus returns to its trigger. Phone panel switching exposes presets and adjustment controls.
- Axe WCAG 2 A/AA and WCAG 2.1 AA automated checks return no violations for the home page and populated studio at 1440px and 360px widths.
- No uncaught browser page errors during the viewport checks.
- Desktop and phone screenshots were inspected. Two observed decorative overflow issues were corrected at their source: the card-group glow and the hero ring ornament.

## Viewports

320×568, 360×800, 390×844, 430×932, 768×1024, 820×1180, 1024×768, 1280×800, 1440×900, 1920×1080, 2560×1440, and 844×390.

## Screenshots

- `screenshots/home-desktop.png`
- `screenshots/home-mobile.png`
- `screenshots/studio-empty.png`
- `screenshots/studio-desktop.png`
- `screenshots/studio-mobile.png`

## Boundaries of this verification

The supplied design screenshot was absent; the implementation follows the written design document. Tests used Chromium-based Chrome, not physical phones or every browser. Safari, Firefox, Edge, assistive-technology sessions, exhaustive zoom/text-enlargement cases, continuous width sweeps, EXIF/profile fixtures, and production performance budgets have not been independently verified. Automated axe checks do not replace a complete accessibility audit.

CSS includes reduced-motion handling and responsive reflow, but this report does not claim full manual accessibility certification. No LCP, CLS, INP or processing-throughput targets are claimed.

Backend-specific acceptance tests are intentionally deferred: API errors/tokens/expiry, authoritative animation and multi-frame checks, OpenCV enhancement, Pillow preview/export agreement, sRGB conversion, metadata removal and full-resolution exports. The current CSS/SVG preview is an approximation for demonstrating the interface, not a substitute for those server guarantees.
