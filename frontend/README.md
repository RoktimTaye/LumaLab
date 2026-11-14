# LumaLab frontend

A responsive photography website and editing studio built from the LumaLab product PRD and the supplied infrastructure design document. The frontend preview is implemented. The backend now exposes all eight MVP endpoints, including a basic private image editing workflow and live Neon presets. Detailed backend hardening and frontend API integration remain pending.

## Backend development (A01–A08, B01–B11, C01–C12, D01–D13)

Neon setup: [LumaLab project](https://console.neon.tech/app/projects/shy-field-11180671), AWS Singapore, PostgreSQL 18. Use database `lumalab` on the `development` branch (`br-small-frost-b3yx6xrk`) for development. `lumalab_owner` owns the database; `lumalab_app` is the limited application role on that branch. The ignored local `backend/.env` is configured with its pooled connection URL and `sslmode=require`. A local Psycopg connection confirmed TLS and the application identity on 13 November 2026. The migration ledger, constrained presets table, seeded definitions and read-only retrieval endpoint were verified on 14 November. The application role has SELECT permission on presets.

`DATABASE_URL` uses the `-pooler` endpoint and `lumalab_app` for application traffic. The local `DATABASE_DIRECT_URL` uses the same development endpoint without `-pooler`, database `lumalab`, and `lumalab_owner` for migration commands. Both connections were verified over TLS. The application pool reads only `DATABASE_URL`; the migration command requires `DATABASE_DIRECT_URL` and rejects a pooled endpoint. Keep the owner credential in the migration environment and omit it from an application-only deployment. See [Neon connection pooling](https://neon.com/docs/connect/connection-pooling).

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The supported development baseline is CPython 3.11, selected by `backend/.python-version`; verification used Python 3.11.9 and uv 0.10.10 on Windows. `requires-python = ">=3.11"` allows newer Python versions, but they and other operating systems have not been tested.

On first setup, copy `backend/.env.example` to `backend/.env` and replace the `DATABASE_URL` placeholders with your Neon pooled connection URL. Keep an existing `.env` when updating the application. Alternatively, supply settings through the process environment. From the repository root:

```sh
cd backend
uv sync --locked
uv run --locked python -m app
```

The server listens on `http://127.0.0.1:8000`. Open `http://127.0.0.1:8000/api/docs` for Swagger UI or `/api/openapi.json` for the schema. `GET /api/v1/health` checks readiness; `/` returns 404.

OpenAPI describes the Pydantic JSON request/response models, required multipart `file`, image bearer security, implemented image error envelopes and response headers. JPEG responses are binary `image/jpeg`, and deletion's 204 has no body. Upload metadata constrains detected format to JPEG/PNG/WEBP, dimensions to positive oriented pixel counts, and expiry to a timezone-aware timestamp. Image 422 responses use `ErrorResponse`, matching the generic runtime envelope. Frontend contracts are generated and checked against this schema.

Application errors now consistently use `{ "error": { "code": "...", "message": "..." } }`, including request-validation failures, malformed JSON, routing 404/405 and unexpected server errors. Validation returns generic `invalid_request`/422; unexpected errors return generic `internal_error`/500 outside image routes, whose specific processing codes are retained. Responses omit input values, validation traces and raw exception details, use no-store, and preserve applicable Allow/WWW-Authenticate/Retry-After headers.

Frontend API contracts live in `src/lib/api.generated.ts`. From `frontend/`, run `npm run contracts:generate` after an intentional API change, review the generated diff, then run `npm run contracts:check` and `npm run build`. Use the check command in CI: it exits nonzero for missing/stale output and never rewrites it. Keep the generated file in version control. The commands require uv and the backend environment installed with `uv sync --locked`; no running server, database or `.env` is required. Schema export uses synthetic settings and does not enter the application lifespan.

Generated `components` describe models and `paths` describe methods, path parameters, request/response media types, statuses and response headers. File/JPEG bodies map to `Blob`, timestamps to strings, and integers to TypeScript numbers; server validation still enforces strict integers and bounds. A schema fingerprint also catches constraints/security metadata drift. The generator intentionally supports only the current schema constructs and stops for unsupported additions. `src/lib/editor.ts` reuses the generated Adjustments type; full API/Studio wiring remains phase G. No generator dependency is required.

Image endpoint workflow (all paths under `/api/v1`):

Successful edited previews echo the submitted nonnegative integer revision exactly in `X-Image-Revision`; the client can use it to discard stale results. Revisions are request identifiers, not server-maintained edit state. Failed preview requests omit that success header. JPEG exports provide `Content-Type: image/jpeg`, byte-matching `Content-Length`, and `Content-Disposition: attachment; filename="lumalab-<safe-stem>.jpg"`. The stem is ASCII/sanitized, limited to 80 characters and falls back to `image`. Configured CORS exposes both custom response headers; Studio stale-result handling remains phase G.

For separate frontend/backend origins, set `ALLOWED_ORIGINS` to an explicit JSON list such as `["http://localhost:5173","http://127.0.0.1:5173"]` and restart the backend. The default `[]` keeps CORS disabled for same-origin/proxy setups. CORS permits GET/POST/DELETE, Authorization/Content-Type (plus browser-safelisted headers), and exposes X-Image-Revision/Content-Disposition on allowed-origin responses, including errors. Cookie credentials are disabled; bearer tokens remain explicit request headers. Preflights use framework protocol responses (200/400), with unlisted origins/methods/headers rejected. CORS controls browser access and does not replace image-token authorization.

Continue launching with `uv run --locked python -m app` (or `--reload`), which uses `app.main:application` so CORS also covers server errors. `app.main:app` remains the inner FastAPI instance for schema tooling; direct Uvicorn deployments should target `app.main:application`. The private cache guard also covers preflight responses.

Every response under `/api/v1/images` uses `Cache-Control: no-store`, including upload metadata, JPEG bytes, enhancement JSON, empty deletion responses, errors and trailing-slash redirects. A small ASGI header guard enforces this at the HTTP boundary and overrides any cacheable header on private paths. It does not change public documentation/static response caching. Browser object URLs still use the explicit disposal contract described below.

Verified HTTP outcomes:

| Status | Meaning |
| --- | --- |
| 201 | Upload created a session and returned metadata/token. |
| 204 | Authorized deletion succeeded; no response body. |
| 401 | Image bearer authorization is missing or invalid. |
| 404 | Image is unknown, deleted, purged or unavailable after restart. |
| 410 | A valid token identifies a known expired session. |
| 413 | Upload bytes or decoded dimensions exceed limits. |
| 415 | Unsupported, animated or extension/content-mismatched image. |
| 422 | Image decoding or request-field/JSON validation failed. |
| 429 | Processing is busy or session capacity is full. |
| 500 | Unexpected operation failure; response details are generic. |
| 503 | Required database or image-storage resource is unavailable. |

The API also returns generic 400 for malformed multipart and 405 for disallowed methods. A purged expired session returns 404 because its metadata is no longer available; 410 applies while its expired record is known. OpenAPI declares expected image statuses and 500/503 service failures across all eight operations.

Preview/export endpoints return JPEG bytes directly, with no base64/JSON wrapper or redirect to private storage. `src/lib/imageResponse.ts` provides browser consumption helpers for an already-authorized fetch `Response`: `imageResponseUrl(response)` returns `{url, revoke}` for display, and `downloadImageResponse(response, filename)` initiates a blob-backed download. The display caller must invoke `revoke()` on replacement/unmount; download cleanup removes its anchor and releases the URL after initiation (or immediately on failure). Error/non-JPEG responses are rejected before allocating a URL. Studio wiring to these helpers remains phase G; the current local preview continues its existing object-URL cleanup.

Upload using browser `FormData` with a file part named `file`; let the browser set the multipart Content-Type and boundary. Preview/export settings use `Content-Type: application/json` and a JSON body; a charset parameter is supported. JSON/raw-image uploads and form/text preview/export bodies are rejected before processing. Missing/wrong fields or JSON content types return generic 422; a missing multipart boundary returns generic 400.

The server independently accepts still `.jpg`/`.jpeg`, `.png` and `.webp` files (case-insensitive). It matches the extension to the detected content, requires one frame, verifies the container and fully decodes the pixels before creating a session. The uploaded part's MIME declaration is not trusted. Unsupported/mismatched formats or multiple frames return 415; decoding failures return 422.

EXIF orientation is applied to working pixels before dimensions are reported, including mirrored orientations. For example, an 80×40 upload with orientation 6 reports 40×80; its previews and exports follow that orientation. Working/derived files omit the orientation tag to prevent another rotation.

Upload normalization also rejects Pillow decompression-bomb warnings/errors with 413. Pillow metadata warnings and binary parsing failures return generic 422 responses; malformed ICC profiles are rejected. Warning handling is scoped to normalization. Pillow's built-in compressed PNG metadata limits remain enabled; see its [image safety guidance](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open) and [PNG metadata limits](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#png).

1. `POST /images` with multipart `file`. A 201 response contains `image_id`, `access_token`, `filename`, detected `format`, oriented `width`/`height`, and `expires_at`.
2. Send `Authorization: Bearer <access_token>` on every request for that image. `GET /images/{image_id}/original-preview` returns a JPEG. `POST /images/{image_id}/preview` accepts `{revision, adjustments}` and returns JPEG bytes with `X-Image-Revision`.
3. `POST /images/{image_id}/enhance` returns `{adjustments, message}` computed from the normalized original. Submit those values to preview to view the suggestion.
4. `POST /images/{image_id}/export` accepts `{adjustments, format: "jpeg", quality: 92}` and returns a full-resolution JPEG attachment. `DELETE /images/{image_id}` returns 204 and removes the session files.

Every adjustment object requires integer `brightness`, `contrast`, `saturation` (0–200), `warmth` (−50–50), `sharpness` and `vignette` (0–100). Bounds are inclusive. Preview/export reject floats (including `100.0`), numeric strings, booleans, nulls, missing fields and extra fields with 422 before rendering; values are never silently coerced or clamped. Image responses use no-store; expected failures use `{error: {code, message}}`. Missing/wrong tokens return 401, unavailable sessions 404, known expired sessions 410, oversized input 413, unsupported formats 415, invalid input 422, and busy/full capacity 429.

Authorization is image-specific: the token returned by one upload cannot authorize another image, and an image ID is not a token. Send the token only as `Authorization: Bearer <access_token>` for original preview, edited preview, enhancement, export and deletion. Query parameters, cookies and JSON token fields do not grant access; never build token-bearing URLs. Failed authorization uses a generic 401 with `WWW-Authenticate: Bearer` and does not echo the token. Session records retain only token hashes; uploaded image files contain no token. Upload itself, health and presets remain public. After a replacement upload succeeds, the client can DELETE the old session without affecting the new one; it can also DELETE the current session on explicit closure. Browser-close cleanup is best effort, with server expiry as the fallback.

IDs and tokens are generated independently with Python's `secrets` module from 16 and 32 random bytes respectively. Storage directories use generated IDs and fixed internal filenames; submitted filenames never choose disk paths. Repeated filenames create separate sessions.

Uploads enforce configurable defaults of 10,000,000 file bytes, 24,000,000 decoded pixels and 10,000 pixels per side, accepting exact boundaries. An upload-only receive guard caps the total multipart request at MAX_UPLOAD_BYTES plus 65,536 bytes before passing chunks to the parser. It checks declared Content-Length and actual streamed bytes; missing/understated lengths cannot bypass the cap. The separate file-byte check excludes multipart overhead. Oversized requests/files/dimensions return 413 before image decoding.

Sessions retain exact uploaded bytes as `original` and a separate `normalized.png` in the private per-run directory. Processing reads the normalized file; previews, enhancement and exports do not overwrite either source file. Tokens are stored as hashes. Each session records its UTC upload time and returns a fixed expiry, 60 minutes later by default; reads and edits do not renew it. Each process currently allows 32 sessions and one active image operation, with immediate 429 backpressure. Expiry is enforced on access; a lifespan task purges expired sessions every five minutes by default, and uploads also trigger purging. A shared store lock keeps files available during active processing and coordinates deletion. Startup removes old run directories under the configured private root; shutdown waits for cleanup and removes this run's directory. Hosting request limits, request rates, execution time and aggregate disk-budget hardening remain phase H. The frontend is still using its local editing workflow.

The initial renderer applies brightness, contrast, saturation, warmth, sharpness and vignette in that order from the normalized original. Warmth adds/subtracts `0.4 × warmth` to red/blue (disabled at zero saturation); sharpness uses an unsharp mask with radius `max(0.5, long_edge/1600)` and percent `2 × sharpness`; vignette darkens the normalized squared distance from centre by up to `0.7 × vignette/100`. Preview geometry is limited by `PREVIEW_MAX_EDGE`; exports reuse the full-resolution pipeline. Enhancement uses reduced-image luminance/spread, HSV saturation and red/blue balance. Detailed image-quality and edge-case verification remains in D–F.

`GET /api/v1/presets` publicly returns a JSON array of five objects in this order: `original`, `cinematic`, `golden-hour`, `monochrome`, `vivid`. Each contains `preset_id`, `preset_name`, `description`, `brightness`, `contrast`, `saturation`, `warmth`, `sharpness` and `vignette`. Definitions are read from Neon on each request and validated by Pydantic; unrelated IDs are excluded. Database failures or missing/invalid built-ins return 503 with `{"error":{"code":"service_unavailable","message":"Presets are temporarily unavailable."}}`. Both 200 and 503 use `Cache-Control: no-store`. Only GET is exposed; the endpoint does not require temporary image storage or an image token. The studio still uses local presets until frontend integration.

Run migrations explicitly from `backend/` with `uv run --locked python -m app.db.migrate`. The command applies pending numbered files from `backend/migrations/`, records checksums, and skips files already applied. A failed batch rolls back completely; concurrent runs and changed applied files fail with exit code 1. Migrations do not run at API startup. See `backend/migrations/README.md` for the SQL file convention. Paths in this backend section are relative to the repository root; from this `frontend/` directory, use `../backend`.

After migrations, run `uv run --locked python -m app.db.seed` from `backend/`. It requires the direct owner URL and upserts Original, Cinematic, Golden Hour, Monochrome and Vivid by stable ID. Definitions live in `backend/app/db/seed.py` and match the existing frontend. Repeat runs restore all built-in fields without duplicating IDs or deleting other rows. All five upserts commit together; failure rolls back the batch and returns exit code 1 with a generic message. Seeding runs only when explicitly invoked.

Migration/seeding integration checks were verified on the isolated `development` branch: repeated runs, seed repair, database constraint failure, migration batch rollback, checksum protection and final application-role retrieval. Temporary probes were rolled back and fixture files removed. Main/production was not modified. Use an isolated test database or development branch for these checks; the ordinary unit suite uses simulated database resources. See `frontend/VERIFICATION.md` for the recorded scope.

`backend/app/schemas/presets.py` defines the reusable Pydantic `Preset` model used by seeding and retrieval. All nine fields are required; adjustment values use strict integers and the database's numeric bounds. Floats, numeric strings, booleans, nulls and extra fields are rejected. The seed command validates the entire batch before executing any upserts and reports validation failures through the same generic error path.

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

The shared router, configuration loader, and lifespan hook are wired into the application. `routes/health.py` and `schemas/health.py` define readiness; `routes/presets.py`, `db/presets.py` and `schemas/presets.py` handle preset retrieval. `schemas/errors.py` holds the shared service-unavailable envelope. `db/pool.py` owns the database pool and database probe; `storage/runtime.py` owns temporary run directories and the storage probe. Image responsibilities are separated into `routes/images.py`, `schemas/images.py`, `services/images.py` and `storage/images.py`. Route handlers delegate processing/storage/database work to those modules.

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

The pool uses a 30-minute connection lifetime and a 60-second idle shrink interval. Expired connections are retired when returned, without interrupting an active query; idle capacity can shrink to zero. Use `db.pool.database_connection(pool, timeout_seconds)` for application queries: it borrows one connection, applies a transaction-local statement timeout, and commits or rolls back before returning it. Readiness and preset retrieval use this helper. Keep image processing outside the connection scope. These are separate acquisition, connection-attempt and per-statement limits, not a total request deadline or a guarantee against every network stall. See [Psycopg pool behavior](https://www.psycopg.org/psycopg3/docs/api/pool.html).

Database failures, pool exhaustion and query timeouts produce generic 503 responses from health/presets. A stale idle connection can fail the request that discovers it; Psycopg discards the broken client and prepares a replacement. Connection attempts retry in background workers with exponential backoff, using Psycopg's default five-minute retry window; request acquisition waits remain bounded by `DATABASE_TIMEOUT_SECONDS`. Later requests can recover on the same running application once a connection becomes available. Failed SQL is not automatically replayed. Driver and application failures use fixed log categories that omit connection strings and raw exception details. See [Psycopg connection lifecycle and recovery](https://www.psycopg.org/psycopg3/docs/advanced/pool.html). Development checks verified initial connection failure, stale-client replacement, pool exhaustion and query cancellation; they did not interrupt the Neon service itself.

Graceful shutdown closes the pool and removes only this run's directory, including when startup partially fails or the lifespan is cancelled. The configured parent and unrelated files are preserved. Each new run directory is restricted before image storage opens: POSIX mode 0700, or a Windows service-account-only inheritable ACL applied with bundled whoami/icacls tools. Permission setup failure aborts startup and removes the empty run. This covers the Python 3.11.9 Windows mode-handling gap; see [Python directory permissions](https://docs.python.org/3.11/library/os.html#os.mkdir) and [Windows ACL commands](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls). Private files have no public/static URL; previews and exports are authorized binary responses and are not saved publicly. Scheduled expiry/crash-leftover cleanup remains D11; request rates, execution time and aggregate disk-budget enforcement remain phase H.

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
