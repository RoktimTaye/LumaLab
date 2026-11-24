# ABSTRACT

LumaLab is a browser-based photo editing application for people who need to prepare individual photographs without installing a desktop editor. It brings image upload, creative presets, manual light and colour controls, automatic enhancement, crop, before-and-after comparison, and full-resolution JPEG export into one responsive workflow. The project aims to make routine image improvements approachable while retaining meaningful user control.

The application has a React and TypeScript frontend and a FastAPI backend. Pillow, NumPy, and OpenCV support image validation, normalization, analysis, and rendering. PostgreSQL stores the preset catalogue and migration history. Uploaded image data is kept in private temporary storage for the duration of an image session. A typed HTTP API connects the browser to the processing service.

This report explains the problem, requirements, architecture, implementation, validation, and limitations of the current application. LumaLab supports still JPEG, PNG, and WebP uploads and exports a JPEG at the normalized source dimensions. Its current scope is a single-image editing workflow; it does not include accounts, persistent photo libraries, batch processing, or generative editing.

# CHAPTER 1 INTRODUCTION

## 1.1 Project Overview

Digital photographs are used in personal communication, portfolios, promotional material, and social media. Many photographs need modest corrections to light, colour, framing, or detail before use. Desktop editing software can provide these controls, but its installation and complex interface may be unnecessary for an occasional task. LumaLab offers a focused browser workflow for editing one photograph at a time.

The user uploads a photograph, chooses a preset or Auto Enhance, changes individual controls, compares the edited result with the original, and exports a JPEG. The system retains the normalized source during the temporary session, so each preview and export is rendered from the same base image rather than from a previously compressed preview.

## 1.2 Problem Statement

A simple image editor must balance ease of use with control and output consistency. Users need fast visual feedback, a way to compare changes, and an export that matches the selected edit. Large or malformed uploads must be rejected safely. Images also may contain orientation and colour-profile information that must be normalized before editing. The system must manage image data without exposing temporary files or access tokens.

## 1.3 Objectives

- Provide a responsive interface for uploading and editing a still photograph.
- Offer presets, six manual controls, RGB point curves, crop, and automatic enhancement.
- Render previews and full-resolution export from a shared editing state.
- Protect temporary image sessions with image-specific bearer tokens.
- Validate file type, size, dimensions, and editing input on the server.
- Support comparison, reset, keyboard interaction, and clear error messages.

## 1.4 Scope

The implemented application covers single-image editing from upload through JPEG download. It accepts still JPEG, PNG, and WebP files. The backend normalizes orientation and colour, stores private temporary files, and processes previews and export. PostgreSQL supplies five named presets. The application currently has no user accounts or durable editing history.

# CHAPTER 2 BACKGROUND AND SYSTEM STUDY

## 2.1 Photo Editing Workflow

The main editing tasks are exposure correction, contrast adjustment, colour balance, detail refinement, and framing. LumaLab groups them into a short workflow: bring a photograph, choose a starting point, refine the result, compare it with the original, and download the final image. The workflow supports both quick corrections and manual exploration.

## 2.2 Presets and Manual Refinement

Five presets provide starting values: Original, Cinematic, Golden Hour, Monochrome, and Vivid. A preset replaces the six adjustment values. The user can then refine brightness, contrast, saturation, warmth, sharpness, and vignette. Manual changes identify the result as a custom edit. Reset restores neutral values.

## 2.3 Automatic Enhancement

Auto Enhance analyzes the uploaded image and returns a versioned enhancement recipe with an explanation of its decisions. The current implementation uses deterministic photographic analysis, including tonal distribution, regional lighting, colour characteristics, and source-scale detail sampling. It is not a trained generative model. A strength control blends the automatic result with the source, and the manual controls can refine it afterward.

# CHAPTER 3 REQUIREMENT ANALYSIS

## 3.1 Functional Requirements

- Upload a still JPEG, PNG, or WebP image and report validation errors.
- Retrieve and apply the preset catalogue.
- Adjust six numeric editing controls within their allowed ranges.
- Edit combined RGB and individual red, green, and blue point curves.
- Request automatic enhancement and inspect its stated editing decisions.
- Crop with a visual frame, aspect-ratio choices, and numeric pixel fields.
- Compare edited and original views without changing the editing state.
- Preview the current edit, inspect 100% detail, and download a full-resolution JPEG.
- Delete or expire a temporary image session and remove its files.

## 3.2 Non-Functional Requirements

The interface should remain usable at narrow and wide viewport sizes and support keyboard controls, visible focus, status announcements, and reduced motion. The backend must validate every request independently of browser-side checks. Private image responses must avoid cache storage, and access tokens must not be placed in image URLs. Preview requests must handle stale responses so that an older result cannot replace a newer edit.

## 3.3 Input and Output Limits

An upload may contain at most 10,000,000 bytes, 24 megapixels, and a 10,000-pixel maximum side. Animated, malformed, unsupported, and extension/content-mismatched images are rejected. JPEG export uses the normalized source dimensions or the selected crop dimensions. It removes source EXIF/GPS metadata and embeds an sRGB colour profile.

# CHAPTER 4 SYSTEM DESIGN AND ARCHITECTURE

## 4.1 Overall Architecture

The browser hosts the editing interface and sends typed requests to the FastAPI service. The backend validates uploads and editing settings, renders images, manages temporary sessions, and reads presets from PostgreSQL. During local development Vite proxies API calls. The production Docker build serves the frontend and API from one origin.

[[diagram:docs/diagrams/lumalab_use_case_diagram.png|Figure 4.1 Use case diagram for the LumaLab editing workflow]]

## 4.2 Data Flow

Upload creates an image session and returns an image identifier, an access token, dimensions, and an expiry time. Authorized preview and export requests submit the complete adjustment state. The backend renders from the normalized source and returns JPEG bytes. Automatic enhancement returns settings and a recipe rather than changing the stored source image.

[[diagram:docs/diagrams/lumalab_dfd_level_0.png|Figure 4.2 Level 0 data flow diagram]]

[[diagram:docs/diagrams/lumalab_dfd_level_1.png|Figure 4.3 Level 1 data flow diagram]]

## 4.3 Data Storage

PostgreSQL stores preset records and a migration ledger. Preset records contain a stable identifier, name, description, and bounded adjustment values. Image bytes and token hashes are not stored in PostgreSQL. Private temporary files hold image data while process memory coordinates the session. This design supports the present single-worker, single-replica deployment model.

[[diagram:docs/diagrams/lumalab_er_diagram.png|Figure 4.4 Entity relationship diagram for persistent data]]

## 4.4 Session Security

Each uploaded image has a random identifier and an image-specific bearer token. The browser sends the token in the Authorization header for private operations. The backend retains a hash of the token and sets private image responses to no-store. Session deletion, expiry, and graceful shutdown remove temporary files. Sessions expire after 60 minutes by default; edits do not extend this period.

# CHAPTER 5 USER INTERFACE DESIGN

## 5.1 Home and Studio

The Home page introduces the product and offers a sample-based visual demonstration. The Studio is the authoritative editing workspace and uses backend-rendered images. It shows the photograph, editing controls, presets, comparison, crop, enhancement, and export actions in a responsive arrangement.

## 5.2 Editing Controls

Brightness, contrast, and saturation use integer values from 0 to 200, with 100 as neutral. Warmth ranges from -50 to 50, with 0 neutral. Sharpness and vignette range from 0 to 100, with 0 neutral. RGB curves allow two to sixteen ordered points per channel, fixed input endpoints, and bounded input/output values from 0 to 255.

## 5.3 Crop and Comparison

The crop interface offers freeform, original, and named aspect ratios. Users can drag the crop frame or use numeric pixel fields and keyboard arrows. Applying the crop sends it to the backend; cancelling discards the draft. Comparison displays the original and edited versions at the same crop without changing settings.

## 5.4 Feedback and Accessibility

The interface retains the last successful preview while a new preview is pending. It ignores obsolete responses whose session, revision, or edit state no longer match. Status and error messages explain processing results. Keyboard operation, focus restoration, visible focus styles, reduced-motion support, and responsive reflow are part of the documented user interface.

# CHAPTER 6 BACKEND AND IMAGE PROCESSING

## 6.1 Upload Validation and Normalization

Both client and server check basic upload constraints, while the server makes the final decision. It verifies format, file size, image dimensions, animation state, and filename/content agreement. The service applies EXIF orientation, converts colour to sRGB, and composites transparent pixels onto white. It keeps original bytes separate from normalized working files.

## 6.2 Preview and Export Pipeline

The backend accepts complete settings for each render. The enhancement layer, when present, runs before manual brightness, contrast, saturation, warmth, curves, sharpness, and vignette. Preview uses a reduced image for responsive feedback. Export renders a JPEG from the full normalized source and current crop. Both operations use the same edit recipe so the preview reflects the intended export.

## 6.3 RGB Curves

The curve interface provides a combined RGB channel and separate red, green, and blue channels. The backend validates ordered control points and uses shape-preserving cubic interpolation to build bounded lookup tables. The combined curve is applied first, followed by each colour channel. Identity curves leave the image unchanged.

## 6.4 Automatic Enhancement

The analyzer evaluates tonal quantiles, regional lighting, hue-specific saturation, plausible neutral colours, and noise/structure indicators. The version 3 recipe also samples source-resolution patches to guide restrained texture and medium-scale detail adjustments. Edge, noise, brightness, and colour conditions limit these corrections. The output is a documented set of deterministic decisions, not restoration of missing information.

## 6.5 Capacity and Cleanup

Processing permits limit expensive operations such as source analysis and full-resolution export. Temporary files are removed on deletion, expiry, graceful shutdown, and startup cleanup of stale run directories. A backend restart ends in-memory image sessions, so users must upload again if they have not downloaded their result.

# CHAPTER 7 DATABASE AND API

## 7.1 Database Design

The application uses PostgreSQL for the preset catalogue and schema migration history. Numbered SQL migrations create and manage the schema. A seed command validates and upserts the five built-in presets by stable ID. Runtime database access is intended for a limited application role, while migration and seeding use a separate owner connection.

## 7.2 API Resources

The API exposes health and preset retrieval, image upload, original preview, edited preview, enhancement suggestions, export, and deletion under /api/v1. Upload returns an image identifier and access token. Preview accepts a client revision and echoes it in the response. Export returns a JPEG attachment. Existing-image operations require the bearer token.

## 7.3 Contract Validation

Pydantic schemas reject invalid adjustment types and out-of-range values. Crop coordinates must be integers within the source image. Curves require ordered integer points and fixed endpoint inputs. The frontend uses types generated from the backend OpenAPI schema, but the backend still validates requests at runtime.

# CHAPTER 8 TESTING AND VALIDATION

## 8.1 Test Strategy

Backend pytest tests cover image validation, processing, enhancement, storage, access control, session lifecycle, database migration logic, and API contracts. Frontend unit tests check editor state and binary image responses. Playwright browser tests exercise upload, editing, preview, export, replacement, responsive layouts, keyboard interaction, and accessibility checks across Chromium, Firefox, and WebKit.

## 8.2 Recorded Verification

The project documentation records 142 backend tests and 530 subtests passing after the source-detail renderer change on 22 November 2026. It also records 11 frontend unit tests, API contract validation, and a production build passing. These are historical results, not tests rerun for this report.

## 8.3 Performance Observation

A local synthetic 6000 by 4000 pixel version 3 JPEG render took 47.784 seconds and reached 379.6 MiB peak working set on the development Windows machine. Hosting timeouts, memory capacity, and real maximum-size inputs require separate checks.

## 8.4 Remaining Validation

Automated browser coverage does not replace physical-device or assistive-technology testing. Release checks must also cover configuration, database permissions, temporary storage, HTTPS, workload limits, and representative photographs in the hosting environment.

# CHAPTER 9 DEPLOYMENT AND MAINTENANCE

## 9.1 Local Development

The backend is started after configuring a PostgreSQL development database, applying migrations, and seeding presets. Vite runs the frontend separately and proxies /api to the local FastAPI service. The API offers interactive documentation at /api/docs. Development credentials remain in a private backend environment file.

## 9.2 Combined Build

The repository contains a Dockerfile that builds the frontend and serves it with the FastAPI API from one origin. The application uses one backend worker and one replica because image sessions and processing coordination are process-local. Moving to multiple workers or replicas would require shared session coordination and storage.

## 9.3 Operational Maintenance

Maintenance includes keeping dependencies and database migrations controlled, checking temporary-storage capacity, reviewing failures and performance, and validating the deployed API and frontend together. Preset changes should preserve stable identifiers and migration history. Private credentials must remain on the server.

# CHAPTER 10 LIMITATIONS AND FUTURE SCOPE

## 10.1 Current Limitations

LumaLab edits one still image at a time. It does not provide accounts, saved editing history, a durable photo library, batch processing, RAW decoding, or collaboration. Automatic enhancement makes deterministic tonal, colour, and detail decisions; it cannot recreate blurred or missing image information. Temporary sessions end after expiry or restart.

## 10.2 Future Enhancements

Possible future work includes durable user-managed projects, batch workflows, additional export formats, stronger mobile-device verification, and shared storage for multi-replica deployment. Any learned image model should be evaluated separately for image quality, reproducibility, privacy, resource cost, and failure modes before integration.

# CHAPTER 11 CONCLUSION

LumaLab provides a complete browser-based workflow for editing a single photograph, from validated upload through full-resolution JPEG export. Presets and automatic enhancement offer quick starting points, while manual controls, curves, crop, comparison, and 100% detail inspection preserve user choice. The architecture separates the responsive frontend, typed API, image-processing service, temporary session storage, and PostgreSQL preset data.

The present implementation demonstrates the core workflow with documented automated checks and explicit resource and privacy limits. Its next stage is validation in the intended hosting environment and on representative devices and photographs.

# REFERENCES

- LumaLab project README, product overview, architecture, and scope, repository file README.md.
- LumaLab backend developer guide, API, storage, database, and deployment, repository file Backend_doc.md.
- LumaLab frontend developer guide, editing behaviour and verification, repository file Frontend_doc.md.
- LumaLab Photographic Enhancement V3, processing and local verification record, repository file docs/PHOTO_ENHANCEMENT_V3.md.
- LumaLab Crop and Aspect Ratio, crop behaviour and API contract, repository file docs/CROPPING.md.
