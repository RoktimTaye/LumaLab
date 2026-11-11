# LumaLab frontend

A responsive photography website and editing studio built from the LumaLab product PRD and the supplied infrastructure design document. This delivery contains only the frontend; there is no backend, database, account system, or external image-processing API.

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
