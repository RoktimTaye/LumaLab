# LumaLab frontend developer guide

The React/TypeScript frontend provides a responsive landing page and `/studio` photograph editor. Studio uploads, presets, previews, enhancement and JPEG export use the FastAPI backend. See [Backend_doc](Backend_doc.md) for API and database setup.

## Local development

Install Node.js >=22.12.0 and npm. From the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. In another terminal, start the provisioned backend:

```powershell
cd backend
uv run --locked python -m app --reload
```

Complete [backend first setup](Backend_doc.md#prerequisites-and-first-setup) before using the normal API. Vite proxies `/api` to `http://127.0.0.1:8000`, so local development needs no frontend environment file or CORS configuration. Both processes must remain running for Studio editing.

Use `npm ci` with the committed `frontend/package-lock.json`. The stack is React, TypeScript, Vite, TanStack Router/Query, CSS Modules, locally bundled Fontsource fonts and Lucide icons. Exact dependency versions are in `frontend/package.json`.

## Source layout

| Path | Responsibility |
| --- | --- |
| `frontend/src/main.tsx` | Router, Query provider and app entry |
| `frontend/src/pages/Home.tsx` | Landing page and local marketing demo |
| `frontend/src/pages/Studio.tsx` | Session lifecycle, editing workflow and UI state |
| `frontend/src/pages/*.module.css` | Page styling and responsive layouts |
| `frontend/src/components/` | Brand, header and photograph preview |
| `frontend/src/styles/global.css` | Shared typography, colours and controls |
| `frontend/src/lib/api.ts` | Shared typed HTTP client and API errors |
| `frontend/src/lib/api.generated.ts` | Committed OpenAPI-derived types |
| `frontend/src/lib/editor.ts` | Adjustment helpers and local upload validation |
| `frontend/src/lib/imageResponse.ts` | JPEG response/object-URL and download helpers |
| `frontend/public/` | Favicon and bundled sample photographs |
| `frontend/tests/unit/` | Editor and image-response tests |
| `frontend/tests/e2e/` | Connected workflow, accessibility, responsive and performance tests |

## Editing behavior to preserve

- Accept still JPEG, PNG and WebP with matching extensions, up to 10,000,000 bytes, 24 megapixels and 10,000 pixels per side. Client validation gives early feedback; the backend independently validates all files.
- Keep all six adjustments as complete integer state. Brightness/contrast/saturation range from 0–200 (neutral 100), warmth from -50–50 (neutral 0), and sharpness/vignette from 0–100 (neutral 0).
- Load Original, Cinematic, Golden Hour, Monochrome and Vivid from `/api/v1/presets`. Presets replace every adjustment; manual changes mark the selection Custom. Show an unavailable message when preset retrieval fails.
- Render Studio edits through the API. The Home demo uses a local CSS/SVG approximation and is not the authoritative image renderer.
- Keep the last successful preview while another is pending or fails, mark outdated previews, and apply a response only when its session, revision and edit state still match. Abort or ignore obsolete work.
- Auto Enhance applies returned settings only on success. Failed enhancement preserves edits and supports explicit retry. Compare changes only the display; it does not edit settings or request a new render.
- Export waits for a successful preview of the current state, submits an immutable settings snapshot and downloads the full-resolution backend JPEG.
- Commit a replacement only after upload and original preview succeed. Failed replacement preserves the existing image/edits. Successful replacement resets editor state, disposes obsolete URLs and requests deletion of the old session.
- Store tokens and editor settings only in memory. Send tokens only through Authorization headers. Closing/replacing Studio cleans up best effort; backend expiry remains the fallback. Restarted/expired sessions require a new upload.
- Preserve keyboard/touch controls, visible focus, skip navigation, dialog focus restoration, Escape behavior, reduced motion, status/alert announcements and narrow-screen reflow.

## API integration and generated types

`src/lib/api.ts` centralizes relative `/api/v1` requests, bearer headers, `AbortSignal`, JSON errors and binary responses. Use it for new UI operations. Errors are `ApiError` instances carrying status and optional backend code. The server envelope is `{"error":{"code":"...","message":"..."}}`.

Send uploads as `FormData` with a part named `file`; let the browser supply the multipart boundary. Preview/export use JSON with all six adjustments. Preview requests include a nonnegative revision; successful responses echo it in `X-Image-Revision`. Original preview, edited preview and export return JPEG bytes directly. Export includes `Content-Disposition`; deletion returns an empty 204.

Image operations require the image-specific token returned by upload. Use blob URLs for authorized image responses and release them on replacement/unmount or after download. `imageResponse.ts` rejects errors and non-JPEG responses before allocating a URL. Do not place private image data in persistent storage or token-bearing URLs.

For intentional backend contract changes, install uv and the backend locked environment, then run from `frontend/`:

```powershell
npm run contracts:generate
npm run contracts:check
npm run build
```

Review and commit the generated file. Generation exports OpenAPI locally using synthetic settings and does not start the API or connect to PostgreSQL. The check detects stale/missing output without rewriting it; unsupported schema constructs fail generation. Types do not replace backend runtime validation.

## Verification

From `frontend/`:

```powershell
npm test
npm run build
npm run contracts:check
```

The build runs TypeScript checks before Vite output. Contract checking also requires uv and installed backend dependencies. To run connected browser tests without Neon, start this isolated API in a separate terminal from `backend/`:

```powershell
uv run --locked python -m scripts.e2e_server
```

The test API binds to loopback port 8000, uses a test preset catalogue and temporary image storage, and exposes a test-only session reset route. Stop any normal backend already using that port. Never use this entry point in deployment.

Then, from `frontend/`, in PowerShell:

```powershell
npx playwright install chromium firefox webkit
$env:PLAYWRIGHT_CHANNEL = "chromium"
npm run test:e2e
```

Playwright starts Vite on port 4173 and runs Chromium, Firefox and WebKit with one worker. Its default Chromium channel is installed Google Chrome; `PLAYWRIGHT_CHANNEL=chromium` selects the bundled engine. For one browser, use `npm run test:e2e -- --project=chromium` (or `firefox` / `webkit`). For installed Edge, set `PLAYWRIGHT_CHANNEL=msedge` and select the Chromium project. Ensure a reused Vite server on port 4173 belongs to this checkout.

Coverage includes upload-to-download, retries, stale responses, replacement failures, JPEG consumption, keyboard interaction, axe checks and performance inputs at 12 MP/24 MP. The responsive matrix is 320×568, 360×800, 390×844, 430×932, 768×1024, 820×1180, 1024×768, 1280×800, 1440×900, 1920×1080, 2560×1440 and 844×390.

`.github/workflows/verify.yml` runs backend tests, frontend unit/build/contract checks and all three Playwright engines against the isolated API. Failures upload browser artifacts. Historical local evidence from 17 November 2026 recorded 9 frontend unit tests and 36 browser tests passing; these were not rerun by this documentation update. Automated WebKit coverage does not establish physical Safari/device or assistive-technology coverage. Verify actual devices, browser zoom and the hosted release separately.

## Build and hosting

```powershell
npm run build
npm run preview
```

Build output is `frontend/dist`. For the combined production service, the repository-root Dockerfile builds that directory and serves it through FastAPI alongside `/api`. Direct `/studio` and other application navigation receive the SPA entry document; missing API and asset paths retain their errors. See [backend deployment](Backend_doc.md#deployment-and-release-checks).

For separate static hosting, configure an SPA fallback to `index.html` and set this in `frontend/.env.local` before building:

```dotenv
VITE_API_BASE_URL=https://your-api-host.example
```

This value is a public, build-time backend origin; rebuilding is required when it changes. Set the backend's `ALLOWED_ORIGINS` to the exact frontend origin and restart the backend. Keep normal asset responses intact. Use HTTPS for both hosts. Never put backend/database credentials in `VITE_*` variables or browser code.

## Assets

Bundled photographs came from Unsplash's image CDN; retain provenance when replacing them:

- [Alpine](https://images.unsplash.com/photo-1464822759023-fed622ff2c3b)
- [Forest](https://images.unsplash.com/photo-1441974231531-c6227db76b6e)
- [Nature](https://images.unsplash.com/photo-1472396961693-142e6e269027)

Space Grotesk and DM Sans retain their packaged Fontsource license information; Lucide icons use the ISC license. Fonts and photographs are bundled rather than fetched from external services at runtime.
