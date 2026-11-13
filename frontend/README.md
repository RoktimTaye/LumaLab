# LumaLab frontend

A responsive photography website and editing studio built from the LumaLab product PRD and the supplied infrastructure design document. The frontend preview is implemented; the backend has application/configuration foundations, managed resources, a readiness endpoint, and restricted operational logging (A01–A08). Neon infrastructure and the local SSL connection are verified (B01–B02); preset queries, image processing, and frontend API integration are still pending.

## Backend development (A01–A08, B01–B04)

Neon setup: [LumaLab project](https://console.neon.tech/app/projects/shy-field-11180671), AWS Singapore, PostgreSQL 18. Use database `lumalab` on the `development` branch (`br-small-frost-b3yx6xrk`) for development. `lumalab_owner` owns the database; `lumalab_app` is the limited application role on that branch. The ignored local `backend/.env` is configured with its pooled connection URL and `sslmode=require`. A local Psycopg connection confirmed TLS and the application identity on 13 November 2026; migrations and preset-table grants have not been applied.

`DATABASE_URL` uses the `-pooler` endpoint and `lumalab_app` for application traffic. The local `DATABASE_DIRECT_URL` uses the same development endpoint without `-pooler`, database `lumalab`, and `lumalab_owner` for migration commands. Both connections were verified over TLS. The application pool reads only `DATABASE_URL`; the migration command will be added in B05 and must use `DATABASE_DIRECT_URL`. Keep the owner credential in the migration environment and omit it from an application-only deployment. See [Neon connection pooling](https://neon.com/docs/connect/connection-pooling).

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The supported development baseline is CPython 3.11, selected by `backend/.python-version`; verification used Python 3.11.9 and uv 0.10.10 on Windows. `requires-python = ">=3.11"` allows newer Python versions, but they and other operating systems have not been tested.

On first setup, copy `backend/.env.example` to `backend/.env` and replace the `DATABASE_URL` placeholders with your Neon pooled connection URL. Keep an existing `.env` when updating the application. Alternatively, supply settings through the process environment. From the repository root:

```sh
cd backend
uv sync --locked
uv run --locked python -m app
```

The server listens on `http://127.0.0.1:8000`. Open `http://127.0.0.1:8000/api/docs` for Swagger UI or `/api/openapi.json` for the schema. `GET /api/v1/health` checks readiness; `/` returns 404. Preset and image endpoints are still pending.

For development with automatic reload, use `uv run --locked python -m app --reload`. This entry point applies the same restricted logging configuration to Uvicorn and its reload process. Run a single backend worker: the planned temporary image sessions will live in process memory.

`backend/pyproject.toml` pins the direct dependencies and `backend/uv.lock` locks their transitive dependencies. Prereleases are disabled. The runtime stack includes FastAPI, Uvicorn, Pydantic, pydantic-settings, python-multipart, Pillow, NumPy, opencv-python-headless, and Psycopg 3 with binary and pool extras. Headless OpenCV provides server-side image processing without GUI dependencies; Psycopg's binary extra bundles the PostgreSQL client library, and its pool extra supports the planned bounded connections. Run the frontend separately using the commands below; it is not connected to this backend yet.

Keep `pyproject.toml`, `uv.lock`, and `.python-version` in version control. Run `uv lock --check` from `backend/` to check that the lockfile matches the project metadata. `uv sync --locked` creates or synchronizes `.venv` and fails if the lockfile needs updating; it does not silently update dependency versions. See [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/). Use uv for intentional dependency changes and review both the manifest and lockfile changes together.

A fresh environment was successfully recreated from the lockfile using cached packages and matched all 24 installed package versions. A first installation needs network access to download Python if absent and any uncached packages. The virtual environment and download cache are local generated files excluded from Git.

Backend module boundaries:

```text
backend/app/
  __main__.py   Uvicorn entry point
  main.py       FastAPI application and router registration
  lifespan.py   Resource initialization and shutdown cleanup
  logging.py    Restricted operational console logging
  routes/       HTTP handlers; shared /api/v1 router
  schemas/      Pydantic request and response models
  services/     Image validation, rendering, enhancement and export
  storage/      Private temporary files and in-memory sessions
  db/           PostgreSQL connections and preset queries
  config.py     Environment-based settings
```

The shared router, configuration loader, and lifespan hook are wired into the application. `routes/health.py` and `schemas/health.py` define the readiness endpoint. `db/pool.py` owns the database pool and database probe; `storage/runtime.py` owns temporary run directories and the storage probe. Image schemas and services remain pending. Route handlers use schemas and delegate processing/storage/database work to their respective modules. These lower-level modules should not import route handlers or the application entry point.

### Backend configuration

Settings load once at application startup from the process environment and then `backend/.env`; environment variables take precedence. The `.env` location is independent of the working directory. Unknown `.env` keys and invalid values stop startup with a `configuration_invalid` log event and a nonzero exit code. Database URLs are masked in settings representations. Keep real values in the ignored `.env` or hosting secrets, never in frontend `VITE_*` variables.

| Setting | Default / validation |
| --- | --- |
| `DATABASE_URL` | Required PostgreSQL URL containing host, database, user and password; `sslmode=require`, `verify-ca` or `verify-full` |
| `DATABASE_DIRECT_URL` | Optional direct migration URL with the same SSL validation; same branch/database, schema-owner role, hostname without `-pooler`; omit when unused |
| `DATABASE_POOL_MAX_SIZE` | 4; integer from 1 to 20; waiting requests are bounded to twice this value |
| `DATABASE_TIMEOUT_SECONDS` | 5; integer from 1 to 60; pool acquisition, individual connection attempts and each SQL statement through `database_connection` |
| `TEMP_IMAGE_DIR` | `.runtime/images`, relative to `backend/`; repository paths must be inside `backend/.runtime`, or use a dedicated private directory outside the repository |
| `MAX_UPLOAD_BYTES` | 10000000; positive integer |
| `MAX_IMAGE_PIXELS` | 24000000; positive integer |
| `MAX_IMAGE_SIDE` | 10000; positive integer |
| `PREVIEW_MAX_EDGE` | 1600; positive integer no larger than `MAX_IMAGE_SIDE` |
| `IMAGE_TTL_SECONDS` | 3600; positive integer |
| `CLEANUP_INTERVAL_SECONDS` | 300; positive integer at most 300 and no larger than the session TTL |
| `JPEG_QUALITY` | 92; integer from 1 to 100 |
| `ALLOWED_ORIGINS` | JSON array, default `[]`; explicit HTTP(S) origins only, for example `["http://localhost:5173"]` |

Startup validates configuration, creates a unique `lumalab-run-*` child under `TEMP_IMAGE_DIR`, and opens a bounded Psycopg pool. The pool starts with zero connections and connects on demand; successful startup does not prove Neon connectivity. The readiness endpoint uses the synchronous pool from a threadpool handler.

The pool uses a 30-minute connection lifetime and a 60-second idle shrink interval. Expired connections are retired when returned, without interrupting an active query; idle capacity can shrink to zero. Use `db.pool.database_connection(pool, timeout_seconds)` for application queries: it borrows one connection, applies a transaction-local statement timeout, and commits or rolls back before returning it. Readiness already uses this helper; preset queries will use it when implemented. Keep image processing outside the connection scope. These are separate acquisition, connection-attempt and per-statement limits, not a total request deadline or a guarantee against every network stall. See [Psycopg pool behavior](https://www.psycopg.org/psycopg3/docs/api/pool.html).

Graceful shutdown closes the pool and removes only this run's directory, including when startup partially fails or the lifespan is cancelled. The configured parent and unrelated files are preserved. POSIX run directories use owner-only permissions; on Windows, use a directory restricted to the service account by its ACL. Cleanup after abrupt termination and session-expiry cleanup belong to phase D. Image-processing limits, CORS, render concurrency, request rates and disk-budget enforcement are still pending.

### Readiness

`GET /api/v1/health` first writes, reads and deletes a small probe in the current run directory, then borrows a database connection and executes `SELECT 1`. It uses `DATABASE_TIMEOUT_SECONDS` for pool acquisition and a transaction-local PostgreSQL statement timeout. Missing resources, pool exhaustion, database errors and failed storage operations return 503. Blocking resource checks run outside the async event loop.

- **200:** `{"status":"ready"}`
- **503:** `{"error":{"code":"service_unavailable","message":"Database or temporary storage is unavailable."}}`

Both responses use `Cache-Control: no-store` and are documented in OpenAPI. Responses expose no credentials, database hostnames or storage paths. The endpoint can recover on a subsequent request when resources become available. It is a readiness probe: a 503 means the HTTP service responded but a required resource failed its check. It does not validate migrations or seeded presets. An example database URL cannot produce a successful live database check.

Run backend tests from `backend/` with `uv run --locked python -m unittest discover -s tests -v`. They use synthetic credentials, simulated database query results and temporary test directories, do not contact a live database, and do not require a real `.env`. A separate live Neon smoke check on 13 November 2026 confirmed TLS, a successful read-only query, and a 200 readiness response through the application's ASGI interface. Shutdown closed the pool and removed the run directory.

### Operational logs

The module entry point writes one JSON object per line to stderr with `time` (UTC), `level`, and `event`. Application events cover startup/shutdown, configuration failures, resource initialization/cleanup failures, and readiness failures by resource. Successful readiness polling is silent. Examples of failure events are `configuration_invalid`, `database_pool_start_failed`, `storage_cleanup_failed`, and `readiness_database_unavailable`.

The formatter emits only approved application event names. Uvicorn and Psycopg warnings/errors become `server_event` and `database_driver_event`; other messages become `runtime_event`. Raw messages, arguments, exception traces, and extra fields are excluded. Access logs are disabled, so request URLs, headers, tokens, client addresses, image metadata/content, credentials, and private filesystem paths are not included in this configured output. No log files are created. Use `python -m app` (with optional `--reload`) to retain this policy; external hosting/proxy logs need their own configuration.

## Run locally

Use Node.js 22.12+ (Node 24.9.0 and npm 11.19.1 were used for this implementation).

```sh
npm ci
npm run dev
```

Open the URL printed by Vite. The same commands work in Windows PowerShell, macOS and Linux terminals.

```sh
npm run build
npm run preview
npm test
npm run test:e2e
```

The browser tests use installed Google Chrome. To use Playwright Chromium instead, remove `channel: 'chrome'` from `playwright.config.ts` and run `npx playwright install chromium`.

## Stack

- React 19.3.1, TypeScript 7.0.2, Vite 8.3.8
- TanStack Router 1.170.46: home, studio, route errors and not-found handling
- TanStack Query 5.107.1: application provider configured for the future API phase; no artificial server queries are made
- CSS Modules and shared RGBW/mint design tokens
- Locally bundled Space Grotesk and DM Sans; Lucide icons
- Vitest and Playwright with axe accessibility checks

Exact direct dependency versions are saved in `package.json`; transitive dependencies are locked in `package-lock.json`. `npm ci` preserves the verified versions.

## Implemented

- Responsive home with an interactive studio preview, product introduction, editing layers illustration, four feature stories, workflow and footer.
- `/studio` with an empty state, bundled sample, local image selection/drop, loading state, metadata and validation errors.
- Still JPEG, PNG and WebP detection, extension matching, decoding, 10,000,000-byte, 24-megapixel and 10,000-pixel side limits. PNG and WebP animation chunks are rejected. The eventual backend must independently validate every upload, including exhaustive multi-frame/colour-profile handling.
- Six integer adjustment controls and five complete, versioned preset definitions. Manual changes mark the look Custom; switching presets replaces every value.
- Browser-only visual previews, original/edited comparison and reset. Transparent input is shown against white. Failed replacement keeps the current photo and settings. Obsolete local uploads are ignored and object URLs are released.
- Phone panel switching, responsive tablet layout, full desktop sidebars, keyboard controls, focus indicators, skip link, reduced motion and an Escape-dismissable navigation menu.
- Export and Auto Enhance dialogs with explicit service-unavailable messaging. They preserve edits and make no processing claims or fake downloads.

## Intentionally deferred

Auto Enhance analysis, authoritative preview rendering, full-resolution JPEG export, metadata stripping, sRGB conversion, server upload validation, temporary sessions/tokens and all API connections belong to the later FastAPI phase. Current CSS/SVG previews are visual approximations, not the final Pillow rendering pipeline. No photographs are sent over a network in this frontend preview. Uploaded photos and settings are held in memory and disappear on refresh or leaving the studio.

Use the complete adjustment type and seeded presets in `src/lib/editor.ts` when defining the later API contracts. Introduce the typed HTTP client and TanStack Query operations once those actual contracts exist. Avoid claiming browser-only processing after backend integration: update the UI to disclose backend processing and temporary storage at that time.

## Structure

```text
src/
  components/       Shared brand, navigation and photograph preview
  lib/editor.ts     Adjustment types, presets and local upload checks
  pages/            Home and Studio with adjacent CSS Modules
  styles/global.css Shared typography, colours, spacing and controls
  main.tsx          Router, query provider and application entry
public/
  images/           Bundled landscape/sample photography
tests/
  unit/             Upload and preset validation
  e2e/              Layout, workflow, keyboard and accessibility tests
```

## Hosting

Deploy the generated `dist` folder to a static host. Configure an SPA fallback that serves `index.html` for application routes such as `/studio`; Vite development and preview servers already handle this. Asset URLs must retain their normal file responses. No secrets or environment variables are needed for this phase.

## Design and assets

The product PRD governs scope and RGBW identity. The second document supplies the near-black console aesthetic, mint accents, fine borders, restrained radii, layered diagram and alternating landscape-backed feature rows. Its infrastructure-specific tables, API demos, and account content have not been copied into the photography product. The screenshot referenced in that document was not supplied, so this is an interpretation of the written design contract, not a verified pixel match.

Bundled photographs were downloaded from Unsplash's image CDN:

- Alpine: https://images.unsplash.com/photo-1464822759023-fed622ff2c3b
- Forest: https://images.unsplash.com/photo-1441974231531-c6227db76b6e
- Nature: https://images.unsplash.com/photo-1472396961693-142e6e269027

Fonts are installed through Fontsource and retain their packaged license information. Icons are provided by the ISC-licensed Lucide package. No external assets are fetched at runtime.

See `VERIFICATION.md` for actual test coverage and limitations.

The remaining backend and API work, including the Neon PostgreSQL database decision, is tracked in [BACKEND_IMPLEMENTATION_CHECKLIST.md](BACKEND_IMPLEMENTATION_CHECKLIST.md).
