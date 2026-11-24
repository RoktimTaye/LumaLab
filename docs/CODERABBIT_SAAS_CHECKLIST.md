# LumaLab: reusable SaaS security and reliability review checklist

Version: 1.0 | Repository inspected: 2026-11-25 | Owner: release maintainer

Use this baseline with [FEATURE_TEST_CHECKLIST.md](FEATURE_TEST_CHECKLIST.md) for every software update. These are review requirements, not a report of confirmed vulnerabilities. No checklist or AI reviewer can guarantee finding every bug or attack. Combine code review with automated tests, dependency scanning, staging load/failure tests, and independent security testing for major releases.

## 1. How to use this on every update

1. Copy the feature template into the PR description or a release-specific record. Fill in the base/head commits, changed behavior, affected modules, and risks.
2. Review every changed file and trace affected callers, schemas, storage, background tasks, database operations, UI consumers, and deployment settings. A small diff can break an unchanged component.
3. Apply all baseline sections. Record individual control IDs as PASS, FAIL, NOT TESTED, or N/A with evidence. N/A requires a reason; an unchecked box is not a pass. Use conditional sections when a feature activates them.
4. Ask CodeRabbit to apply this document and the completed feature checklist. Use the prompt below. The root `.coderabbit.yaml` registers these documents as guidelines and adds focused path instructions.
5. Run the applicable checks in section 19. CodeRabbit guidance does not execute these checks or enforce a merge gate by itself.
6. Resolve blocking findings, add regression evidence, and review the final commit. Repeat affected checks after fixes. Archive the results with the release.
7. When a real bug escapes review, add a specific case and regression test. Retain stable control IDs; append new IDs instead of renumbering existing ones.

### Copy/paste review prompt

```text
Review this LumaLab update using docs/CODERABBIT_SAAS_CHECKLIST.md and the
completed docs/FEATURE_TEST_CHECKLIST.md instance in this PR. Record the exact
base and head commits. Trace changed code through its affected end-to-end flow.
Prioritize private-photo access, hostile uploads, resource exhaustion, render
correctness, concurrency, SQL safety, frontend races, deployment and recovery.

For each actionable issue give: control ID, severity, exact file/line,
reachable trigger, impact, evidence, concrete fix, and a regression test.
Separate newly introduced issues from pre-existing issues reached by this change.
Do not treat desired future capabilities as existing vulnerabilities.
Do not claim tests, load tests, deployment checks, scans or attacks were run
unless execution evidence is available. Mark uncertain issues as hypotheses
with the verification needed. Report uncovered controls as NOT TESTED.

Return: scope and risk summary; issues ordered by severity; coverage table
(control ID/status/evidence); missing runtime evidence; release blockers.
Assess whether the feature and its failure paths preserve existing workflows.
Do not claim the application is secure merely because no issue was found.
```

For hosted PR reviews, paste the prompt in a CodeRabbit-addressed PR comment. Confirm that CodeRabbit actually loaded the guideline files and reviewed the intended final commit. Reviews ordinarily focus on changes: a whole-repository baseline audit needs an explicitly defined full-repository scope; a full PR review is not proof that every unchanged file was audited. CLI users may pass this document as review context using the CLI's supported configuration/context option; verify options with the installed CLI's help.

## 2. Project-specific architecture and invariants

Current product: React/TypeScript browser photo editor; FastAPI/Python API; Pillow, NumPy and OpenCV processing; Neon PostgreSQL preset catalogue; private process-local temporary files. Auto Enhance uses deterministic photographic analysis, not a trained or generative model. Accounts, payments, durable libraries, team tenancy and public sharing are outside current scope.

Observed flow:

```text
Untrusted browser file + filename + edit JSON
  -> API request admission / multipart bounds
  -> format, animation, size and decoded dimension validation
  -> EXIF orientation + sRGB normalization + white alpha composition
  -> private original + normalized.png + preview.png + analysis.png
  -> image ID and bearer token (server stores token hash)
  -> authorized original-preview / preview / enhance / export / delete
  -> normalized-source rendering with complete versioned editing state
  -> no-store image response -> browser Blob -> download / URL revocation
  -> fixed expiry / deletion / shutdown / stale-run cleanup

Separate flow: browser -> presets API -> bounded PostgreSQL pool -> catalogue
```

Check the actual implementation each release; this snapshot can become stale:

| Invariant / default | Current owner |
| --- | --- |
| Upload 10,000,000 bytes; at most 24,000,000 pixels; side at most 10,000 | `backend/app/config.py`, `uploads.py`, `services/images.py`; frontend validation must agree |
| Still JPEG/PNG/WebP input; full-resolution JPEG output | `services/images.py`, `schemas/images.py` |
| Fixed 3,600-second TTL; cleanup interval 300 seconds | `config.py`, `storage/images.py`, `lifespan.py` |
| 32 sessions; 1,000,000,000-byte configured temporary storage budget | `storage/images.py`, `config.py` |
| 12 uploads/minute/client; 1,024 remembered client buckets | `rate_limit.py`, `config.py` |
| One processing slot for upload/enhance/export; two preview slots | `routes/images.py`, `storage/images.py` |
| One backend worker and one replica; process-local sessions and limits | `deploy.py`, `README.md` |
| PostgreSQL presets currently total 35 in defined order | `db/presets.py`, catalogue, migrations |

These values are implementation defaults, not validated production capacity targets. Runtime overrides, temporary write amplification, active threads, and native-library allocations must be measured.

## 3. Scope, threat model, and data flow

- [ ] ARCH-01: Inventory all public routes, methods, content types, static paths, internal endpoints and external calls. Identify new bypass paths and obsolete API versions.
- [ ] ARCH-02: Identify assets: original photos, metadata, tokens, editing recipes, database credentials, migrations, release artifacts and service availability. Map each trust boundary and controller responsible for it.
- [ ] ARCH-03: Trace each input from source to validation to processing to storage to response to deletion. Validate at the server boundary even when the browser validates it.
- [ ] ARCH-04: Document abuse by anonymous clients, stolen-token holders, hostile uploads, distributed bots, malicious dependencies, compromised operators and future tenants. Rank by reachability, impact and expected resource cost.
- [ ] ARCH-05: Preserve source immutability and isolate session state. No request may select a filesystem path, another session's source, arbitrary SQL identifier, code, or server-side execution target.
- [ ] ARCH-06: Reconcile documentation with actual contracts and configuration. Explicitly decide whether a change alters retention, image quality, data exposure, deployment topology or cost.

## 4. Authorization and temporary-session security

- [ ] AUTH-01: For original-preview, preview, enhance, export, detail export, and delete, require the token belonging to the exact image. Exercise two sessions A/B: A's token must never authorize B. Image-ID unpredictability alone is insufficient.
- [ ] AUTH-02: Test absent, malformed, empty, incorrect, very long, reused, expired and deleted-session tokens. Confirm stable documented 401/404/410 behavior without revealing private data in errors.
- [ ] AUTH-03: Generate IDs/tokens with cryptographic randomness; retain only token hashes server-side; compare securely. No debug token, shared fallback token or predictable seed.
- [ ] AUTH-04: Keep tokens in Authorization headers and browser memory. No tokens in query strings, URLs, filenames, analytics, logs, crash reports, persistent browser storage or exported images.
- [ ] AUTH-05: Enforce fixed expiry on every protected operation; editing cannot silently refresh it. Define behavior for work admitted before expiry that completes afterward and test it.
- [ ] AUTH-06: Reject new readers once deletion/expiry retires a session. Prevent double deletion, token/session confusion and accessing files while cleanup removes them.
- [ ] AUTH-07: Prove original/normalized/preview/analysis files cannot be retrieved via static serving, guessed URLs, directory listings, path traversal, alternate methods, or CDN cache.
- [ ] AUTH-08: Anonymous upload remains intentional. Define per-client and global abuse controls; do not mistake CORS for authentication or require nonexistent account flows.

## 5. Hostile uploads, parser safety, and filesystem attacks

- [ ] FILE-01: Allow only supported extensions AND successfully decoded matching formats. Test forged MIME types, double extensions, uppercase names, missing suffixes, SVG/HTML/PDF/ZIP renamed as photos and polyglots. Never execute or directly serve retained original bytes.
- [ ] FILE-02: Reject animations, including APNG and animated WebP; test deceptive first frames and corrupt frame counts.
- [ ] FILE-03: Enforce byte bounds while receiving, before framework multipart spooling and decoder allocation. Test missing/incorrect Content-Length, chunked bodies, duplicate file parts, many form fields, large headers and excessive multipart overhead.
- [ ] FILE-04: Bound decoded width, height, total pixels, metadata and decoder work independently of compressed size. Reject decompression bombs before full decode; handle decoder warnings as intended errors.
- [ ] FILE-05: Exercise truncated, empty, corrupt, progressive and adversarial images; malformed ICC/EXIF data; unsupported modes; extreme aspect ratios; and one-pixel dimensions. A bad file must not take down subsequent valid requests.
- [ ] FILE-06: Sanitize filenames for display and Content-Disposition; test CR/LF, nulls, Unicode, separators, `..`, Windows drive/UNC names and alternate data streams. Use server-generated storage names.
- [ ] FILE-07: Resolve filesystem targets under a dedicated private run directory. Reject symlinks/junction substitutions and unexpected paths before recursive cleanup; never remove a shared parent, another active run or repository data.
- [ ] FILE-08: Check Linux permissions and Windows ACL failure handling. Fail safely when privacy cannot be established; no public webroot, world-readable directory or executable upload directory.
- [ ] FILE-09: Account for original plus normalized PNG plus previews plus scratch allocations. Reserve disk headroom before writes or otherwise prove pre-admission bounds; a quota checked after writing must not exhaust the volume.
- [ ] FILE-10: Clean partial writes on decode/save/register failures, disconnects and disk-full errors. Session count and byte accounting remain correct after rollback and retries.
- [ ] FILE-11: Re-encode outputs from validated pixels; strip original GPS/EXIF and unwanted metadata from working/output files. Retained original bytes still contain private metadata and need the same protection and deletion guarantees as photos.
- [ ] FILE-12: Maintain decoder/native-library patching and adversarial corpus testing. For any future public sharing or external file distribution, reassess sandboxing, malware scanning and abuse reporting before launch; do not send private photos to a scanner without an approved data policy.

## 6. API validation, injection, and web attacks

- [ ] API-01: Validate every edit field server-side: type, finite numeric range, integer requirements, allowed enums, nesting depth, maximum arrays, unknown properties and supported recipe versions. Test NaN/infinity, booleans-as-numbers, nulls, huge integers and type coercion.
- [ ] API-02: Bound JSON request bodies, headers and path/query strings as well as upload bodies. Deep JSON and huge curve/recipe payloads must be rejected without expensive processing.
- [ ] API-03: Treat image IDs as lookup keys only. Prevent path traversal, encoded traversal, SQL injection, header injection, log injection and command injection at every input sink.
- [ ] API-04: Never evaluate user data with eval/exec, dynamic imports, unsafe YAML/pickle loading, templates-as-code, or shell interpolation. Subprocesses use fixed executables, argument arrays and timeouts.
- [ ] API-05: Escape filenames, preset text, server messages and future user content in React. Audit dangerous HTML sinks, href/src schemes and DOM injection. Test stored and reflected XSS paths, not only form inputs.
- [ ] API-06: Restrict CORS to intended explicit origins, methods and headers; exercise rejected origins, preflights and errors. Expose revision/download headers where required. Review browser credential behavior.
- [ ] API-07: If cookie authentication is introduced, require a documented CSRF defense and suitable cookie attributes. Today header-token authorization still needs XSS protection, while anonymous uploads need abuse controls.
- [ ] API-08: Enforce HTTPS and appropriate edge TLS settings; review CSP, frame protection, nosniff, referrer policy, permissions policy and HSTS for the actual deployment. Validate error and preflight responses too.
- [ ] API-09: Configure trusted proxy peers precisely; test forged Forwarded/X-Forwarded-For, IPv4/IPv6 variants, direct-backend access and Host headers. Edge/backend parsing agreement must prevent request smuggling and routing bypasses.
- [ ] API-10: Return bounded, consistent errors for invalid requests. No SQL text, credentials, filesystem paths, photos, stack traces, internal hosts or token input in responses.
- [ ] API-11: Deny unintended methods and debug/admin/test endpoints; keep API misses as API errors rather than HTML SPA success responses. Review docs/OpenAPI exposure deliberately.
- [ ] API-12: If remote URL import/webhooks are added, prevent SSRF: validate scheme/destination after DNS resolution and every redirect; deny internal, loopback, link-local and metadata destinations; cap bytes/time/redirects and restrict egress. N/A requires proof there is no user-controlled server fetch.
- [ ] API-13: If XML, archives, GraphQL or WebSockets are added, activate appropriate entity, traversal, expansion, query-cost, connection and message limits before exposure. Do not invent these interfaces in the current app.

## 7. PostgreSQL, SQL injection, and durable-data correctness

- [ ] DB-01: Bind every untrusted value with psycopg parameters. Never use f-strings, concatenation, `%` formatting or string interpolation for user-controlled SQL. Dynamic identifiers use safe composition plus an allowlist; parameter binding does not quote identifiers.
- [ ] DB-02: Test preset IDs and future filters with quotes, Unicode, comment syntax, malformed values and oversized inputs. Assert no SQL structure changes or unintended data access; time-bound injection tests in an isolated database.
- [ ] DB-03: Use least-privilege runtime roles and separate migration credentials. Verify actual grants; a separate environment variable alone does not prove least privilege. Runtime must not obtain DDL/owner access unnecessarily.
- [ ] DB-04: Validate TLS mode and certificate/hostname verification against the database threat model. `sslmode=require` encrypts transport but is not a substitute for verified server identity where that is required.
- [ ] DB-05: Bound pool size, waiting clients, acquisition time, connection time, statements and locks. Check every endpoint uses the intended connection wrapper and cannot hold connections during image rendering.
- [ ] DB-06: Prove transactions commit/rollback and return clean connections on every exception/cancellation. Retry only safe operations with bounded backoff; never replay a non-idempotent write blindly.
- [ ] DB-07: Use database constraints for durable invariants: keys, uniqueness, ranges, ordering and valid catalogue entries. Reconcile seed JSON, schema and frontend assumptions; test missing, duplicate, malformed and reordered presets.
- [ ] DB-08: Review migrations for forward/backward compatibility, advisory locking, partial failure, checksums and concurrent deploys. Test upgrade from the previous release and restore/roll-forward; document destructive steps explicitly.
- [ ] DB-09: Require EXPLAIN and representative data for new costly queries. Prevent N+1 calls, unnecessary full scans, unbounded fetches and inappropriate indexes. Measure under the deployed Neon pooling/cold-start behavior.
- [ ] DB-10: Exercise DB unavailable, slow, stale-schema and exhausted-pool conditions. Health/error reporting must remain bounded and redact DSNs; decide which existing image operations can continue during catalogue failure.
- [ ] DB-11: Back up durable database data and test restoration. Current photos are temporary files and must not be represented as recoverable from PostgreSQL backups.

## 8. Rate limiting, quotas, DoS and cost controls

- [ ] LIMIT-01: Inventory route-specific request rates, bursts, active work, body sizes, response bandwidth, sessions, disk, CPU, memory, file descriptors and execution deadlines. Concurrency limits alone do not prevent sustained expensive requests.
- [ ] LIMIT-02: Apply upload admission before parsing/spooling/decoding; apply protected-operation admission without letting invalid-token traffic monopolize scarce render slots. Test abuse while legitimate users work.
- [ ] LIMIT-03: Test current 12/minute boundary, exact window rollover, concurrent same-client calls, 1,024-bucket exhaustion and recovery. New identities must not evict live buckets to reset limits.
- [ ] LIMIT-04: Validate client identity through the real trusted proxy chain. Address NAT fairness, IPv6 normalization, bot address rotation and spoofed headers. Anonymous limits require global protection as well as per-IP rules.
- [ ] LIMIT-05: Apply cost-aware protection to preview, original-preview, Auto Enhance, export and 100% detail (which performs a full export). Add safeguards for expensive unauthenticated endpoints, health checks and repeated failed requests.
- [ ] LIMIT-06: Check aggregate work: one upload/enhance/export plus two previews can execute together. Measure peak RSS and CPU for this combination, not one route at a time; include native thread oversubscription.
- [ ] LIMIT-07: Test session count and byte limits just below/at/above boundaries, parallel requests, failed writes and delayed cleanup. Reject overload with controlled 429/503 behavior and correct optional Retry-After semantics.
- [ ] LIMIT-08: Bound inbound request duration, slow uploads, idle connections and response writes at server/edge. A held upload permit must not indefinitely prevent other processing.
- [ ] LIMIT-09: Confirm aborted browser requests do not imply server computation stopped. Bound remaining work; release permits only when protected work really completes or is safely terminated.
- [ ] LIMIT-10: Place internet-scale DDoS, connection/bandwidth limits and bot controls at an appropriate edge. Restrict origin bypass. Application rate limits cannot absorb network saturation.
- [ ] LIMIT-11: Define behavior if a limiter/queue/cache backend fails. Avoid accidental unlimited admission, retry storms and permanent denial; alert on degraded protection.
- [ ] LIMIT-12: Set provider spend alerts and, where supported, hard budgets; monitor storage/egress/render costs. Future paid integrations require per-account quotas and replay-safe usage accounting.

## 9. Concurrency, cleanup and server-crash resilience

- [ ] LIFE-01: Release semaphores, readers, locks, file handles, images, buffers and database connections on success, exceptions, cancellation and timeout. Inject failures at each acquisition/write/render stage.
- [ ] LIFE-02: Race preview/export/enhance against delete, expiry and shutdown on the same session. No use-after-delete, deadlock, negative reader count, leaked lock or new reader after retirement.
- [ ] LIFE-03: Keep operations on other sessions responsive while deletion waits. Check lock ordering, waiting conditions and bounded shutdown when an active reader stalls.
- [ ] LIFE-04: Ensure CPU/native image work and synchronous DB calls do not block the ASGI event loop. Bound threadpool saturation; test whether health probes and cleanup still run under load.
- [ ] LIFE-05: Exercise disk full, read-only storage, permission loss, missing files, failed delete, encoder exceptions and temporary directory replacement. Never acknowledge deletion as complete when private files remain without a tracked recovery path.
- [ ] LIFE-06: Verify scheduled expiry cleanup keeps running after one failure; measure actual retention delay. Logical access expiry and physical erasure time are separate properties.
- [ ] LIFE-07: Test graceful SIGTERM and forced kill/OOM/restart. Identify orphaned directories and verify safe startup reclamation; do not assume graceful cleanup runs after a crash.
- [ ] LIFE-08: Protect active run directories from stale cleanup. The current one-replica restriction must be preserved or replaced with ownership/liveness coordination before shared storage or rolling overlap.
- [ ] LIFE-09: Do not scale workers/replicas until session routing, storage, quotas, expiry and locks have a tested shared-state design. Sticky routing alone does not provide durability, global quotas or failover.
- [ ] LIFE-10: Catch recoverable failures with useful redacted diagnostics. Native decoder crashes and OOM require process/container isolation and restart handling; Python exception handlers cannot guarantee containment.
- [ ] LIFE-11: Verify health/liveness/readiness semantics, probe time budgets, startup failures and restart backoff. Dependency failures must not create an endless destructive restart loop.
- [ ] LIFE-12: Explain restart/session-loss behavior to users and define a supported release/drain policy. Durable editing requires a new storage design, not an undocumented extension of temporary sessions.

## 10. Image-processing correctness and numerical safety

- [ ] IMG-01: Render from the normalized immutable source on every edit. Repeated application of the same complete state must not accumulate JPEG loss or reapply enhancements.
- [ ] IMG-02: Preview, detail and export use the same recipe, curves and operation ordering. Define tolerances for downsampling/JPEG differences; do not demand byte-identical previews at different sizes.
- [ ] IMG-03: Test EXIF orientations, CMYK/grayscale/palette/alpha inputs and valid/invalid ICC profiles. Ensure sRGB conversion, white alpha composition and post-orientation dimensions match the UI.
- [ ] IMG-04: Validate crop coordinates against normalized source dimensions before allocation. Test edges, one-pixel crops, negative/zero/huge rectangles, crop after rotation/flip/straighten and preview/source scaling.
- [ ] IMG-05: Bound curve point counts; reject malformed/duplicate/unsorted x values as required by the contract; test endpoints, channel composition, interpolation, neutral identity and resets.
- [ ] IMG-06: Exercise all control minima/maxima, combined extremes, rotation and flips. No NaNs, overflow, division by zero, invalid indexing, unexpectedly enlarged canvases or silent wraparound.
- [ ] IMG-07: Verify neutral edits, reset and preset application produce a complete state, including newly added controls. Partial old presets must not retain previous photo/edit settings accidentally.
- [ ] IMG-08: Validate enhancement recipe versions and regional-map dimensions/ranges. Client-supplied recipes are untrusted even when originally created by the server.
- [ ] IMG-09: Test enhancement strength endpoints, crop anchoring, source-detail sampling, dark/bright/flat/noisy/saturated photos and tiny images. Findings text must agree with applied changes; failures preserve existing edits.
- [ ] IMG-10: Use representative portraits, skies, foliage, gradients, monochrome and low-light fixtures to detect clipping, banding, color shifts, halos, oversharpening and texture loss. Human quality review complements numerical tests.
- [ ] IMG-11: For tiled optimization, compare against a trusted reference with declared tolerance: tile seams, overlap/halo handling, global means, rounding and borders must remain correct.
- [ ] IMG-12: Verify actual export dimensions after transforms/crop, JPEG quality, safe filename, image MIME type and metadata. UI export summaries must agree with output bytes.

## 11. Browser state, races and user-data safety

- [ ] UI-01: Track image identity AND edit revision for all asynchronous results. Delay/reorder responses while switching A -> B, changing presets, resetting, undoing, enhancing, cropping and exporting. Stale results must not overwrite current work.
- [ ] UI-02: Capture a complete immutable edit snapshot for each request. Invalidate preview-ready/export/detail state whenever any rendering input changes, including enhancement strength, curves and geometry.
- [ ] UI-03: Check revision response headers and cancellation handling; reject missing/mismatched revisions as specified. An aborted operation must not show a success message or download a stale image.
- [ ] UI-04: Handle upload replacement after the server created a session but the UI abandoned it. Delete known abandoned sessions best-effort; server TTL remains the fallback when the token was never received.
- [ ] UI-05: Revoke Blob URLs, stop timers/workers/listeners and abort obsolete requests on replacement, unmount and modal close. Do not revoke a download URL before supported browsers consume it.
- [ ] UI-06: Bound undo history, decoded images, histogram work, query cache and detail previews. No photos or bearer tokens retained by service workers, browser persistence, analytics or query-devtools exports.
- [ ] UI-07: Handle offline, timeout, 401/404/410, 413/415/422, 429/503 and malformed/non-JSON/non-image responses. Show actionable bounded retry behavior; honor Retry-After where available and avoid automatic non-idempotent upload retries.
- [ ] UI-08: Prevent double-click duplicate work and infinite refetch/retry loops. Rapid sliders should coalesce expensive requests while preserving the last committed state.
- [ ] UI-09: Undo/redo restores the complete state in the correct photo; editing after undo truncates redo history appropriately. Keyboard and pointer paths must agree.
- [ ] UI-10: Confirm Home demo approximations remain distinct from real backend editing; test session expiry and restart messaging without implying durable saving.
- [ ] UI-11: Test current Chromium, Firefox and WebKit plus representative low-memory/mobile devices. Include download behavior, image decode failures, back/forward navigation, refresh and tab closure.
- [ ] UI-12: Verify keyboard navigation, focus restoration, curve/crop controls, screen-reader status/errors, contrast, touch targets, reduced motion and narrow layouts. Accessibility failures can block task completion.

## 12. Speed, memory and optimization

- [ ] PERF-01: Record hardware/container size, network, image corpus, exact commits, concurrency, cold/warm runs and repetitions. Publish p50/p95/p99 where sample size supports them, peak RSS, CPU, throughput and rejection/error rate.
- [ ] PERF-02: Set approved latency and resource budgets before release. Cover upload-to-ready, slider feedback, preview, enhance, detail, export and health latency; a single successful large-image test is not a capacity claim.
- [ ] PERF-03: Benchmark 12 MP, maximum supported 24 MP, long-thin images, high-entropy PNG/WebP and worst combined edits. A small compressed file can still be expensive to decode.
- [ ] PERF-04: Load-test the real route mixture at expected concurrency, then overload it; demonstrate bounded memory/queues, fair rejection and recovery. Include one expensive full-resolution operation plus concurrent previews.
- [ ] PERF-05: Soak-test repeated upload/edit/detail/export/delete cycles across multiple TTL windows. RSS, open descriptors, threads, temporary bytes, sessions and limiter state must stabilize.
- [ ] PERF-06: Profile before optimizing. Check full-frame float arrays, redundant copies/decodes, oversized intermediates, OpenCV thread count, Python/native contention and compression cost.
- [ ] PERF-07: Cache only where privacy and invalidation are correct. Any render-cache key includes session/owner, full edit state, crop, curves, recipe version, output size/quality and processing version; no cross-session disclosure.
- [ ] PERF-08: Browser measurements include long tasks, input responsiveness, canvas/histogram cost, image decode, heap and request count. Move heavy work or reduce sampling when measurements justify it.
- [ ] PERF-09: Reject an optimization that changes image semantics, leaks metadata, bypasses validation, weakens limits or hides errors. Retain quality comparisons and a rollback path.

## 13. Privacy, observability and incident response

- [ ] OPS-01: Cover all private success/error responses with no-store; inspect edge/CDN behavior, Vary and service-worker rules. Public assets may cache, private images/tokens must not.
- [ ] OPS-02: Verify redaction in app, proxy, platform, database and exception logs. Do not record bearer headers, DSNs, photo bytes, EXIF/GPS, or sensitive filenames by default.
- [ ] OPS-03: Preserve diagnostic value with bounded structured events, safe request IDs, route/status, latency, capacity rejection reason and failure category. Test log injection and high-volume log abuse.
- [ ] OPS-04: Monitor active sessions, temp bytes, cleanup failures, oldest retained file, processing occupancy, RSS, CPU, disk free, pool waits, 429/5xx, restarts and p95 latency. Use bounded metric labels; never label by token/photo ID.
- [ ] OPS-05: Define thresholds, alert owner, escalation and response steps for privacy leaks, authorization bypass, rising OOMs, disk exhaustion, stuck cleanup, DB failure and spend spikes. Validate alert delivery in staging.
- [ ] OPS-06: Document retention for originals/working files, logs, backups, crash dumps and diagnostics. A 60-minute access TTL does not promise immediate physical deletion or erase provider snapshots.
- [ ] OPS-07: Prepare safe containment: stop affected operations, revoke affected capabilities by retiring sessions where necessary, patch, validate, restore and communicate. Do not preserve private photos in incident artifacts by default.
- [ ] OPS-08: Check privacy notice, consent/data transfers, subprocessors, deletion commitments and contractual requirements against actual use and markets. Obtain qualified review where obligations apply; this checklist is not a compliance certification.

## 14. Dependencies, CI/CD and production configuration

- [ ] DEP-01: Lock Python/npm dependencies and build deterministically. Scan direct/transitive Python, JavaScript, OS and native image libraries; verify exploitability and patch status, not only a clean top-level manifest.
- [ ] DEP-02: Scan repository history and build artifacts for secrets, `.env`, database URLs, private photos and test credentials. On leakage, revoke/rotate and investigate; deleting a committed secret alone is insufficient.
- [ ] DEP-03: Review dependency changes, install scripts, registries and lockfile integrity for supply-chain risk. Pin third-party CI actions and production base images to reviewed immutable references where practicable; establish update ownership.
- [ ] DEP-04: Keep CI permissions minimal and secrets unavailable to untrusted PR code. Avoid unsafe pull_request_target patterns, untrusted shell interpolation and publishing from unreviewed forks.
- [ ] DEP-05: Run containers as non-root with appropriate CPU/memory/process/file limits, writable private scratch space, limited capabilities and restricted egress. Check image-layer contents and `.dockerignore`.
- [ ] DEP-06: Validate required environment variables and related limits at startup; redact errors. Browser VITE variables are public build inputs and must never contain secrets. Allow only intended API destinations.
- [ ] DEP-07: Production must not run the isolated `scripts.e2e_server` or ship its fake catalogue as authoritative data. Validate against a real isolated PostgreSQL instance in integration testing.
- [ ] DEP-08: Build and smoke-test the actual production container and reverse proxy: SPA deep links, API errors, assets, upload limits, timeouts, headers, trusted peers and download bytes.
- [ ] DEP-09: Separate migration execution from normal runtime privileges where feasible. If startup bootstrap remains, test failed seed/migration and prevent serving incompatible schema.
- [ ] DEP-10: Define branch protection and required CI/security checks in the host. `.coderabbit.yaml` instructions and Markdown boxes alone do not block merging.
- [ ] DEP-11: Tie deployed artifacts to reviewed commits; document deployment, rollback/roll-forward, database recovery and temporary-session disruption. Smoke-test after deployment without exposing real user photos.

## 15. Conditional: accounts, organizations and persistent libraries

Activate before introducing accounts, team workspaces, durable photos, roles or public sharing. Otherwise record N/A with the current anonymous-session scope.

- [ ] TENANT-01: Derive identity/tenant from verified server context; scope every read/write/list/search/cache/job/export by tenant and resource permission. Test A/B users and organizations, role changes and shared-link revocation.
- [ ] TENANT-02: Review signup/login/logout, email verification, password hashing, reset tokens, session fixation, rotation, logout invalidation, MFA/passkeys and account enumeration. Prefer established authentication components.
- [ ] TENANT-03: Enforce RBAC for admin/support actions, invitations, membership changes and ownership transfers; test vertical privilege escalation and confused-deputy paths.
- [ ] TENANT-04: If RLS is used, test real application roles and pooled-connection context resets. Owner/bypass roles and incorrectly scoped queries must not undermine isolation.
- [ ] TENANT-05: Private object storage requires scoped access, bounded signed URLs, safe key ownership, encryption/key management, retention, restore and deletion propagation through derivatives/backups.
- [ ] TENANT-06: Durable editing needs recipe/schema versioning, optimistic concurrency, conflict handling, recovery and quotas. Share links, collaborative channels and background jobs must preserve authorization after permissions change.

## 16. Conditional: billing, plans and paid usage

- [ ] BILL-01: Verify signed payment webhooks on raw payloads; enforce bounded replay windows and event idempotency. Handle duplicates and out-of-order events transactionally.
- [ ] BILL-02: Derive price, plan, currency, user and entitlements server-side. Never grant access from a browser success URL or client-supplied plan flag.
- [ ] BILL-03: Test checkout retry, cancellation, failed payment, refund, chargeback, trial abuse, downgrade and billing-provider outage. Reconcile provider state and internal ledger.
- [ ] BILL-04: Atomically reserve/charge/release usage for concurrent expensive jobs. Prevent quota bypass through request replay, multiple sessions, race conditions or failed-work accounting.
- [ ] BILL-05: Keep card data with the payment processor; protect webhook secrets, limit privileges, and monitor cost/usage anomalies.

## 17. Conditional: AI services, DataRobot or external processing

Current enhancement is deterministic; DataRobot model/agent deployment is not present. Activate this section only when such a feature is introduced.

- [ ] AI-01: Classify prompts, photos and metadata sent externally; define consent, retention, training use, geography and deletion. Do not silently transfer private images.
- [ ] AI-02: Treat model outputs/tool calls as untrusted. Validate structured results; prevent prompt injection from authorizing tools, selecting secrets, bypassing tenancy or executing code.
- [ ] AI-03: Set provider deadlines, concurrency, retries, token/image limits, per-user quotas and hard cost protection. Test provider outage and unexpected/malformed outputs.
- [ ] AI-04: Version model, prompt and processing recipe; evaluate quality/safety on representative fixtures and enable rollback. Track failures without logging private inputs.
- [ ] AI-05: For DataRobot specifically, verify deployment identity, scoped credentials, input/output schemas, tracing redaction, service health and version/traffic changes using its applicable skills before shipping.

## 18. Conditional: batch processing, queues and integrations

- [ ] JOB-01: Use bounded queues with per-user fairness, admission quotas, retry/backoff limits, dead-letter handling and cancellation/expiry semantics.
- [ ] JOB-02: Make job processing idempotent; test duplicate delivery, worker death after write/before acknowledgment, replay, poison jobs and partial batch success.
- [ ] JOB-03: Preserve tenant/session authorization in worker context; do not trust arbitrary storage keys or job-supplied user IDs. Expired/deleted jobs must not resurrect private files.
- [ ] JOB-04: Authenticate outbound callbacks and verify inbound signatures; prevent SSRF, replay and unbounded callback retries. Review OAuth scopes, token rotation and revoked integrations.

## 19. Verification evidence and release gates

### Existing repository checks

Run from the indicated directories with locked dependencies installed. Use isolated test data; never point migration/failure tests at production.

| Check | Directory | Command / evidence |
| --- | --- | --- |
| Backend regression suite | `backend` | `uv run --locked pytest` |
| Frontend unit suite | `frontend` | `npm test` |
| TypeScript and production build | `frontend` | `npm run build` |
| OpenAPI/client contract drift | `frontend` | `npm run contracts:check` |
| Connected browser suite | `frontend` | `npm run test:e2e` after starting the documented isolated test API; see `.github/workflows/verify.yml` |
| Image/enhancement/detail benchmark tools | `backend` | Inspect `scripts/benchmark_images.py`, `benchmark_enhancement.py`, `benchmark_detail.py` and their supported options before running; record fixtures and output |

Existing test locations to extend: `backend/tests/test_images.py`, `test_hardening.py`, `test_lifespan.py`, `test_contracts.py`, `test_migrate.py`, `test_presets.py`, image-tool tests; `frontend/tests/unit/`; `frontend/tests/e2e/` including performance, crop, curves, enhancement and detail coverage. A test filename or mock is not proof that a control works in production.

### Additional release evidence

- [ ] GATE-01: All relevant existing checks pass on the final head commit; new bugs have regression cases with meaningful assertions on output, access, bounds or cleanup.
- [ ] GATE-02: Dependency/SAST/secret/container scans complete with tool/version/date/scope and triaged results. These are required evidence categories, not claims that they are already configured in CI.
- [ ] GATE-03: Real isolated PostgreSQL migration/transaction/permission tests pass. Mock DB/browser fixtures alone do not validate SQL grants, TLS or live migrations.
- [ ] GATE-04: Changed upload/render/storage/limit/deployment paths pass staging abuse, overload and fault tests. Changed image algorithms pass quality and peak-memory comparisons.
- [ ] GATE-05: Production configuration, edge controls, monitoring, restore and rollback evidence is present for infrastructure or major release changes. Use authorized staging targets for active tests.
- [ ] GATE-06: No unresolved critical/high reachable issue, private-image leak, authorization bypass, source corruption, unbounded crash path or untested high-risk control. Any exception needs named owner, compensating control, explicit release decision and expiry.
- [ ] GATE-07: Medium/low issues have owners and deadlines; risk acceptance is documented. N/A controls include feature-scope justification; NOT TESTED never becomes PASS by assumption.
- [ ] GATE-08: For authentication/tenancy/billing/public-sharing launches or major architecture changes, obtain independent security review and scoped penetration testing; re-test fixes.

### Finding severity and required record

| Severity | Examples / disposition |
| --- | --- |
| Critical | Reachable remote code execution, broad photo/secret exfiltration, pervasive authorization bypass. Block release. |
| High | Cross-session image access, repeatable service exhaustion/crash, material data corruption, exploitable injection. Block release. |
| Medium | Bounded abuse, substantial performance regression, recoverable workflow failure with limited blast radius. Assign owner and release decision. |
| Low | Minor hardening or usability issue with limited demonstrated impact. Track with justification. |

Rate severity by actual exploit preconditions, reachability, impact and blast radius. A missing header alone is not proof of a critical attack.

```text
Finding: <ID and title>
Control IDs: <FILE-04, LIMIT-06, ...>
Base/head commit: <...>
Severity / confidence: <...>
Introduced or pre-existing: <...>
Location and affected flow: <file:line -> caller -> sink>
Trigger and preconditions: <minimal reproducible case>
Expected / observed: <...>
Impact / affected users and data: <...>
Evidence: <test, trace, response, scan or measurement; redact secrets/photos>
Fix / regression test: <...>
Status / owner / deadline / exception expiry: <...>
Retest evidence and final commit: <...>
```

### Review cadence

Every PR: impact mapping, baseline review and applicable automated checks. Before deployment: final-commit evidence and configuration smoke checks. For relevant high-risk changes: abuse/load/failure and independent review gates above. On a regular owned schedule and after advisories/incidents: dependency triage, restore drills, capacity/retention validation and checklist refresh. Establish the schedule in the team's operating process; this file creates no automation.

## 20. Sources and maintenance

Guidance was checked on 2026-11-25. These are source frameworks; this project checklist is not a complete ASVS mapping or certification.

- [CodeRabbit configuration reference](https://docs.coderabbit.ai/reference/configuration): V2 path instructions and guideline file discovery. The root configuration explicitly uses V2; V3 preview has a different instruction format.
- [CodeRabbit review instructions](https://docs.coderabbit.ai/pr-reviews/review-instructions): instructions guide review comments and do not create pass/fail gates or expand reviewed file scope.
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/): broader application security verification framework; assess applicable ASVS 5.0.0 requirements for formal verification.
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html): layered validation, private storage and hostile-file protection; retrieved through Firecrawl.
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x11-t10/): object authorization, injection-adjacent API trust boundaries, configuration and unsafe API consumption.
- [OWASP API4: unrestricted resource consumption](https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/): independent resource limits, throttling and cost exposure; located live through Nimble Search.

Recheck CodeRabbit schema/support before changing configuration versions. Revisit this architecture snapshot whenever endpoints, processing order, limits, tenancy, persistence or deployment topology changes.
