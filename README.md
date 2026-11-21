# LumaLab

### Light. Colour. Create.

**A browser-based photo editing studio for everyday creators, photography enthusiasts and small teams.**

LumaLab helps people turn a photograph into a finished image through a focused workflow: upload, adjust, compare and download. It brings manual controls, creative presets and automatic enhancement into one responsive workspace, with no account required in the current application.

The project is built around a practical goal: make common photo adjustments approachable while giving users control over the final result. Users can start with a preset, refine individual settings, compare the result with the original and export a full-resolution JPEG.

## Why LumaLab exists

Many everyday editing tasks come down to a few decisions: improve the light, balance the colour, bring out detail and check whether the result feels right. LumaLab puts those decisions at the centre of the experience.

Its purpose is to provide an accessible workspace for preparing individual photographs for social posts, personal collections, portfolios and everyday business content. The experience combines a quick starting point with manual refinement, so users can explore different looks without overwriting their source photograph.

## Who it is built for

| Audience | Intended use |
| --- | --- |
| Everyday users | Improve travel, landscape and personal photographs through simple light and colour adjustments. |
| Content creators and social media managers | Prepare individual photographs with a chosen visual style before publishing them through their usual channels. |
| Photography enthusiasts | Explore presets, refine tonal choices and compare edits with the original. |
| Freelancers and small business owners | Adjust photographs for portfolios, promotional content and online communication. |
| Students and developers | Study or extend a complete React and FastAPI image editing workflow with typed API contracts and automated checks. |

## Product capabilities

### Six focused editing controls

Adjust brightness, contrast, saturation, warmth, sharpness and vignette. Each control contributes to a complete editing state, allowing users to refine a preset or build their own look.

### Five creative starting points

The preset catalogue includes **Original, Cinematic, Golden Hour, Monochrome and Vivid**. Applying a preset replaces the full set of adjustments, and every look can be refined manually afterward.

### Automatic enhancement

Auto Enhance analyzes the photograph and suggests light and colour adjustments. Users retain control of the resulting settings and can refine or reset them. Enhancement uses image analysis rather than generative image creation.

### Before-and-after comparison

Compare the edited preview with the normalized original using an interactive divider. Users can evaluate the effect of their changes without losing their current settings.

### Editing that preserves the source

The backend keeps the uploaded original separate from its normalized working files. Previews and exports are rendered from the normalized source, so repeated adjustments do not repeatedly overwrite the photograph. Reset returns the controls to their neutral values.

### Full-resolution JPEG export

Download the edited image as a JPEG at the normalized source dimensions. Export uses the current adjustment settings, a safe download filename and output without original EXIF/GPS metadata.

### Responsive workspace

The interface adapts to desktop, tablet and mobile layouts. Keyboard controls, visible focus, status messages and reduced-motion support are included in the UI.

## The user journey

1. **Bring a photograph.** Upload a supported image or try the bundled sample.
2. **Choose a starting point.** Apply a preset, use Auto Enhance or begin with manual controls.
3. **Refine the result.** Adjust light, colour and detail while the backend renders previews.
4. **Compare and decide.** Review the original alongside the edited image, then refine or reset as needed.
5. **Download the finished image.** Export a full-resolution JPEG for use in the user's own workflow.

## Supported images

| Capability | Current support |
| --- | --- |
| Input formats | Still JPEG (`.jpg`, `.jpeg`), PNG and WebP |
| Maximum upload size | 10,000,000 bytes per image |
| Maximum image resolution | 24 megapixels |
| Maximum image side | 10,000 pixels |
| Output format | Full-resolution JPEG |
| Transparency | Composited onto white during normalization |
| Orientation and colour | EXIF orientation handling and sRGB normalization |

Both the browser and the backend validate uploads. Animated, unsupported, malformed and extension/content-mismatched images are rejected.

## Image handling and session privacy

Photographs are uploaded to the backend for processing. They are held in private temporary storage, while PostgreSQL stores the preset catalogue and migration history.

- Each image session has its own bearer token for preview, enhancement, export and deletion.
- Tokens are sent in Authorization headers and kept in browser memory. The backend retains token hashes.
- Private image responses use `Cache-Control: no-store`.
- Sessions expire after 60 minutes by default. Edits do not extend that expiry.
- Session deletion, expiry and graceful shutdown remove temporary files; startup cleans up stale run directories.
- Sessions are temporary and are lost on a backend restart. Users should download their work before leaving the session.

The current product does not provide an account-based photo library or persistent editing history.

## Technology and architecture

LumaLab separates the editing interface from image processing through a typed HTTP API. In development, Vite proxies API requests to FastAPI. The production Docker build serves the frontend and API together from one origin.

| Layer | Technologies and responsibility |
| --- | --- |
| Frontend | React, TypeScript, Vite, TanStack Router and TanStack Query |
| Interface | CSS Modules, Lucide icons and locally bundled fonts |
| Backend | Python, FastAPI, Pydantic and Uvicorn |
| Image processing | Pillow, NumPy and OpenCV |
| Database | Neon PostgreSQL for presets and migration history |
| API contracts | OpenAPI-derived TypeScript types and a shared HTTP client |
| Verification | pytest, Vitest, Playwright and axe accessibility checks |
| Packaging | Docker build for the combined frontend and backend service |

Image sessions and processing coordination are process-local. The current deployment model uses one backend worker and one replica.

## Project scope

This repository contains the current MVP implementation of the upload-to-export workflow. It includes the editing studio, API, database migrations, preset seeding, automated checks and deployment packaging.

The current scope covers individual still-image editing. Accounts, a durable photo library, saved editing history, batch processing, RAW workflows, collaborative editing and generative image tools are outside this implementation. The Home page's interactive demo is a local visual approximation; Studio uses backend-rendered images.

Release readiness depends on validation of the actual hosting environment, configuration and intended workload. Developer documentation includes the deployment and release checks.

## Getting started with development

The project has two main developer guides:

- **[Backend_doc](Backend_doc.md)** — Python environment, database provisioning, migrations, API contracts, image lifecycle, configuration, tests and deployment.
- **[Frontend_doc](Frontend_doc.md)** — Node environment, UI structure, API integration, generated types, browser testing and hosting.

Local development requires **Python 3.11**, **uv**, **Node.js >=22.12.0**, **npm** and a configured PostgreSQL development database. Follow the backend guide first to provision the database, apply migrations, seed presets and configure the private environment file. Then start the backend and frontend in separate terminals.

| Local service | Address |
| --- | --- |
| Frontend | `http://127.0.0.1:5173` |
| Backend | `http://127.0.0.1:8000` |
| Interactive API documentation | `http://127.0.0.1:8000/api/docs` |

For browser tests without a live database, the frontend guide documents an isolated test API. That server is for testing only.

## Repository structure

```text
LumaLab/
├── backend/                 FastAPI service, image processing and database code
├── frontend/                React application, UI assets and browser tests
├── .github/workflows/       Automated verification workflow
├── Backend_doc.md           Backend developer guide
├── Frontend_doc.md          Frontend developer guide
├── Dockerfile               Combined production build
└── README.md                Product overview and entry point
```

## Quality and contribution workflow

The repository includes backend regression tests, frontend unit tests, TypeScript/build checks, API contract checks and connected browser tests across Chromium, Firefox and WebKit. Browser coverage includes the editing workflow, responsive layouts, accessibility checks and representative large-image scenarios.

Before submitting changes, follow the relevant developer guide, run the checks affected by the change and update documentation when behavior changes. API changes should include reviewed generated frontend types. Keep credentials, temporary images and local runtime artifacts out of version control.

Bundled photograph sources and font/icon attribution are documented in [Frontend_doc](Frontend_doc.md#assets).
