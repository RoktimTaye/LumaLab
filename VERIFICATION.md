# Frontend verification

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
