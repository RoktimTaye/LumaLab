# Audit remediation — 17 November 2026

The supplied audit was checked against the working tree. Its remediation commands were treated as suggestions; the changes below preserve the existing PostgreSQL architecture and image API contracts.

| Finding | Change |
| --- | --- |
| SEC-01 | Expiry removes files, the session-map entry, and its storage accounting. Regression checks cover 410 followed by 404 and released capacity. |
| ARCH-01 | Startup validates the application role's access to all five valid presets. An unready database prevents startup with a safe diagnostic event. Container startup migrates and seeds when `DATABASE_DIRECT_URL` is supplied; otherwise it uses the already-provisioned schema. |
| SEC-02 | Container startup explicitly enables Uvicorn proxy processing and accepts `FORWARDED_ALLOW_IPS`. Only configured peers may supply client IPs. The application continues to use the validated ASGI client address. |
| DOS-01 | One heavy upload/export permit and two preview/enhancement permits. Authorization tracks active readers without holding the global map lock during processing. Deletion and expiry wait for active readers, and retirement excludes new readers. Upload encoding also runs outside the map lock. |
| DOC-01 | Home copy now describes available enhancement and JPEG export; the local marketing demo remains labelled as a preview. |
| ROUT-01 | Unknown extensionless navigation routes reach the SPA. Missing API paths, assets, hidden paths and unsupported methods retain errors. Windows path separators are normalized for these exclusions. |
| SEC-03 | Outer ASGI middleware adds nosniff, DENY framing and strict-origin-when-cross-origin referrer policy to normal, error and preflight responses. |
| PERF-01 | Lookup tables and bounded overlapping tiles replace large processing buffers while retaining filter order and rounding. Private preview and analysis PNGs avoid full-resolution decoding during lightweight requests. |
| CODE-01 | Production installs private-cache middleware once, outside the error/CORS layers. |
| TEST-01 | Playwright projects include Chromium, Firefox and WebKit. CI installs all engines and uses an isolated test API with real processing and test-only presets. |

Additional browser fixes: Safari/WebKit now retains the dialog trigger explicitly for focus restoration, and the mobile menu explicitly focuses its trigger so Escape works consistently. The reduced-motion test waits for React to mount before inspecting computed styles.

Additional issue: rate-limiter capacity previously evicted live client buckets, allowing a rotating set of addresses to reset limits. It now reclaims expired buckets and rejects new clients while all slots are active.

## Deployment

Neon PostgreSQL and network access remain required for the production preset catalogue. This is an explicit architecture choice; no silent SQLite fallback is introduced. Unit tests and the isolated browser-test server do not require network access or real database credentials.

For an already-provisioned database, supply the least-privilege pooled `DATABASE_URL` and omit the owner credential. For automatic container bootstrap, also supply a direct owner `DATABASE_DIRECT_URL` for the **same database and branch**. Migrations must have been tested on a development branch first. The existing migration requires the `lumalab_app` role to exist. Bootstrap errors stop startup before accepting requests. For tighter credential separation, run the migration and seed commands as a separate release step, then deploy without the owner URL.

Set `FORWARDED_ALLOW_IPS` as a **process/container environment variable**, containing the ingress proxy's IPs or CIDRs. It is a Uvicorn setting, not a backend `.env` setting. The default is `127.0.0.1`. Never use `*` on a backend directly reachable by untrusted clients. If a hosting provider requires `*`, first ensure all traffic must pass through its trusted ingress and that ingress replaces untrusted forwarding headers. See [Uvicorn proxy settings](https://uvicorn.dev/settings/).

Keep one worker and one replica. Sessions, rate limits and processing permits remain process-local and sessions disappear on restart. Resource usage depends on input and concurrent operations; these changes do not establish a universal 512 MB container guarantee. Use the standalone benchmark on the deployment target before choosing a memory limit.

## Reproduce verification

From `backend/`: `uv run --locked pytest` and `uv run --locked python -m scripts.benchmark_images`.

From `frontend/`: `npm test`, `npm run build`, and `npm run contracts:check`.

For browser checks without Neon, start `uv run --locked python -m scripts.e2e_server` from `backend/`, then run `npx playwright install firefox webkit` and `npx playwright test` from `frontend/`. The fixture server binds only to loopback, substitutes the preset catalogue and readiness probes, and uses temporary image storage. Each test resets sessions through a route available only in that loopback test process. Its larger test-only upload quota prevents the three browser engines, which share one loopback IP, from throttling each other; production limit behavior is covered separately by backend tests. It is not the production entry point. CI additionally installs bundled Chromium.

Renderer compatibility tests compare JPEG bytes against the previous implementation across combined adjustments, thin images and tile boundaries. Concurrency checks verify a preview completes during an export of the same session, while heavy requests retain bounded capacity.


## Verification results

- Backend: **111 passed**, plus **530 subtests**. No live database connection was used.
- Frontend unit tests: **9 passed**.
- Final Playwright run: **36 passed** (12 each in Chrome/Chromium, Firefox and WebKit), including responsive, accessibility, upload/edit/export and 24 MP performance checks.
- Production build, generated API contract check and `git diff --check`: passed.
- `npm audit`: **0 known vulnerabilities** in the locked frontend dependency tree.
- Built frontend/API HTTP smoke checks: Home, Studio and unknown application navigation return HTML; missing API and asset paths retain 404; security headers are present.
- Standalone 24 MP noisy-image export with all six adjustments: **361.7 MiB peak process working set**, **9.616 seconds** on this Windows host while other checks were running. This is an export-only benchmark, not a complete server/concurrency or Linux container measurement.

No live schema migration, production deployment or new CodeRabbit CLI review was run. The supplied audit informed the fixes, supplemented by source inspection and regression testing. The new CI workflow has been added locally and has not yet run on GitHub.
