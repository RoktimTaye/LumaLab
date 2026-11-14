# Frontend verification

## Backend D13 verification — 14 November 2026

- Audited the existing authenticated DELETE endpoint. It supports deleting an old image session after a replacement upload succeeds and closing the current session explicitly; deletion requires that session's bearer token and removes its files and record.
- One new ASGI workflow test uploads two images, confirms the old session still works until explicitly deleted, rejects the replacement token for deleting the old session, verifies deletion leaves the new image usable and unchanged, then closes the new session and confirms both directories are gone. All 42 image API tests passed. The full 98-test backend suite passed at D12; no runtime code changed for D13.
- Browser-close cleanup is best effort; fixed server expiry and scheduled cleanup are already implemented. Frontend replacement/closure integration remains phase G. No dependencies or frontend behavior changed; D14 remains pending.

## Backend D12 verification — 14 November 2026

- Audited processing and deletion: authorized session access holds the store lock through rendering, enhancement and export, and purge/deletion use the same lock. Expired files therefore stay available to an operation already in progress, then are removed after it releases the lock.
- Shielded the periodic cleanup worker and awaited it during lifespan cancellation so shutdown cannot remove its run directory while cleanup is still in progress. Two concurrency tests verify that cleanup and deletion wait for an active session and finish afterward, and that shutdown waits for a deliberately blocked cleanup worker. All 98 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`.
- No dependencies, database or frontend behavior changed. D12 is complete; D13 remains pending.

## Backend D11 verification — 14 November 2026

- Added a lifespan-owned cleanup task at the configured interval, defaulting to five minutes and validated not to exceed it. It removes expired session records/files under the existing store lock without waiting for another request, then stops on shutdown. New uploads use the same purge method.
- Startup now removes old `lumalab-run-*` directories inside the configured private storage root when their modification time exceeds the session TTL. It preserves recent run directories, unrelated names and non-directory entries; symlinks are skipped. Two lifecycle tests exercise scheduled expiry with a one-second test interval and selective startup removal. All 96 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`.
- No dependencies, database or frontend behavior changed. The documented deployment is single-process; active-use coordination remains D12. D11 is complete.

## Backend D10 verification — 14 November 2026

- Audited all image session routes. Original preview, adjusted preview, enhancement, export and deletion already require an image-specific bearer token and use the same authorized-session check before accessing files or processing. Token hashes are compared with `secrets.compare_digest`; unknown sessions, invalid tokens and expired sessions have separate responses.
- Existing ASGI coverage exercises missing, wrong, cross-session and malformed tokens on every operation; query, cookie and JSON tokens do not authorize requests. Failed authorization does not call render/enhance or remove sessions. OpenAPI declares bearer security for every session route. All 40 image API tests passed. The full 94-test backend suite passed at D09; no runtime code changed for D10.
- No dependencies, database or frontend behavior changed. D10 is complete; D11 remains pending.

## Backend D09 verification — 14 November 2026

- Added an aware UTC `uploaded_at` timestamp to each private image session. Its returned `expires_at` is calculated once from that same timestamp plus the default 3,600-second TTL. It does not extend when the image is read, previewed, enhanced or exported. The API response still returns only the existing expiry field; no frontend contract changed.
- One ASGI test verifies upload-time bounds, exact 60-minute response/storage equality, fixed expiry through all four image operations, access at one microsecond before expiry, and a 410 response at the exact expiry boundary. All 94 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`.
- No dependencies, database or frontend behavior changed. D09 is complete; D10 remains pending.

## Backend D08 verification — 14 November 2026

- Confirmed there is no public/static image-file mount. Repository storage paths are limited to backend/.runtime; extended config checks explicitly reject frontend/public and frontend/dist. Original/normalized files stay private, while preview/export JPEG bytes are generated for authorized requests without persisting public derivatives.
- Added a small permission helper for each newly allocated run directory. POSIX uses mode 0700. On the current Python 3.11.9 Windows runtime, bundled whoami/icacls commands identify the service SID, remove inherited access and grant that account inheritable full control. Commands use argument arrays, bounded timeouts and suppressed permission-tool output. Existing configured roots/unrelated files are not modified. Permission failure removes the empty new run and aborts startup before pool creation.
- Three new tests verify real Windows owner-only ACLs on a run directory and inherited child directory/file access, injected permission-failure cleanup, and public/static/runtime/raw file URL rejection with or without a token. Authorized original-preview/preview/export return JPEGs and leave only original/normalized files on disk. Existing cross-session/invalid-token checks remain passing.
- All 93 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Windows ACL inspection passed; POSIX mode assertions are included but require execution on a POSIX host. No dependencies, database or frontend behavior changed. D08 is complete; D09 remains pending.

## Backend D07 verification — 14 November 2026

- Audited existing session generation: image IDs use `secrets.token_hex(16)`, tokens use a separate `secrets.token_urlsafe(32)` call, and only SHA-256 token hashes enter session records. File paths combine the generated ID with fixed internal filenames; submitted names are display metadata. No runtime code, dependencies or frontend behavior changed.
- Two added ASGI tests cover identical repeated uploads receiving separate ID/token values, expected encodings and token hash storage, plus traversal-style, POSIX absolute, Windows drive, UNC, colon and repeated filenames. Tests verify storage stays directly under the private root in generated ID directories, only fixed `original`/`normalized.png` files exist, and earlier upload bytes remain intact. Existing authentication tests also reject an image ID or another session's token as authorization. Randomness comes from the audited secrets calls; uniqueness samples are regression checks, not entropy measurements.
- All 90 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. No live database/browser rerun was needed. D07 is complete; D08 remains pending.

## Backend D06 verification — 14 November 2026

- Confirmed existing storage saves uploaded bytes directly as `original`, separately from `normalized.png`; preview, enhancement and export read the normalized working file. No runtime code, dependencies or frontend behavior changed.
- Added one ASGI regression test covering JPEG/PNG/WebP fixtures containing EXIF orientation, a description and an sRGB ICC profile. It checks exact original-byte preservation, retained original dimensions/metadata, physically separate original/normalized files, and byte-for-byte stability of both files after original-preview, edited preview, enhancement, export and a repeated original-preview. The edited preview differs while the repeated original-preview is identical.
- All 88 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. No live database/browser rerun was needed. D06 is complete; D07 remains pending.

## Backend D05 verification — 14 November 2026

- Confirmed upload normalization already applies EXIF orientation before saving the working PNG and creating metadata from its resulting dimensions. No runtime code, dependencies or frontend behavior changed.
- Strengthened the existing orientation smoke check with asymmetric quadrant fixtures and independently specified expected corner orders. The ASGI test covers JPEG/PNG/WebP with all eight EXIF orientations and no orientation tag (27 cases), including mirrored/transposed cases. It verifies reported width/height, exact normalized/preview/export dimensions, corner colours with JPEG tolerance, and absence of the orientation tag from working/derived images. Orientations 5–8 swap width and height. Existing transparency coverage was retained as a separate test.
- All 87 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. No live database/browser rerun was needed. D05 is complete; D06 remains pending.

## Backend D04 verification — 14 November 2026

- A direct normalization probe found malformed EXIF offsets being accepted with UserWarnings and truncated PNG/WebP EXIF producing an unhandled binary parsing error. Upload normalization now treats Pillow UserWarnings as errors within its existing warnings context and maps binary parsing errors to generic 422 invalid_image responses. Existing bomb warning/error handling still returns 413. No dependency or frontend behavior changes were needed.
- Four added ASGI tests cover both decompression-bomb paths before pixel loading using reduced test thresholds; warning-filter restoration; malformed EXIF offsets across JPEG/PNG/WebP and truncated EXIF headers in PNG/WebP; invalid ICC and valid sRGB profiles across all three formats; compressed PNG text/ICC exceeding the native per-chunk expansion limit; and aggregate text overflow with a reduced test-only limit. Existing valid EXIF orientation tests still pass. Rejected fixtures leave no sessions/files; tested warnings do not escape and a subsequent valid upload succeeds.
- All 86 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Production Pillow image/text thresholds remain enabled and unchanged; application byte/pixel/side limits still apply. No live database/browser rerun was needed. D04 is complete; D05 remains pending.

## Backend D03 verification — 14 November 2026

- Existing MAX_UPLOAD_BYTES (10,000,000), MAX_IMAGE_PIXELS (24,000,000) and MAX_IMAGE_SIDE (10,000) checks remain configurable. File bytes are bounded before decoding; dimensions are checked before full pixel loading. Added `app/uploads.py`, a small upload-only request receive guard used before multipart parsing. It rejects declared oversize immediately and counts streamed bytes independently of Content-Length, limiting multipart input to the file limit plus 65,536 bytes of overhead.
- Three new ASGI tests verify exact/default and reduced configured limits, including a real 10MB file, 24MP image and 10,000-pixel side. One-over bytes/pixels/width/height return 413 before decoding. Declared oversize is rejected without a body read; absent/understated lengths cannot bypass streaming enforcement. Partial multipart spool files close after rejection, no image sessions/files remain, and a subsequent valid upload succeeds.
- All 82 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. No dependency or frontend behavior changes were needed. The ASGI server still receives transport chunks before the application can count them; hosting request limits, request rates, execution time and aggregate disk budget remain phase H. D03 is complete; D04 remains pending.

## Backend D02 verification — 14 November 2026

- Audited unsupported, corrupt, animated and multi-frame rejection. The existing normalizer already satisfies these checks; no runtime code, dependencies or frontend behavior changed.
- Two added ASGI tests cover empty/non-image data, truncated JPEG/PNG/WebP headers, incomplete JPEG/WebP pixel payloads, PNG checksum corruption, animated GIFs and multipage TIFFs. Unsupported containers are tested with their real extensions and renamed as PNG. Together with D01's format matrix and animated PNG/WebP tests, these verify safe 415/422 responses with no retained sessions/files. A valid upload succeeds after corrupt-upload rejections.
- All 79 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. No live database/browser rerun was needed. D02 is complete; D03 and Studio API integration remain pending.

## Backend D01 verification — 14 November 2026

- Audited the existing upload normalizer: extension allowlist, detected-format match, single-frame requirement, container verification and full pixel decoding already run on the server before session creation. No runtime code, dependencies or frontend behavior changed.
- Four new ASGI tests upload real generated files directly with generic multipart MIME. They cover JPG/JPEG, PNG and WebP, uppercase extensions, usable previews, mismatched extensions, GIF/BMP/TIFF disguised as allowed formats, missing/unsupported extensions, a truncated JPEG that passes container verification, and animated two-frame PNG/WebP files. Invalid inputs return the expected 415/422 envelopes and leave no sessions/files.
- All 77 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. No database/browser rerun was needed. D01 is complete; D02 and Studio API integration remain pending.

## Backend/frontend C12 verification — 14 November 2026

- Added synthetic-setting OpenAPI export of the actual application, a limited TypeScript generator and frontend generate/check scripts. Generated models and all eight endpoint contracts include bodies/media types/statuses/headers; the existing frontend Adjustments type now aliases its generated counterpart. Integer bounds/security metadata remain in the full-schema fingerprint; TypeScript numeric types do not replace server validation.
- `npm run contracts:generate`, `npm run contracts:check`, all nine frontend unit tests and the TypeScript/Vite production build passed. No UI behavior was changed. The check normalizes source line endings, returns nonzero on missing/stale output and does not rewrite it.
- Three new backend tests cover resource-free actual schema export, file/JPEG/optional/empty-body mappings, constraint drift, non-mutating stale-file rejection and unsupported schema failures. All 73 backend tests passed. No browser or live database rerun was needed.
- The latest standard generator available through npm required TypeScript 5 and was incompatible with this repository's TypeScript 7. Its installation failed without retained manifest/lockfile dependency changes; the final implementation uses only existing tools. Generation uses synthetic settings, bypasses local dotenv and never opens application resources. Phase C is complete; D01 and full Studio integration remain pending.

## Backend C11 verification — 14 November 2026

- Added conditional CORS wrapping using the already-validated ALLOWED_ORIGINS setting. Explicit origins permit GET/POST/DELETE and Authorization/Content-Type, exposing X-Image-Revision and Content-Disposition. Cookie credentials remain disabled; empty origins return the existing application unchanged. No dependencies, local `.env`, database or frontend application changes were needed.
- Exported `application` outside FastAPI's server-error layer so even handled unexpected 500s carry allowed-origin CORS headers. The existing safe Uvicorn launcher now uses this export; the inner `app` remains available for OpenAPI tooling. An outer private cache guard keeps image preflight responses no-store as well.
- Three new tests verify actual preview/export/auth-error CORS headers, exact origin/Vary behavior, allowed GET/POST/DELETE preflights with bearer/JSON headers, rejected origins/methods/headers, no access grant to unlisted origins, disabled mode and generic 500 header coverage. All 70 backend tests passed.
- An actual exported-application ASGI check used process-only origin configuration and verified preflight plus unavailable-storage response headers. No credentials file changed. After adding a launcher-target assertion, all five logging/launcher tests also passed. Full browser/Studio integration remains phase G; the CORS checks here are ASGI-level.

## Backend C10 verification — 14 November 2026

- Existing handlers already emit revision/download headers and document them in OpenAPI. No application code, dependencies, database or frontend application changes were needed.
- Added a preview-header test for revision zero, a large integer and deliberately out-of-order requests across two sessions. Successful responses echo each submitted revision exactly, return JPEG and omit attachment disposition. Negative/float/string/boolean/null revisions return 422; wrong authorization returns 401. Those failures omit X-Image-Revision.
- Added export-header tests checking JPEG Content-Type, byte-matching Content-Length and bounded quoted ASCII attachment filenames. Injected filename metadata covers paths, punctuation/quotes, Unicode-only names, CR/LF and long stems; outputs contain only the safe JPEG filename pattern and no injected headers. Checked normal filename preservation and fallback behavior. Exports do not accidentally include preview revision headers.
- All 67 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`, including OpenAPI revision/disposition schema checks. Tests use generated images/private temporary sessions; no live database/browser rerun was needed. Cross-origin exposure remains C11 and Studio integration remains phase G.

## Backend C09 verification — 14 November 2026

- Audited existing private response headers. Successes/domain errors already used no-store, but a direct ASGI probe confirmed the framework's trailing-slash 307 redirect omitted it. Added `backend/app/middleware.py` with a small pure-ASGI header guard scoped to `/api/v1/images` and descendants, registered on the application. No dependencies, processing logic, database or frontend application changes were needed.
- Updated the image fixture to use the production error/cache handlers and added a routing-policy test: redirects, unknown paths and wrong methods retain no-store; a private response attempting public/max-age caching is overridden. All documented image responses also declare the no-store policy. Existing image tests assert the header for every tested success/failure, including 201/204, JPEG/JSON, validation/auth/capacity/expiry/server/storage errors.
- All 65 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. A separate actual-application ASGI check confirmed private redirect/error no-store and unchanged `/api/docs` caching headers. No live database rerun or browser cache simulation was needed.

## Backend C08 verification — 14 November 2026

- Audited 201/204/401/404/410/413/415/422/429/500 and service-unavailable behavior. Existing processing/status logic already met the requirement. Added shared OpenAPI 500 metadata at the API-router level so health/presets document the existing global server-error handler; image-specific descriptions remain intact. No dependencies, database or frontend application changes were needed.
- Three new ASGI tests cover lost in-memory session state after restart (404), wrong-token versus known-expired responses (401/410), empty-body deletion (204), actual 32-session capacity (429) and recovery after deletion, missing storage (503), and image dimension/format/decode failures. Injected a normalized-file write error after original bytes were written: the endpoint returned generic 500, removed partial files, retained no session and accepted a subsequent upload.
- Schema checks verify expected upload/session error statuses and 500/503 declarations on all eight operations. Existing tests cover upload success, byte-size rejection, malformed JSON/fields, busy processing, bearer challenges, database failures and generic unexpected exceptions.
- All 64 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Checks use generated images and isolated temporary resources; no live database or frontend rerun was needed. Scheduled expiry cleanup and the remaining checklist work remain pending.

## Backend C07 verification — 14 November 2026

- Added `backend/app/errors.py` with one typed error-response factory and safe handlers for request validation, HTTP exceptions and unexpected failures. Registered the handlers on the actual application; existing image route handling reuses them. Existing image/domain/database codes remain intact, while application routing and validation failures now share the same envelope. No dependencies, database or frontend application changes were needed.
- All error responses use no-store. HTTP handlers preserve applicable Allow/WWW-Authenticate/Retry-After headers and suppress arbitrary exception headers/details. Validation errors never serialize submitted inputs or error bodies. Unexpected server/response-validation failures return generic 500 and log only the fixed `request_failed` event.
- Added three ASGI tests covering invalid query/body fields and malformed JSON, routing 404/405, protocol headers, explicit HTTP errors, unexpected exceptions and invalid response data. They verify exact envelope keys and absence of synthetic private inputs/paths. The server-error test accounts for Starlette re-raising an exception after its handled 500 response is sent.
- All 61 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`, including existing image authorization/processing and database-error tests. Checks use generated images and simulated resources; no live database rerun was needed. C08 and frontend integration remain pending.

## Backend/frontend C06 verification — 14 November 2026

- Confirmed the three binary image endpoints already return direct JPEG bodies. Added an ASGI regression test checking Content-Type/Length, JPEG start/end markers, actual decoding and absence of redirect headers. All 58 backend tests passed; no backend runtime code or database changes were needed.
- Added only browser response-consumption helpers in `src/lib/imageResponse.ts`: JPEG response-to-object-URL with explicit display disposal, and blob-backed download initiation with anchor cleanup/deferred URL release. These consume an existing authorized Response; Studio/API fetch wiring remains phase G. No dependencies were added.
- All nine frontend unit tests passed, including four new checks for binary preservation, rejecting errors/non-JPEG responses before allocation, successful download cleanup and failed-initiation cleanup. `npm run build` passed after removing two pre-existing unused Home icon imports (`ArrowDown`, `ArrowRight`) reported by TypeScript. No Home behavior changed.
- `npx playwright test tests/e2e/image-response.spec.ts` passed in Chrome. The test imports the actual helper through Vite, decodes a generated JPEG object URL in an image element, verifies revocation, initiates a real browser download and reads complete JPEG bytes with the expected filename. It does not claim Studio/backend integration or cross-browser download verification.

## Backend C05 verification — 14 November 2026

- Audited the existing HTTP bearer dependency on all five image-specific operations and the per-session SHA-256 hash/constant-time comparison. No application code, dependencies, database or frontend application changes were needed.
- Added authorization regression coverage across original preview, edited preview, enhancement, export and deletion using valid request bodies. Missing/wrong tokens, another session's token, the image ID as a token, Basic credentials, empty/malformed Bearer headers and extra credential text all returned generic 401 with a Bearer challenge. Rendering/enhancement were never invoked; both sessions and their files remained present. The case-insensitive HTTP scheme also accepted a valid token.
- Supplying tokens through query parameters/cookies/JSON without the required header returned 401 and did not echo credentials. Checked stored session representations and original/normalized files contained no plaintext token. OpenAPI requires HTTPBearer for every image-specific operation and declares no token URL parameters; upload remains public. Existing valid-token workflow tests cover all protected operations.
- All 57 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Tests use generated images and isolated temporary sessions, not user photos or a live database. Browser integration remains pending.

## Backend C04 verification — 14 November 2026

- Existing upload `UploadFile` binding requires multipart `file`; preview/export use JSON Pydantic bodies. No application code, dependencies, database or frontend application changes were needed.
- Added transport regression tests: JSON/raw uploads, wrong multipart part name and a text part named `file` return 422 before normalization; missing multipart boundary returns generic 400. Preview/export reject missing/wrong Content-Type, form/multipart/text bodies and malformed JSON with generic 422 before rendering, then accept valid JSON with a charset parameter.
- OpenAPI advertises only multipart/form-data for upload, with required `file`, and application/json for preview/export. The initial file-schema test assumed `format: binary`; corrected it to match the installed FastAPI's generated string plus `contentMediaType: application/octet-stream` representation. Runtime behavior required no fix.
- All 55 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Tests use generated images/private temporary directories and no live database. C05 onward remains pending.

## Backend C03 verification — 14 November 2026

- Confirmed the existing `Adjustments` model already requires all six strict integer fields, forbids extras and uses the frontend control bounds. No application code, dependencies, database or frontend application changes were needed.
- Added two focused model tests covering Python/JSON input, preservation of all inclusive boundaries, rejection of fractional/whole-valued floats, numeric strings, booleans, nulls, missing/extra fields and out-of-range values. Generated JSON Schema requires exactly the six fields, declares integer minimum/maximum values and disallows extras.
- Added an ASGI regression test submitting invalid adjustment objects to both preview and export with a valid session token. Every case returned generic 422 and the renderer was never called. Tests use generated images/private temporary directories and no live database.
- All 53 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. C04 onward remains pending.

## Backend C02 verification — 14 November 2026

- Audited all eight existing endpoints and reused their request/success models. Added typed `ErrorDetail`/`ErrorResponse` for the image error path, constrained upload metadata to supported detected formats/positive dimensions/aware expiry, and described revision/token metadata. No dependencies, database schema/data, frontend application code or processing formulas changed.
- Documented implemented image errors at router/operation level, replacing the inaccurate automatic 422 validation schema with the actual generic envelope. Added binary JPEG schemas, no-body 204 deletion, cache/revision/download/authentication headers, operation summaries and bearer-token guidance. Existing health/preset contracts remain intact.
- All 50 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Contract coverage validates actual upload/enhancement/error JSON with the models, checks multipart and JSON request references, verifies JPEG media schemas contain no JSON body, confirms deletion has no content schema, and checks headers, format/dimension/expiry metadata and typed image 422 responses.
- No live database rerun was needed for contract/documentation changes; image workflow tests use real generated images and temporary storage. Broader common HTTP error handling, exhaustive status/security tests, frontend contract generation and browser integration remain scheduled work.

## Backend C01 verification — 14 November 2026

- Added the six remaining image endpoints, bringing the versioned API to eight operations. Added only their supporting image contracts, private session store and shared normalization/render/enhancement service, using existing dependencies. Lifespan owns the session store; shutdown clears its reference and removes private run files. Frontend application code and database schema were unchanged.
- All 49 backend tests passed. Six new ASGI tests exercise multipart upload, metadata, original/edited JPEG previews, neutral equivalence, revisions, repeatable enhancement, full-resolution export, deletion, bearer protection, invalid adjustments, expiry, immediate busy rejection, corrupt/unsupported/oversized input, all eight OpenAPI operations, JPEG/PNG/WebP orientation, transparent-white compositing, combined grayscale adjustments, and generic processing-error recovery. Export-quality handling and the current Pillow pixel API were then adjusted; all six image tests passed again.
- A separate actual-application ASGI smoke check exercised health/presets against development Neon and all six image operations with a generated PNG. It used a test-only 32-pixel preview limit in memory, verified full-resolution export, removed the image session, then confirmed pool/run-directory/session-store cleanup. No browser integration or production deployment was tested.
- This initial endpoint implementation does not complete all later C–F items: full OpenAPI error contracts, cross-origin integration, scheduled expiry/crash-leftover cleanup, comprehensive malformed/profile/bomb tests, ingress/disk limits and image-quality verification remain scheduled work. The upload byte check occurs after framework multipart spooling and before image decoding. No frontend integration claims are made.

## Backend B11 verification — 14 November 2026

- Used the existing isolated Neon `development` branch (`br-small-frost-b3yx6xrk`), verifying the exact direct endpoint and database before execution. No branch, database or other infrastructure was created; no main/production data was changed. No application code, dependencies or new test harness were needed.
- Ran the real migration runner twice; both reported zero pending migrations. Ran the real seed command function twice; the table retained exactly the five canonical definitions, and the ledger retained the two expected filenames/checksums. Initial creation of these migrations was verified in B05–B06; this check exercised the existing migrated development database.
- Within a force-rollback transaction, changed a preset and verified seeding repaired its fields. An injected SQL-level bound violation raised `CheckViolation`; its savepoint rolled back and preserved the pre-attempt state. The enclosing probe transaction rolled back completely.
- Copied the actual migration files into a temporary directory under ignored `.runtime`, then added a data-update migration followed by intentional division by zero. The real migration runner raised `DivisionByZero` and rolled back both the earlier update and new history entries. Modifying an applied migration in that temporary directory was rejected by checksum validation. All fixture files were removed.
- Final retrieval through the real application pool returned all five canonical presets in UI order. All 43 existing backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Phase B is verified; frontend integration and subsequent checklist phases remain pending.

## Backend B10 verification — 14 November 2026

- Reviewed existing Psycopg 3.3.9/pool 3.3.3 behavior, transaction boundaries, timeouts, health/preset errors and safe log formatting. Existing implementation covers this step; no application code, tests, dependencies, migrations or frontend application files were added or changed for B10. Updated documentation and checklist only.
- All 43 existing backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`, including pool/query failures, redacted responses, later-request recovery, rollback/release and resource cleanup.
- A separate actual-application ASGI check used the development pooled application role and a test-only one-connection pool. Injected synthetic `OperationalError` failures into `Connection.connect` in the real pool workers: health and presets returned generic no-store 503s. After removing the injection, both returned 200 on the same application/pool, using a real TLS connection to Neon.
- Closed only this test process's returned idle client connection, separately for each endpoint. Each stale client caused a generic 503, was discarded by the pool, and was replaced by a distinct TLS connection; subsequent requests succeeded. No Neon compute restart, backend-session termination or infrastructure change was used.
- Holding the only pool connection caused health/presets acquisition timeouts and generic 503s; both recovered after release. A real `SELECT pg_sleep(3)` inside the shared one-second statement scope raised `QueryCanceled` before three seconds, and subsequent health/preset requests succeeded. Test-only request/statement limits were shortened in memory; connection-attempt limits and local `.env` were preserved.
- Captured application and driver logs contained fixed event categories and excluded the actual connection URL/password, injected private details and tracebacks. The pool remained open through the scenarios, then closed at shutdown and removed its owned run directory. No persistent database data changed. This validates controlled client failures and recovery, not a real Neon-wide outage or every possible network stall.

## Backend B09 verification — 14 November 2026

- Added `GET /api/v1/presets` and a separate database reader. The reader selects nine required fields for the five stable built-in IDs, orders by their studio sequence in SQL, borrows from the existing application pool with its transaction timeout, and validates every definition with `Preset`. No seed values are used as runtime fallback. The endpoint exposes a typed JSON array and no write methods.
- Shared the existing service-unavailable envelope between readiness and presets. Pool/query failures and incomplete/invalid definitions return a generic 503 with `Cache-Control: no-store`; success uses the same cache policy. A fixed `presets_unavailable` event excludes exception details. No dependencies, migrations or frontend application code changed.
- All 43 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Six new tests cover complete database-derived values/order, pool failures and subsequent recovery, query cancellation and connection release, missing/invalid definitions, rejected POST/PUT/PATCH/DELETE methods, and typed OpenAPI 200/503 responses. Existing health/logging tests passed after the shared-schema move.
- A separate live check ran the actual application lifespan and ASGI endpoint against the development pooled application role over TLS. Two requests returned 200, no-store headers and the exact five canonical definitions in UI order. The role still lacked INSERT/UPDATE/DELETE privileges. OpenAPI contained both outcomes; shutdown closed the pool and removed the run directory. This was an ASGI/backend check, not browser or frontend integration. No database data was changed.

## Backend B08 verification — 14 November 2026

- Added `backend/app/schemas/presets.py` with a strict, frozen `Preset` model containing all nine required fields, six integer ranges matching PostgreSQL, and forbidden extra fields. The seed path validates all rows before opening its write cursor and catches validation/tuple-shape failures through the generic CLI error path. No dependencies, migrations or frontend application code changed.
- All 37 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. New coverage checks all seed values and JSON round trips, inclusive bounds, out-of-range values, float/string/boolean/null rejection, missing/extra fields, strict text fields, and invalid/incomplete/oversized final seed rows rejected before any upsert. CLI tests also verify private Pydantic error details are excluded. After simplifying the JSON test construction, the three preset schema tests were rerun and passed.
- The actual validated seed CLI ran twice successfully against the existing development branch. A live pooled application-role query over TLS returned exactly five rows; each passed the Pydantic model and preserved every canonical value. Connections closed after verification. The main/default branch was not seeded. The public retrieval endpoint and its response integration remain B09.

## Backend B07 verification — 14 November 2026

- Added `backend/app/db/seed.py` with the five version-controlled preset definitions and an explicit `python -m app.db.seed` command. Parameterized upserts update every definition field by `preset_id` in one transaction using the direct owner connection and configured timeouts. Missing/pooled direct URLs fail before opening a connection; no fallback uses the application role. CLI failures return 1 without raw private errors. No dependencies, migrations or frontend application code changed.
- Imported the actual frontend TypeScript definitions with Node and compared all IDs, names, descriptions and six adjustment values against the backend seed tuples; they matched exactly. Ran the actual seed CLI twice on the development branch; both succeeded and the database contained exactly five complete unique definitions.
- Separate live transaction checks verified all eight non-key fields are repaired by an upsert, an unrelated test row is preserved, and an invalid final seed row rolls back earlier updates in the batch. These temporary changes were rolled back; the committed database retains exactly the five canonical presets. The main/default branch was not seeded.
- The pooled application role read all five exact definitions over TLS and still lacked INSERT/UPDATE/DELETE privileges. All 33 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`, including two new seed command tests covering URL safeguards and redacted/nonzero database failures. Pydantic preset validation and the retrieval API remain B08–B09.

## Backend B06 verification — 14 November 2026

- Added `backend/migrations/002_presets.sql`: nine columns matching the checklist, a text primary key, required text/integer values, and six numeric-range constraints matching `frontend/src/lib/editor.ts`. Granted only SELECT on this table to `lumalab_app`. No runtime application logic, frontend code or dependencies changed.
- Applied migration 002 through `python -m app.db.migrate` on the existing development branch's direct owner connection. The next invocation reported zero migrations, and both ledger checksums matched the local files. The default/main branch was not migrated.
- Live PostgreSQL verification confirmed exact column order/types and not-null attributes. Within a rolled-back transaction, all 12 lower/upper boundary values were accepted; all 12 immediately out-of-range values raised the corresponding check violation. Nulls in each of the nine columns were rejected, and a duplicate ID raised the primary-key violation. No test rows remain; the table is empty.
- The actual pooled application connection over TLS could SELECT from presets. Privilege checks confirmed INSERT, UPDATE, DELETE and TRUNCATE are false. All 31 existing backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Constraint checks were separate live verification, not new mocked unit tests. Seeding remains B07.

## Backend B05 verification — 14 November 2026

- Added `backend/app/db/migrate.py`, migration `001_migration_history.sql`, and migration-authoring instructions. Uses the existing Psycopg dependency, requires the direct URL, and never runs automatically at API startup. No frontend application code or dependency files changed.
- The runner validates ordered filenames and normalized SHA-256 checksums, checks the applied history is a matching prefix, and applies all pending SQL/history entries in one transaction under an advisory lock. CLI failures return 1 without raw database/configuration errors or tracebacks.
- All 31 backend tests passed with `uv run --locked --offline --cache-dir .uv-cache python -m unittest discover -s tests -q`. Four new tests cover stable checksums across line endings, filename/order validation, missing/pooled migration URLs, and redacted CLI failures. Existing Windows asynchronous checks ran outside the sandbox.
- Live checks used the existing isolated development branch's direct owner connection over TLS. The actual command initialized the history table and a repeat run reported zero migrations. The ledger matched the SQL checksum. Temporary test migrations created a probe table followed by intentional division by zero; the batch rolled back both the table and its history entries. An edited applied file and a simultaneous advisory lock holder were rejected. A final run was a no-op. Temporary fixture files were removed. No presets table or seed data was created; the default/main branch was not migrated.
- The frontend/backend folder move had left backend secrets and bytecode tracked. Added backend-local ignore rules and removed `.env` plus generated bytecode from the Git index, preserving their local copies. This does not remove credentials from earlier commits; rotation is still required. No history rewrite or credential rotation was performed.
- Verified the local credential file is preserved, ignored and absent from the index. A scan found neither database URL nor password in tracked/nonignored working files. Staged and unstaged whitespace checks passed.

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
