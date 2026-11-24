# LumaLab backend developer guide

The FastAPI backend validates photographs, renders edits, suggests enhancements and exports JPEGs. PostgreSQL stores the preset catalogue and migration ledger. Images, session tokens and editor history are not persisted in the database.

For the UI and client integration, see [Frontend_doc](Frontend_doc.md).

## Prerequisites and first setup

- Python 3.11 (the development baseline in `backend/.python-version`). The package declares Python >=3.11.
- uv for the locked Python environment.
- A Neon PostgreSQL development branch with an owner role and a limited `lumalab_app` login role. Obtain credentials from the project maintainer or provision your own development database.
- Node.js >=22.12.0 and npm if building the frontend or checking generated contracts.

From the repository root, in PowerShell:

```powershell
cd backend
uv sync --locked
# First setup only; keep an existing .env when updating.
Copy-Item .env.example .env
```

Edit `backend/.env` with credentials for your development database:

```dotenv
DATABASE_URL=postgresql://lumalab_app:PASSWORD@HOST-pooler.neon.tech/DB_NAME?sslmode=require
DATABASE_DIRECT_URL=postgresql://OWNER:PASSWORD@HOST.neon.tech/DB_NAME?sslmode=require
```

Use the pooled, least-privilege URL for runtime traffic and the direct owner URL for migrations/seeding. Both must target the same branch and database. URLs require a host, database, user, password and TLS (`sslmode=require`, `verify-ca` or `verify-full`). Keep `.env` private and ignored; never copy credentials into frontend variables.

Before applying migrations to a new database, create the `lumalab_app` login role through your database administration tooling, and ensure it can connect to the database and use the `public` schema. Migration `002_presets.sql` creates the table and grants it SELECT; `003_preset_catalog.sql` adds grouping and popularity metadata. The application role must not inherit owner or write privileges. Use a separate development branch for migration experiments.

From `backend/`, prepare the database, then start the API:

```powershell
uv run --locked python -m app.db.migrate
uv run --locked python -m app.db.seed
uv run --locked python -m app --reload
```

The API listens at `http://127.0.0.1:8000`. Startup checks database access, all 35 saved presets and private image storage. A database or catalogue failure prevents normal startup. The owner URL can be removed from the runtime environment after provisioning.

| URL | Purpose |
| --- | --- |
| `/api/docs` | Interactive Swagger documentation |
| `/api/openapi.json` | OpenAPI schema |
| `/api/v1/health` | Database and temporary-storage readiness |
| `/` | Built frontend when `frontend/dist` exists; otherwise 404 |

Start the frontend in another terminal using [Frontend_doc](Frontend_doc.md#local-development). Vite proxies `/api` to port 8000.

## Source layout

| Path | Responsibility |
| --- | --- |
| `backend/app/main.py` | FastAPI app, middleware and route wiring |
| `backend/app/__main__.py` | Local development entry point |
| `backend/app/deploy.py` | Container bootstrap and production server |
| `backend/app/config.py` | Validated environment settings |
| `backend/app/routes/` and `schemas/` | HTTP handlers and Pydantic contracts |
| `backend/app/services/images.py` | Normalization, rendering and enhancement |
| `backend/app/storage/`, `uploads.py`, `rate_limit.py` | Private sessions, bounded uploads and capacity controls |
| `backend/app/db/` | Pool, readiness, migration runner, preset queries and seed command |
| `backend/migrations/` | Numbered transactional SQL migrations |
| `backend/scripts/` | Contract export, isolated browser-test API and image benchmark |
| `backend/tests/` | Backend regression tests |

Runtime dependencies are pinned in `backend/pyproject.toml` and locked in `backend/uv.lock`: FastAPI, Pydantic, Uvicorn, Psycopg, Pillow, NumPy and headless OpenCV. Use `uv sync --locked` to reproduce the environment.

## Architecture and data flow

```mermaid
flowchart LR
  Browser[React Studio] -->|JSON, multipart, bearer token| API[FastAPI /api/v1]
  API --> Renderer[Validation and image processing]
  Renderer --> Temp[Private temporary files]
  API --> Pool[Psycopg pool]
  Pool --> DB[(PostgreSQL presets and migration ledger)]
  API -->|JPEG bytes and JSON| Browser
```

1. Studio loads the complete 35-preset catalogue from PostgreSQL, grouped by saved category and popularity metadata.
2. Upload validation checks still JPEG/PNG/WebP content, filename extension, frame count, dimensions and colour metadata. The service normalizes EXIF orientation and sRGB colour, composites transparency onto white, and keeps the exact original bytes separately.
3. Upload returns a random image ID, a one-time bearer token, dimensions, format and fixed expiry. Session memory retains only the token hash.
4. Preview and export render the complete adjustment state from immutable normalized source files. Reduced private PNGs support preview and analysis. Enhancement returns suggestions rather than modifying the source.
5. Deletion, expiry and graceful shutdown remove private files. Startup removes stale run directories. Restart loses the in-memory sessions; clients must upload again.

There are no accounts, durable photo library or saved editing history. PostgreSQL contains `public.presets` (stable ID, name, description, six bounded adjustments, category, popularity and display order) and `public.schema_migrations` (migration history/checksums). The canonical seed data is `backend/app/db/preset_catalog.json`.

## API contract

All paths below are under `/api/v1`. The live OpenAPI schema is the detailed contract.

| Method | Path | Input and successful response |
| --- | --- | --- |
| GET | `/health` | Resource readiness JSON |
| GET | `/presets` | Validated preset array from PostgreSQL |
| GET | `/presets/{preset_id}` | One saved preset from PostgreSQL for lazy loading |
| POST | `/images` | Multipart `file`; 201 with `image_id`, `access_token`, `filename`, `format`, `width`, `height`, `expires_at` |
| GET | `/images/{image_id}/original-preview` | Normalized original as JPEG |
| POST | `/images/{image_id}/preview` | JSON `{revision, adjustments, crop?, enhancement?, curves?}`; JPEG with matching `X-Image-Revision` |
| POST | `/images/{image_id}/enhance` | JSON response `{adjustments, recipe, assessment, message}`; source-derived `natural-v3` recipe |
| POST | `/images/{image_id}/export` | JSON `{adjustments, crop?, enhancement?, curves?, format: "jpeg", quality: 92}`; full-resolution JPEG attachment |
| DELETE | `/images/{image_id}` | 204, empty body |

Every operation on an existing image requires `Authorization: Bearer <access_token>`. Upload, health and presets are public. Tokens are image-specific; query strings, cookies and JSON fields do not authorize access. Private responses use `Cache-Control: no-store`. JPEG responses are binary bytes, with safe attachment filenames for export.

Every adjustment object contains all six strict integer fields; extra fields, floats, strings and booleans are rejected:

| Field | Inclusive range | Neutral value |
| --- | --- | --- |
| `brightness` | 0–200 | 100 |
| `contrast` | 0–200 | 100 |
| `saturation` | 0–200 | 100 |
| `warmth` | -50–50 | 0 |
| `sharpness` | 0–100 | 0 |
| `vignette` | 0–100 | 0 |

When present, the versioned `enhancement` recipe runs first: float32, linear-light exposure/tone adjustments, conservative white-balance gains, vibrance and smooth gamut compression. Strength blends the complete correction with the original encoded sRGB pixels; zero is exactly neutral. The existing manual render order then follows: brightness, contrast, saturation, warmth, RGB point curves, sharpness and vignette. Original input precision remains that of the normalized RGB source; this is not a high-bit-depth RAW decoder. JPEG output embeds sRGB ICC while omitting source EXIF/GPS. Preview revisions are nonnegative client request identifiers echoed by the server; they do not represent stored edit history.

Optional `curves` contains `rgb`, `red`, `green` and `blue` channel objects, each with `points: [{x: 0, y: 0}, {x: 255, y: 255}]` by default. Each channel accepts 2–16 points, strict integer x/y values from 0–255, strictly increasing inputs and endpoint inputs 0 and 255. Outputs may reverse direction. Shape-preserving cubic interpolation produces bounded 256-entry lookup tables in encoded sRGB; the master RGB table runs first, followed by each individual channel. Omitting curves, null curves and identity curves preserve the existing render. No source files or database preset rows change.

Auto Enhance uses the whole uncropped original preview (up to 768 pixels per edge for tonal analysis), luminance quantiles, regional lighting, hue-specific saturation, plausible neutral-color evidence and resized-image noise/structure indicators. It can correct deficits and excesses: brighten or darken, add or soften midtone contrast, deepen lifted black levels, and reduce excessive individual colors. It limits correction for low/high-key scenes and backs off if the candidate introduces excessive new clipping or blocked blacks. It returns neutral manual `adjustments`; clients must submit the returned `recipe` as `enhancement` on both preview and export to apply the photographic result. No server-side recipe history is stored, and repeated analysis does not compound prior edits. Recipe fields are strict, finite and bounded; `version` accepts `natural-v1` (legacy renderer) and `natural-v2` (previous photographic renderer), and `natural-v3` (current source-scale detail renderer). Legacy requests that omit `enhancement` keep their existing manual behavior.

V2 stores a fixed 8×8 regional exposure field and, when local contrast is justified, a 32×32 luminance guide. Bilinear sampling uses full-source pixel-center coordinates. Crop/strip rendering passes its full-source region, so maps are not stretched or re-estimated after cropping. Luminance guidance limits shadow lifts on bright objects and highlight darkening on dark objects. Per-hue chroma controls contain six bounded values; local-exposure/guide arrays must be empty or exactly 64/1024 finite values. Clarity requires its guide. These source-derived fields are private recipe data and are transmitted only through the authenticated image workflow.

This is a deterministic photographic controller, not a pretrained model or a demonstrated Lightroom equivalent. See [implementation and verification](docs/PHOTO_ENHANCEMENT_V3.md). Native float intermediates use 64-row cores plus overlapping original-pixel halos. Tonal analysis is bounded to 768 pixels per edge. V3 also samples up to five native 256×256 patches from the normalized source for texture, edge and noise evidence. Sampling does not guarantee scene-wide noise estimation or semantic segmentation. Bounded fine/medium luminance bands protect strong edges, noisy or smooth regions, extreme tones and warm moderately saturated colors; the latter is a hue proxy, not face detection. V3 texture/noise fields are rejected on older recipe versions. The optional 100% detail viewer uses the existing authenticated full-resolution export endpoint.

Errors use `{"error":{"code":"...","message":"..."}}` without raw exception or input details. Expected statuses include 400 malformed multipart, 401 invalid token, 404 unavailable session, 410 known expired session, 413 size limit, 415 unsupported/mismatched/animated format, 422 invalid request/image, 429 rate/capacity limit, 500 processing failure and 503 unavailable resource. Purged expired sessions return 404. Applicable errors include `WWW-Authenticate` or `Retry-After` headers.

## Configuration and capacity

`backend/.env.example` lists configurable settings; `app/config.py` defines their validation. Process environment variables override `.env`.

| Setting | Default / purpose |
| --- | --- |
| `DATABASE_URL` | Required pooled application-role URL |
| `DATABASE_DIRECT_URL` | Optional owner URL; required by migration/seed commands |
| `DATABASE_POOL_MAX_SIZE` | 4 connections |
| `DATABASE_TIMEOUT_SECONDS` | 5 seconds for acquisition, connection attempts and SQL statements |
| `TEMP_IMAGE_DIR` | `backend/.runtime/images`; relative paths resolve from `backend/` |
| `MAX_TEMP_IMAGE_BYTES` | 1,000,000,000 aggregate private-file budget |
| `MAX_UPLOAD_BYTES` | 10,000,000 file bytes, plus 65,536 allowed multipart-overhead bytes |
| `UPLOADS_PER_MINUTE` | 12 per client address |
| `MAX_IMAGE_PIXELS` | 24,000,000 decoded pixels |
| `MAX_IMAGE_SIDE` | 10,000 pixels |
| `PREVIEW_MAX_EDGE` | 1,600 pixels |
| `IMAGE_TTL_SECONDS` | 3,600 seconds, fixed from upload; edits do not renew it |
| `CLEANUP_INTERVAL_SECONDS` | 300 seconds |
| `JPEG_QUALITY` | 92; the current export contract accepts only quality 92 |
| `ALLOWED_ORIGINS` | `[]`; exact JSON origin list for separate frontend hosting |

Each process supports at most 32 sessions, one heavy upload/export/source-analysis operation and two preview operations concurrently. Busy/full requests receive 429. Session retirement waits for active readers before deleting files. Keep one worker and one replica because sessions, limits and processing permits are process-local.

For separate origins, configure e.g. `ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]` and restart. CORS exposes `X-Image-Revision` and `Content-Disposition`, permits the required methods/headers and disables cookie credentials.

## Migration and preset maintenance

Run migration and seed commands explicitly from `backend/` against the intended branch. Ordinary `python -m app` startup does not migrate or seed. The container entry point optionally runs both when `DATABASE_DIRECT_URL` is supplied.

- Add SQL as `NNN_description.sql` in increasing three-digit order. Never edit, rename or remove an applied migration.
- Applied filenames and SHA-256 checksums are recorded in `public.schema_migrations`; line endings are normalized before hashing.
- The runner takes a transaction-scoped advisory lock and applies all pending files in one transaction. A failure rolls back the batch; concurrent runs fail immediately. Changed, missing or out-of-order history is rejected.
- Use transactional SQL without explicit `BEGIN`, `COMMIT`, `ROLLBACK`, `VACUUM`, `CREATE DATABASE` or commands requiring separate transaction control. Adjust the statement timeout deliberately for longer migrations.
- `app/db/seed.py` validates and upserts all 35 built-ins by stable ID in one transaction. Repeating it restores their fields without duplicate IDs or deletion of unrelated rows.

## Tests and contract changes

From `backend/`:

```powershell
uv run --locked pytest
uv run --locked python -m scripts.benchmark_images
```

The ordinary suite uses temporary files and simulated database resources; it does not require a live database. Validate SQL constraints, migration rollback/checksums, repeatable seeding and application-role permissions separately on an isolated database branch.

After intentional schema changes, from `frontend/`:

```powershell
npm run contracts:generate
npm run contracts:check
npm run build
```

Review and commit `frontend/src/lib/api.generated.ts`. Contract export requires the installed backend environment and uv, but no running server or database. See [Frontend_doc](Frontend_doc.md#verification) for browser tests without Neon.

## Deployment and release checks

The root `Dockerfile` builds `frontend/dist`, installs locked production backend dependencies and starts `python -m app.deploy` as a non-root user. It serves the SPA and API from one origin, binds `0.0.0.0` to process `PORT` (default 8000), and uses `/tmp/lumalab/images` for private volatile storage. Use `app.main:application` for custom ASGI deployments so the outer middleware is included.

For Railway, deploy from the repository root, supply service secrets, generate an HTTPS domain, set `/api/v1/health` as the health path and keep one worker/replica. Prefer a separate migration/seed release step followed by deployment with only `DATABASE_URL`. Optional automatic bootstrap requires the direct owner URL for the same branch/database and stops startup on failure.

Set `FORWARDED_ALLOW_IPS` in the process/container environment, not backend `.env`, to trusted ingress IPs/CIDRs; the default is `127.0.0.1`. Use `*` only when direct untrusted access is prevented and the ingress replaces untrusted forwarding headers. Validate client-IP rate limiting through the real ingress.

Before public release, record evidence for the release commit:

- Deploy to an isolated staging database/environment with production-like resource limits and real credentials; never deploy `scripts.e2e_server`.
- Verify HTTPS, health, direct SPA navigation, missing API/asset errors, exact CORS origins, security headers and read-only database access.
- Exercise upload/edit/enhance/compare/export, invalid and maximum-size images, wrong/cross-session tokens, deletion, expiry and restart recovery.
- Rerun tests, build and contract checks. Review fresh Python/npm dependency and built-container scans and resolve release-blocking findings; retain independent security-test findings and their disposition.
- Measure mixed concurrent uploads/previews/exports and sustained cleanup on the hosting target. Record CPU, memory peaks, response times, errors and restarts; choose memory with measured headroom.
- Record the release owner, exceptions, rollback target/triggers, migration compatibility and monitoring. An application rollback does not automatically undo database changes. Smoke-test production after deployment.

Do not attach durable photo storage for the current session model. Existing sessions may continue through a database-only outage, but preset/readiness requests fail; reload or retry after recovery. Restart/redeploy requires re-upload. Processing has no separate hard wall-clock cancellation; validate hosting timeouts with maximum inputs.

Historical local evidence from 17 November 2026 recorded 111 backend tests plus 530 subtests. A standalone 24 MP noisy export measured 361.7 MiB peak working set and 9.616 seconds on Windows; this is not a full-server or container capacity guarantee. These are historical results, not checks rerun by this documentation update. Hosted load validation, fresh backend/container scans and independent penetration testing were still release tasks in that record.
