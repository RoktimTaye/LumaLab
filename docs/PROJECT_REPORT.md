# LumaLab photograph editor — implementation report

**Report date:** 16 November 2026  
**Project:** LumaLab web photograph editor  
**Status:** MVP implementation and connected verification

## Abstract

LumaLab is a responsive browser-based photograph editor with private temporary image sessions, database-backed presets, six adjustment controls, automatic enhancement suggestions, before/after comparison and full-resolution JPEG export. The React/TypeScript frontend communicates with a FastAPI service. Neon PostgreSQL stores the preset catalogue and migration history; image bytes remain in process-local private temporary storage and are removed through deletion, expiry and lifecycle cleanup.

## Objectives and scope

The MVP supports a complete upload-to-export workflow for still JPEG, PNG and WebP images up to 10,000,000 upload bytes, 24 megapixels and 10,000 pixels per side. It validates uploads in both browser and server, normalizes orientation and colour, preserves the exact uploaded bytes during a session, renders edits from the normalized original, and protects image operations with a per-session bearer token. No user accounts, durable photo library or saved editing history are included.

The repository's implementation checklist references a separate product PRD, but that source document was not present in this checkout. This report therefore records the implemented scope and acceptance criteria available in the checklist and code; institution-specific academic cover details were not inferred.

## Architecture and implementation

- **Frontend:** React 19.3.1, TypeScript 7.0.2, Vite 8.3.8, TanStack Router and Query. OpenAPI-derived TypeScript contracts and one shared API client provide uploads, authorized JPEG previews, enhancement, export and deletion.
- **API and processing:** FastAPI 0.162.4, Pydantic 2.14.3, Pillow 13.0.0, NumPy 2.4.6 and OpenCV 5.0.0.93. The API independently checks multipart size, format, animation/frame count, dimensions, EXIF orientation, ICC profiles and decompression limits.
- **Database:** Neon PostgreSQL 18 stores five bounded, seeded presets and the migration ledger. The runtime uses a pooled, read-only application role; numbered migrations and repeatable seeding require the direct owner connection and are explicit commands.
- **Temporary image data:** Exact input bytes and a normalized working copy are held under private per-run storage. Sessions expire after 60 minutes, are capped at 32 per process and are volatile across process restarts. The API does not persist photographs or edit state in Neon.
- **Deployment model:** The repository Dockerfile builds the frontend and serves the API and SPA from one Railway service. One replica is required while sessions and processing coordination remain process-local. Deployment was documented; this verification did not publish a Railway service.

The full architecture, MVP data model and Level 0/Level 1 flows are in [ARCHITECTURE.md](ARCHITECTURE.md). API request and response contracts are available at `/api/docs` and `/api/openapi.json` when the service is running.

## Verification method and results

Automated backend tests use generated images, temporary directories and simulated database failures. Separate checks use the isolated Neon development branch for migration checksums, PostgreSQL constraints, repeatable preset seeding, rollback behavior and application-role retrieval. The default/main branch was not modified by those checks.

The connected browser suite exercises upload, presets, keyboard edits, comparison, automatic enhancement, explicit retry after an unavailable-service response, replacement/error handling, stale preview ordering and JPEG download. Responsive and accessibility coverage includes the twelve specified viewport sizes, axe checks, keyboard focus, reduced motion, 200% text sizing and touch-emulated navigation/panel controls. The 320 px viewport is used as a reflow proxy for a 200% zoom layout; desktop browser zoom was not directly automated.

### Reference performance

Measurements were collected on a Windows laptop with Intel Core i5-11400H (11th generation, 2.70 GHz), 8.32 GB RAM (7.74 GiB reported by the OS), Node 24.9.0, npm 11.19.1 and Python 3.11.9. Inputs were locally generated gradient/detail JPEGs: 4,000×3,000 (12 MP, 418,784 bytes) and 6,000×4,000 (24 MP, 821,440 bytes). Values are single-run wall-clock measurements and are not production load guarantees.

| Operation | Chrome 157.0.8103.51 | Edge 157.0.4341.60 | Checklist target |
| --- | ---: | ---: | ---: |
| Home heading usable | 910 ms | 703 ms | < 3 s |
| Slider key input to next paint | 18.8 ms | 21.9 ms | < 100 ms |
| Settled preview response after debounce, 12 MP source | 465 ms | 404 ms | < 1 s |
| Enhance plus settled preview | 1,304 ms | 1,426 ms | < 3 s |
| Full-resolution JPEG export | 1,061 ms | 1,442 ms | < 5 s |
| 12 MP upload and preview ready | 1,709 ms | 1,571 ms | Observed |
| Maximum supported 24 MP upload and preview | 2,730 ms | 3,035 ms | Completes without resource exhaustion |

Chrome reported 44,771,549 bytes and Edge 44,504,814 bytes of JavaScript heap after the 24 MP case. This is browser heap, not total renderer/native-image memory. Both browsers completed the maximum-size case without an error. See [VERIFICATION.md](../frontend/VERIFICATION.md) for commands and remaining limits.

## Conclusion

The local connected MVP passed the documented backend, frontend, contract, browser and performance checks. Core output remains private and session-scoped; Neon is used for the preset catalogue rather than photo storage. The main verification limits are unavailable Firefox/Safari/WebKit executables, no physical-device or assistive-technology session, no direct desktop-zoom automation, and no published Railway deployment. The report should be updated if the original product PRD or institutional submission format is supplied later.
