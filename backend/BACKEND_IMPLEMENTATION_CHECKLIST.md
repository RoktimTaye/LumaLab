# LumaLab — Remaining Backend and API Integration Work

**Updated:** 13 November 2026  
**Status:** A01–A08 and B01–B04 verified, including separate pooled application and direct migration connections over TLS. Awaiting the owner's go-ahead for B05.  
**Target:** Complete the MVP upload → edit → enhance → compare → download workflow.  
**Database decision:** Neon PostgreSQL replaces the SQLite database specified in the original PRD.

## 1. Scope and implementation rules

This document records the remaining work requested by the project owner. Use it alongside `LumaLab_Product_Requirements_Document_Final.md`, the supplied design-style document, and the existing application. Later explicit user requirements take precedence over this checklist.

- Preserve the existing React, TypeScript, Vite, TanStack Router/Query, CSS Modules, RGBW identity, responsive layouts, and navigation.
- Keep the frontend in its current repository location. Add a `backend/` directory; do not reorganize the whole repository just to match the illustrative PRD folder tree.
- Use FastAPI, Pydantic, Uvicorn, Pillow, OpenCV, NumPy, and Neon PostgreSQL.
- Keep one FastAPI backend and one active photograph per editing session.
- Use the backend as the authoritative renderer for settled previews and exports. Browser filters are optional temporary approximations.
- Store preset definitions in Neon, photographs in private temporary file storage, and active slider state in React.
- Keep temporary image-session metadata in backend memory for the initial single-process implementation. A restart may end sessions. Multiple processes require a separate shared-state/storage design.
- Do not add accounts, persistent editing history, cloud photo libraries, custom presets, RAW support, batch processing, crop/rotate, masks, undo/redo history, PNG export, background removal, or trained AI models.
- Do not add paid AI providers or send images to third-party AI services.
- Keep implementation limited to the MVP requirements. Add dependencies only when they solve a concrete requirement.
- Never put credentials, access tokens, uploaded photographs, or runtime temporary files into Git.
- This checklist does not itself start implementation or authorize deployment. Begin development when the user requests it.

## 2. Existing frontend baseline

The frontend already contains:

- Home and `/studio` routes, responsive layouts, navigation, keyboard controls, and comparison UI.
- Local file selection/drop, initial format/size checks, image metadata, and replacement handling.
- Six adjustment controls, complete preset objects, Custom state, and reset.
- CSS/SVG previews and local original/edited comparison.
- Placeholder Auto Enhance and Export dialogs that explain the unavailable backend.
- TanStack Query's provider, but no real API queries or mutations.
- Frontend build, unit tests, browser tests, and verification documentation.

Useful integration points:

| Existing file | Work to perform during integration |
| --- | --- |
| `src/lib/editor.ts` | Preserve adjustment types and bounds; move preset authority to the backend/Neon |
| `src/pages/Studio.tsx` | Connect upload sessions, preview, enhancement, export, cleanup, and real pending/error states |
| `src/components/PhotoPreview.tsx` | Display authoritative original/edited image responses at identical geometry |
| `src/pages/Home.tsx` | Update feature availability and processing/privacy copy; retain an explicitly labelled demo where appropriate |
| `src/main.tsx` | Reuse the Query provider and existing routing |
| `vite.config.ts` | Add the development `/api` proxy |
| `.gitignore` | Exclude backend secrets, environments, caches, and private runtime files |
| `README.md`, `VERIFICATION.md` | Document the connected application and actual validation results |

Do not treat earlier frontend test results as proof that the eventual connected backend works. Re-run relevant checks after integration.

## 3. Work sequence

| Phase | Deliverable | Depends on |
| --- | --- | --- |
| A | Backend foundation and configuration | Existing repository |
| B | Neon schema, migrations, and seeded presets | A and Neon connection configuration |
| C | Typed API contracts and common error handling | A |
| D | Validated uploads and private temporary sessions | A, C |
| E | Shared rendering pipeline and original/edited previews | D |
| F | Auto Enhance and full-resolution export | E |
| G | Real frontend API integration and recovery states | B–F; integrate incrementally as endpoints become usable |
| H | Security, limits, cleanup, and deployment configuration | A–G; enforce safeguards as each feature is built |
| I | End-to-end verification and handoff | A–H |

### A. Backend foundation

- [x] A01 — Create the FastAPI application and Uvicorn entry point in `backend/`.
- [x] A02 — Separate route modules, Pydantic schemas, image services, temporary storage, database access, and configuration.
- [x] A03 — Add compatible stable dependencies for FastAPI, Pydantic/settings, Uvicorn, multipart uploads, Pillow, OpenCV, NumPy, and Psycopg 3.
- [x] A04 — Manage Python dependencies with `pyproject.toml` and `uv.lock`; document the supported Python version.
- [x] A05 — Add validated environment-based configuration and a secret-free `.env.example`.
- [x] A06 — Configure application startup/shutdown, resource initialization, and cleanup.
- [x] A07 — Implement health/readiness checks, including required database and temporary-storage availability.
- [x] A08 — Add useful operational logging without tokens, credentials, photo contents, private metadata, or exposed internal paths.

**Acceptance:** The backend starts reproducibly from its lockfile, responds to health checks, and fails clearly when required configuration is invalid.

**A01 evidence (12 November 2026):** Added `backend/app/main.py` and the `python -m app` Uvicorn entry point. Minimal `pyproject.toml` and `uv.lock` support reproducible startup with FastAPI 0.162.4 and Uvicorn 0.54.0 on Python 3.11.9. Locked installation and a live HTTP smoke check passed: OpenAPI and Swagger UI return 200; the unimplemented root returns 404. See `VERIFICATION.md`. The full phase A acceptance criteria are not yet satisfied. Dependency-management groundwork for A04 was needed to run A01, but the full A03 dependency set is deferred.

**A02 evidence (12 November 2026):** Added separate `routes`, `schemas`, `services`, `storage`, and `db` packages plus `config.py`. Registered the shared `/api/v1` router in `main.py`; other modules contain responsibility docstrings only. Module imports, router prefix, OpenAPI/Swagger responses, and unimplemented-route 404s passed smoke checks. A03–A08 remain pending; no business endpoints or extra dependencies were added.

**A03 evidence (12 November 2026):** Resolved stable runtime dependencies from PyPI, pinned direct versions, and updated `uv.lock`. Added Pydantic/settings, python-multipart, Pillow, headless OpenCV, NumPy, and Psycopg 3 with binary/pool extras. Locked offline synchronization, installed-package compatibility, imports, multipart registration, JPEG/PNG/WebP encoding/decoding, NumPy/OpenCV interoperability, and Psycopg binary/pool loading passed. Exact versions and verification scope are recorded in `VERIFICATION.md`. No application logic was added; A04–A08 remain pending.

**A04 evidence (12 November 2026):** Existing `pyproject.toml`, `uv.lock`, and `.python-version` satisfy dependency management without further code changes. Verified lock consistency and installed into a fresh temporary environment offline from the cache; all 24 installed package versions matched the development environment, compatibility/import/OpenAPI checks passed, and SHA-256 checks confirmed both dependency files were unchanged. Removed the verification environment. Documented CPython 3.11 as the development baseline, tested with Python 3.11.9/uv 0.10.10 on Windows; newer Python versions and other operating systems are untested. A05–A08 remain pending.

**A05 evidence (12 November 2026):** Implemented Pydantic environment settings and startup validation, plus a secret-free `backend/.env.example`. Validates PostgreSQL URL/SSL requirements, numeric bounds, related limits, private storage paths and explicit origins. Environment variables override the backend-local `.env`; credentials are masked and validation errors omit input values. Six configuration tests pass, including subprocess startup and secret-redaction checks. No database connections or runtime directories are created by this step. Resource initialization and readiness remain A06–A07; operational resource-limit settings will be added with their enforcing features.

**A06 evidence (12 November 2026):** Added a FastAPI lifespan hook, bounded on-demand Psycopg pool, and private per-run temporary storage. Graceful shutdown closes the pool, removes only the owned run directory, and clears resource references; startup failure and cancellation also release acquired resources. Added validated pool-size/acquisition/connection-timeout settings. All 12 configuration/lifecycle tests pass, including preservation of unrelated files and safe cleanup refusal for a substituted path. No live database was contacted; readiness remains A07 and stale/expired-session cleanup remains phase D. No dependencies were added.

**A07 evidence (12 November 2026):** Added `GET /api/v1/health` with typed OpenAPI responses: 200 when a database query and temporary-file write/read/delete probe pass, otherwise a generic 503 error envelope. Responses use `Cache-Control: no-store`. Pool acquisition and the database statement use the configured timeout; checks run in a synchronous threadpool handler. All 19 backend tests pass, covering failure/recovery, response redaction, missing resources and probe cleanup. Database responses were simulated; live Neon verification remains pending connection setup. No dependencies were added. A08 remains pending.

**A08 evidence (12 November 2026):** Added JSON console logging with UTC time, severity and approved event categories for lifecycle, resource and readiness failures. Raw message/argument/exception/extra-field content is excluded; Uvicorn access logging is disabled and driver/server logs use fixed categories. The module entry point supports the same policy with `--reload`, and invalid settings exit without a traceback. All 25 backend tests pass, including synthetic-secret/metadata/path exclusion, repeated logging setup, launch configuration and lifecycle-event checks. No dependencies were added. Live Neon connection verification and the remaining project completion gates are still pending.

### B. Neon PostgreSQL and presets

- [x] B01 — Configure the Neon project, database, branch, and application database role.
- [x] B02 — Read the database connection string from backend environment variables; require SSL.
- [x] B03 — Use Psycopg 3 with controlled connection lifetime, connection/query timeouts, and bounded pooling.
- [x] B04 — Use Neon's pooled connection for application traffic and a direct connection for migration tooling where needed.
- [ ] B05 — Add versioned PostgreSQL migrations and a repeatable migration command.
- [ ] B06 — Create the `presets` table described below with primary-key, not-null, and numeric-bound constraints.
- [ ] B07 — Add an idempotent seed/upsert command for the five existing preset definitions.
- [ ] B08 — Validate preset values in Pydantic as well as database constraints.
- [ ] B09 — Implement read-only preset retrieval with stable identifiers and deterministic display order.
- [ ] B10 — Handle unavailable Neon connections, timeouts, and reconnects without leaking credentials or crashing the application.
- [ ] B11 — Test migrations/seeding in an isolated test database or Neon development branch; do not run destructive tests against the production database.

**B01 evidence (13 November 2026):** Following the owner's selection of a new database, created project `LumaLab` (`shy-field-11180671`) in AWS Singapore on the existing Free organization, using PostgreSQL 18. Database `lumalab` is owned by `lumalab_owner`. Default branch `main` is `br-sweet-salad-b38p818v`; its development child is `br-small-frost-b3yx6xrk`. Both branches reached `ready`. Compute is capped at 0.25 CU with plan-default idle suspension. The existing `Durga Ma` project was not changed.

Created `lumalab_app` with a server-generated random password on the development branch using SQL, without `neon_superuser` membership. Verified a live query as that role, CONNECT/USAGE privileges, and absence of superuser, database/role creation, replication, RLS-bypass, schema/table creation and temporary-table privileges. Preset-table grants, migrations and seeding remain pending. No passwords were printed or written into tracked files; no local `.env` was created. Local connection and client SSL verification belong to B02. See [Neon's role documentation](https://neon.com/docs/manage/roles).

**B02 evidence (13 November 2026):** Reused the existing environment-based settings and mandatory SSL validation without adding application code or dependencies. Configured the ignored local `backend/.env` with the development branch's pooled `lumalab_app` URL and `sslmode=require`. A local Psycopg connection confirmed TLS via `PGconn.ssl_in_use`, the expected database/role, and a successful read-only query. The actual ASGI readiness endpoint returned 200 with `{"status":"ready"}` and `Cache-Control: no-store`; shutdown closed the pool and removed the run directory. All 25 backend tests pass. Git ignores the credential file, and a scan found no database credential in version-control-eligible files. B03 remains pending.

**B03 evidence (13 November 2026):** Kept the existing bounded Psycopg pool and configurable acquisition/connection timeout. Set explicit 1,800-second connection lifetime and 60-second idle shrink controls. Extracted the existing transaction-local statement timeout into the shared `database_connection` context manager, used by readiness and available for later preset queries. Pool contexts commit or roll back before returning connections. All 27 tests pass. A read-only live development check verified TLS, query cancellation at a one-second timeout, rollback, reuse of the same connection, timeout reset between transactions, acquisition timeout with an exhausted one-connection pool, successful subsequent readiness database probe and pool shutdown. No dependencies or frontend code changed. B04 remains pending.

**B04 evidence (13 November 2026):** Preserved the pooled `DATABASE_URL` for `lumalab_app` and configured the ignored local `DATABASE_DIRECT_URL` for `lumalab_owner` on the same development branch/database. Existing settings already support both; no application code or dependencies were added. Read-only local checks verified TLS on both connections, the expected roles/database, schema CREATE permission for the migration owner and its absence for the application role, and connection cleanup. The application pool continues to use only `DATABASE_URL`. Updated the environment example and setup guidance to distinguish roles and endpoints. All 27 tests pass. Migration tooling and schema changes remain B05 onward.

Required schema:

| Column | PostgreSQL type | Constraint |
| --- | --- | --- |
| `preset_id` | TEXT | Primary key; stable slug |
| `preset_name` | TEXT | Not null |
| `description` | TEXT | Not null |
| `brightness` | INTEGER | 0–200, not null |
| `contrast` | INTEGER | 0–200, not null |
| `saturation` | INTEGER | 0–200, not null |
| `warmth` | INTEGER | −50–50, not null |
| `sharpness` | INTEGER | 0–100, not null |
| `vignette` | INTEGER | 0–100, not null |

Initial version-controlled seed values, matching `src/lib/editor.ts` at planning time:

| ID | Name | Brightness | Contrast | Saturation | Warmth | Sharpness | Vignette |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `original` | Original | 100 | 100 | 100 | 0 | 0 | 0 |
| `cinematic` | Cinematic | 98 | 120 | 78 | −12 | 12 | 22 |
| `golden-hour` | Golden Hour | 110 | 94 | 112 | 22 | 5 | 8 |
| `monochrome` | Monochrome | 102 | 125 | 0 | 0 | 18 | 16 |
| `vivid` | Vivid | 103 | 110 | 140 | 2 | 30 | 0 |

**Acceptance:** A fresh Neon database can be migrated and seeded repeatedly without duplicates; invalid values are rejected, and the presets API returns all five complete definitions.

### C. API contracts and shared HTTP behaviour

- [ ] C01 — Implement all eight endpoints in the table below under `/api/v1`.
- [ ] C02 — Define Pydantic request/response models and document them in FastAPI OpenAPI.
- [ ] C03 — Define a strict integer adjustment object with all six fields and documented bounds. Do not silently accept fractional or out-of-range values.
- [ ] C04 — Use multipart `file` for uploads and JSON for preview/export settings.
- [ ] C05 — Require `Authorization: Bearer <image-access-token>` on every image-specific endpoint. Tokens must not appear in URLs.
- [ ] C06 — Return image bytes directly; use browser object URLs for display/download.
- [ ] C07 — Standardize errors, including request-validation failures, as `{ "error": { "code": "...", "message": "..." } }`.
- [ ] C08 — Define and test relevant HTTP statuses: 201 upload, 204 deletion, 401 invalid token, 404 unavailable image, 410 known expired session, 413 size limit, 415 unsupported format, 422 decoding/validation failure, 429 capacity limit, and 500 unexpected failure. Document service-unavailable responses as needed.
- [ ] C09 — Return `Cache-Control: no-store` for private image/session responses.
- [ ] C10 — Include `X-Image-Revision` on preview responses and appropriate content/download headers on exports.
- [ ] C11 — Expose revision and download headers through CORS if using separate frontend/backend origins.
- [ ] C12 — Generate or check frontend TypeScript contracts against OpenAPI; document the regeneration/check command.

| Method | Endpoint | Contract |
| --- | --- | --- |
| GET | `/api/v1/health` | Service readiness JSON |
| GET | `/api/v1/presets` | Five presets with stable IDs, descriptions, and complete adjustments |
| POST | `/api/v1/images` | Multipart upload; return HTTP 201 with image ID, secret token, filename, detected format, oriented dimensions, and expiry |
| GET | `/api/v1/images/{image_id}/original-preview` | Authorized normalized original-preview bytes |
| POST | `/api/v1/images/{image_id}/preview` | Accept revision and complete adjustments; return JPEG bytes with matching revision header |
| POST | `/api/v1/images/{image_id}/enhance` | Analyse original; return complete adjustments and user-facing feedback |
| POST | `/api/v1/images/{image_id}/export` | Accept complete adjustments, `format: "jpeg"`, and `quality: 92`; return full-resolution JPEG attachment |
| DELETE | `/api/v1/images/{image_id}` | Authorized deletion; HTTP 204 |

Preview request shape from the PRD:

```json
{
  "revision": 7,
  "adjustments": {
    "brightness": 110,
    "contrast": 115,
    "saturation": 120,
    "warmth": 10,
    "sharpness": 15,
    "vignette": 5
  }
}
```

Preset application copies a preset's full values into editor state and calls the normal preview endpoint. It does not require another endpoint.

**Acceptance:** Documented contracts, status codes, security requirements, headers, and frontend types agree with actual endpoint responses.

### D. Upload validation and private sessions

- [ ] D01 — Accept still JPG/JPEG, PNG, and WebP; validate extension, detected content format, decoding, and frame count independently of frontend checks.
- [ ] D02 — Reject unsupported, corrupt, animated, and multi-frame files.
- [ ] D03 — Enforce configurable limits of **10,000,000 bytes**, **24,000,000 decoded pixels**, and **10,000 pixels per side**. Bound incoming data before expensive processing where possible.
- [ ] D04 — Protect against decompression bombs and malformed image metadata.
- [ ] D05 — Apply EXIF orientation to working images and report the resulting dimensions.
- [ ] D06 — Preserve uploaded original bytes separately from normalized/derived files.
- [ ] D07 — Generate unpredictable image IDs and separate secret access tokens. Never use submitted filenames as storage paths.
- [ ] D08 — Store originals, previews, and exports outside public/static directories with restricted access.
- [ ] D09 — Track upload time and a fixed **60-minute expiry**; return expiry to the frontend.
- [ ] D10 — Require valid session authorization for every read, processing request, export, and deletion.
- [ ] D11 — Clean expired files at least every **five minutes** and remove stale files during startup.
- [ ] D12 — Coordinate processing/deletion so cleanup does not remove files in active use; release them safely afterward.
- [ ] D13 — Support deletion after successful image replacement and explicit session closure. Browser-close cleanup remains best effort; server expiry is mandatory.
- [ ] D14 — Clean partial uploads and failed intermediate files.
- [ ] D15 — Return clear unavailable/expired-session responses after expiry or backend restart.
- [ ] D16 — Preserve the current frontend session and settings when a replacement upload fails.

**Acceptance:** Invalid uploads are rejected without losing valid edits; sessions are private, isolated, time-limited, and cleaned without processing races.

### E. Shared image renderer and comparison

- [ ] E01 — Normalize orientation, convert supported input profiles to sRGB, and composite alpha onto white before adjustments.
- [ ] E02 — Implement brightness, contrast, and saturation as factors of `value / 100`.
- [ ] E03 — Define and document bounded warmth, sharpness, and vignette formulas.
- [ ] E04 — Apply effects in the fixed order **brightness → contrast → saturation → warmth → sharpness → vignette**.
- [ ] E05 — Render each request from the normalized original and one complete adjustment object; never compound edits on a previous preview.
- [ ] E06 — Preserve the normalized image's appearance at neutral settings before JPEG encoding.
- [ ] E07 — Preserve grayscale when saturation is zero, including when warmth is nonzero.
- [ ] E08 — Scale sharpness radius and vignette geometry consistently with image dimensions.
- [ ] E09 — Generate previews with maximum long edge **1,600 pixels**, preserving aspect ratio.
- [ ] E10 — Generate the normalized original preview with the same orientation, scale, colour handling, and white compositing used for edited previews.
- [ ] E11 — Strip private metadata from encoded previews and exports.
- [ ] E12 — Reuse the same rendering pipeline for reduced previews and full-resolution exports.
- [ ] E13 — Execute CPU-heavy processing outside the async event loop through synchronous handlers or explicit bounded execution.
- [ ] E14 — Limit concurrent renders and prevent unbounded preview-request queues.

**Acceptance:** All controls combine correctly, Original/reset restores the normalized original, comparison preserves settings, and resized exports match previews within expected resampling/compression differences.

### F. Automatic enhancement and JPEG export

- [ ] F01 — Analyse original-image brightness, contrast, saturation, colour balance, and tonal distribution using OpenCV/NumPy.
- [ ] F02 — Use a reduced analysis image where suitable to bound processing cost.
- [ ] F03 — Calculate bounded brightness, contrast, saturation, and warmth suggestions; return sharpness and vignette at zero.
- [ ] F04 — Always analyse the same original, so repeated Auto Enhance does not accumulate edits.
- [ ] F05 — Allow balanced photographs to receive neutral or subtle adjustments.
- [ ] F06 — Return all six validated values and meaningful completion feedback; preserve previous edits on failure.
- [ ] F07 — Apply the returned values in the frontend, mark Auto Enhanced, and render an authoritative preview before allowing export of those new settings.
- [ ] F08 — Keep manual refinement and reset available after enhancement; manual refinement changes the label to Custom.
- [ ] F09 — Render exports from the full-resolution oriented original using an immutable snapshot of the requested adjustments.
- [ ] F10 — Export JPEG at default quality **92/100**; quality selection is optional and must stay within backend-supported bounds if added.
- [ ] F11 — Export sRGB, flatten transparent regions onto white, and strip EXIF/GPS metadata.
- [ ] F12 — Sanitize the download filename, for example `lumalab-<original-name>.jpg`.
- [ ] F13 — Return `Content-Type: image/jpeg` and a safe `Content-Disposition` attachment filename.
- [ ] F14 — Implement export loading, success, failure, and explicit retry; prevent duplicate export and enhancement requests.
- [ ] F15 — Verify that edits made after export starts cannot alter the in-progress download.

**Acceptance:** Auto Enhance is non-cumulative and editable; downloads contain the exact snapshotted settings at original oriented resolution with the required format and privacy properties.

### G. Frontend API integration

- [ ] G01 — Add a centralized typed API client with configurable base URL, request cancellation, error parsing, authorized image requests, and blob handling.
- [ ] G02 — Retrieve presets from Neon through FastAPI and TanStack Query; remove hardcoded studio presets as the production source of truth.
- [ ] G03 — Wire upload, preview, enhancement, export, and deletion into TanStack Query queries/mutations or an appropriately cancellable preview request layer.
- [ ] G04 — Keep local editor state in React; do not make the Query cache the primary store for sliders or image pixels.
- [ ] G05 — Replace local-only image sessions with backend IDs, tokens, metadata, normalized previews, and expiry information.
- [ ] G06 — Keep image access tokens in memory, outside URLs, logs, and persistent browser storage.
- [ ] G07 — Keep slider values immediate; request a preview after roughly **250 ms** without a new change and immediately on slider release. Avoid duplicate release/debounce requests.
- [ ] G08 — Reconcile any temporary browser approximation with the settled backend preview.
- [ ] G09 — Track image identity and increasing preview revisions; accept a response only if both match the current editor state.
- [ ] G10 — Cancel obsolete requests where possible and ignore late results, including enhancement responses after replacement or newer manual edits.
- [ ] G11 — Preserve the last successful preview during processing or recoverable failures, and visibly mark it outdated when it does not match current settings.
- [ ] G12 — Wire original/edited comparison to normalized backend previews with identical image geometry; comparison must not change settings or request another edit.
- [ ] G13 — Connect Auto Enhance and Export controls and replace the service-unavailable placeholder dialogs with real flows.
- [ ] G14 — Keep export disabled without a valid image or while export is pending; require a current successful authoritative preview for the settings being exported.
- [ ] G15 — On successful replacement, reset preset/adjustments/comparison, cancel old work, clear old image-specific state, and request deletion of the previous image.
- [ ] G16 — Release obsolete preview/download object URLs and clear image-specific query data on session replacement/closure.
- [ ] G17 — Ensure the bundled sample uses the real upload/render pipeline when opened in the studio, rather than remaining a separate local-only editing path.
- [ ] G18 — Add clear loading, success, failure, expired-session, service-unavailable, and capacity-limit states with accessible status announcements.
- [ ] G19 — Avoid automatic retries for upload/enhancement/export mutations. Offer explicit retries; use only bounded retries for suitable read-only queries.
- [ ] G20 — Update home/studio feature availability and privacy copy: photographs are processed by the backend and stored temporarily. Remove browser-only privacy claims from the connected editing workflow.
- [ ] G21 — Preserve phone/tablet/desktop usability, keyboard controls, visible focus, reduced-motion support, and the existing navigation design.

**Acceptance:** A user can enter the studio, upload or load a sample, edit, switch presets, enhance, compare, export, and replace an image using real backend responses with truthful feedback.

### H. Security, reliability, and environment configuration

- [ ] H01 — Use parameterized database queries and validate all external input on the server.
- [ ] H02 — Prevent path traversal and never execute uploaded content.
- [ ] H03 — Bound upload frequency, simultaneous processing, temporary disk use, request size, and execution time; document initial configurable limits.
- [ ] H04 — Return actionable capacity errors instead of unbounded memory/CPU growth or silent request loss.
- [ ] H05 — Ensure errors do not expose credentials, tokens, stack traces, filesystem paths, or private metadata.
- [ ] H06 — Prefer a Vite `/api` proxy during development; if separate origins are used, allow only configured frontend origins in CORS.
- [ ] H07 — Serve the production frontend and `/api/v1` under one origin through FastAPI or a reverse proxy.
- [ ] H08 — Configure SPA fallback for `/studio` without intercepting API, documentation, or missing asset responses.
- [ ] H09 — Configure HTTPS and suitable request-size/time limits when hosted beyond the local machine.
- [ ] H10 — Configure private writable temporary storage and cleanup for the selected host. Do not assume ephemeral hosting storage provides durable sessions.
- [ ] H11 — Run one backend process initially. Revisit session sharing and storage coordination before adding workers/instances.
- [ ] H12 — Exclude `.env`, backend virtual environments, caches, runtime images, temporary files, and generated private artifacts from Git.
- [ ] H13 — Document Neon network dependence and clear recovery behaviour when the database or image service is unreachable.

Configuration to define and document (names below are proposed; keep final names consistent):

| Setting | Purpose / initial requirement |
| --- | --- |
| `DATABASE_URL` | Backend-only SSL-enabled Neon application connection |
| `DATABASE_DIRECT_URL` | Direct migration connection, if required by migration tooling |
| `TEMP_IMAGE_DIR` | Private temporary image directory |
| `MAX_UPLOAD_BYTES` | 10000000 |
| `MAX_IMAGE_PIXELS` | 24000000 |
| `MAX_IMAGE_SIDE` | 10000 |
| `PREVIEW_MAX_EDGE` | 1600 |
| `IMAGE_TTL_SECONDS` | 3600 |
| `CLEANUP_INTERVAL_SECONDS` | At most 300 |
| `JPEG_QUALITY` | 92 |
| Allowed origins | Explicit frontend origins when CORS is used |
| Processing/storage limits | Bounded concurrency, timeouts, request rate, and disk budget |

Use example placeholders in tracked configuration. Supply real Neon credentials through an untracked backend environment file or hosting secret configuration; never through frontend `VITE_*` variables.

**Acceptance:** The application runs with documented configuration, keeps private data private, handles resource pressure predictably, and supports direct studio URLs in production.

### I. Testing, performance, and handoff

- [ ] I01 — Add pytest coverage for schemas, upload checks, sessions, authorization, processing, enhancement, export, and cleanup.
- [ ] I02 — Test PostgreSQL constraints, migrations, repeatable seeding, preset retrieval, and database failure handling against isolated test data.
- [ ] I03 — Create fixtures for JPEG/PNG/WebP, transparency, EXIF rotation, grayscale, supported colour profiles, corruption, animation, multi-frame inputs, and supported-limit cases.
- [ ] I04 — Test exact byte/pixel/side boundaries and out-of-range/fractional adjustment rejection.
- [ ] I05 — Verify that all six controls combine correctly and every preset replaces the complete state without accumulation.
- [ ] I06 — Verify grayscale preservation, neutral settings, repeated enhancement, balanced-image results, and reset behaviour.
- [ ] I07 — Verify missing/invalid tokens, cross-image token isolation, expiry, cleanup, and restart recovery.
- [ ] I08 — Verify failed replacement preservation and rapid edits/replacements with out-of-order responses.
- [ ] I09 — Compare authoritative previews against resized full-resolution exports for material brightness, colour, and effect differences.
- [ ] I10 — Verify exported dimensions, JPEG format/quality settings, safe filenames, white transparency handling, and removal of EXIF/GPS metadata.
- [ ] I11 — Verify original uploaded bytes remain unchanged.
- [ ] I12 — Add connected Playwright coverage for the full upload → edit → enhance → compare → download workflow, including explicit retry and unavailable-service cases.
- [ ] I13 — Run relevant frontend unit tests, strict TypeScript checks, and the production build after integration.
- [ ] I14 — Check Chrome, Firefox, Edge, and Safari where available; document versions and unavailable coverage honestly.
- [ ] I15 — Check the required responsive widths, keyboard/touch input, focus, reduced motion, text enlargement, zoom/reflow, long filenames, and loading/error layouts.
- [ ] I16 — Measure performance on a documented reference laptop with at least 8 GB RAM; record CPU, browser, image dimensions, timings, and memory/resource observations.
- [ ] I17 — Verify reproducible setup from npm and uv lockfiles and check generated frontend contracts against OpenAPI.
- [ ] I18 — Update README setup/run/build/test instructions, Neon configuration, migrations/seeding, temporary-storage cleanup, and deployment guidance.
- [ ] I19 — Update API documentation, system architecture, MVP data model, and Level 0/Level 1 data-flow documentation to reflect Neon.
- [ ] I20 — Produce the connected test/verification report, remaining limitations, and an upload-to-export demonstration.
- [ ] I21 — Update the academic project documentation/report required by the original PRD with the final implemented architecture and measured results.

Performance targets from the PRD; these are targets to measure, not guarantees:

| Operation | Target |
| --- | --- |
| Home page usable | Within 3 seconds on the documented reference setup |
| Slider value/interaction feedback | Within 100 ms |
| Settled 1,600-pixel preview | Within 1 second after debounce under single-user load |
| Auto Enhance | Within 3 seconds for a representative 12 MP image |
| Full-resolution export | Within 5 seconds for that representative image |
| Largest supported input | Completes without exhausting resources |

Responsive matrix: **320×568, 360×800, 390×844, 430×932, 768×1024, 820×1180, 1024×768, 1280×800, 1440×900, 1920×1080, 2560×1440, and 844×390**. Also inspect intermediate widths around breakpoints. Record actual browser/device coverage rather than claiming all devices were tested.

**Acceptance:** The connected workflow is verified with representative and invalid inputs, performance results are recorded, remaining limitations are explicit, and another developer can reproduce the application from the documentation.

## 4. Completion gate

Do not mark the remaining project work complete until:

- [ ] FastAPI and Neon start/connect using documented configuration and locked dependencies.
- [ ] All eight APIs implement the documented contracts and authorization rules.
- [ ] Presets come from Neon and all six manual controls work through authoritative rendering.
- [ ] Auto Enhance and full-resolution JPEG download function end to end.
- [ ] Original preservation, comparison, reset, replacement, and export snapshots are correct.
- [ ] Preview and export have no material visual mismatch.
- [ ] Validation, error handling, stale-response protection, expiry, and cleanup are verified.
- [ ] The connected UI retains its responsive and accessible behaviour.
- [ ] Required tests/builds pass, or any acceptance exceptions are explicitly reported rather than marked passed.
- [ ] Documentation describes Neon, the actual deployment model, privacy behaviour, and measured results.
- [ ] Runtime files and secrets are excluded from the committed source.

Track completion by checking an item only after its implementation and relevant verification are finished. Record blockers and test evidence alongside the phase or in `VERIFICATION.md`; do not treat this checklist's existence as completed implementation.

## 5. Reference material

- Product baseline: `LumaLab_Product_Requirements_Document_Final.md` supplied by the project owner.
- Styling baseline: `Infrastructure_Design_Style_PRD (12).md` supplied by the project owner.
- User decision: Neon PostgreSQL replaces SQLite; backend development follows a separate instruction to begin.
- [Neon Python connection guide](https://neon.com/docs/guides/python)
- [Neon connection pooling guide](https://neon.com/docs/connect/connection-pooling)
- [Current frontend setup](README.md)
- [Existing verification record](VERIFICATION.md)
