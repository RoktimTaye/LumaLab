# Natural enhancement v1

Historical record of the first increment. The current implementation is [Photographic v2](PHOTO_ENHANCEMENT_V2.md), which adds deficit/excess diagnosis, source-derived regional corrections, hue-specific reduction and editing explanations.

Implemented 22 November 2026. This is the first rendering/controller upgrade from the [enhancement roadmap](PHOTO_ENHANCEMENT_PLAN.md), delivered inside the existing API/editor. It is not the full future v2 platform, a pretrained model, or a demonstrated Lightroom equivalent.

## What changed

Auto Enhance now analyzes an uncropped original preview at up to 1024 pixels per edge. Luminance quantiles, tonal range, plausible neutral pixels and conservative low/high-key rules replace the previous four-statistic brightness/contrast/saturation/warmth suggestion.

The returned `natural-v1` recipe describes exposure, shadow lift, highlight roll-off, contrast, vibrance and bounded RGB white-balance gains. Its candidate render is checked for additional near-clipped channels; automatic strength backs off where necessary. Flat images can be left unchanged. Dominant scene colors are not used as white-balance evidence.

The new stage operates in float32 with explicit sRGB transfer functions. Tone changes use luminance and smooth curves; a smooth gamut shoulder limits saturated colors without independently hard-clipping channels. It processes 64-row strips, so it does not allocate a stack of full-resolution float images. Strength blends the entire completed correction in encoded sRGB, continuously from the original at zero to the full transform at one.

This stage runs before the six existing manual controls. Their established pixel behavior and preset values remain intact. JPEGs now embed the output sRGB ICC profile while continuing to omit source EXIF/GPS. This intentionally changes JPEG file metadata; decoded legacy-render pixels are regression-checked against the previous implementation.

## Editor behavior

- Auto Enhance applies a separate recipe and neutral manual controls on success; failed analysis preserves the prior state.
- Auto Enhance strength appears in Adjustments. Manual sliders refine the accepted automatic base; strength changes leave those manual values intact.
- Preview and export send the same recipe, manual values and crop. Recipe changes participate in preview identity and stale-response handling.
- Zero strength restores the original automatic layer. Reset clears the recipe and manual controls while retaining the crop. A preset replaces the automatic layer. Replacing the photo clears both.
- Re-running analysis starts from the original preview, making the base recipe repeatable instead of stacking prior enhancement.
- Late analysis/preview responses cannot overwrite newer edits. Edits cancel outstanding client export work so a stale response cannot trigger a download.

## API integration

`POST /api/v1/images/{id}/enhance` returns `{adjustments, recipe, message}`. Send `recipe` as `enhancement` with both preview and export requests. The six manual adjustment fields remain required as before; omitting `enhancement` preserves the legacy manual path. The returned manual adjustments are neutral because the recipe contains the actual automatic transformation. Deploy frontend and backend together; a client that consumes only the six returned sliders will not apply this new automatic result.

The recipe has an explicit `natural-v1` version, finite bounded numbers, forbidden extra fields and no paths or model URLs. It contains mathematical parameters rather than stored artifact handles; it does not introduce a cross-session artifact store or persistent image history. Existing authorization, private caching, expiry, file quotas and processing permits still apply.

Main implementation: `backend/app/services/enhancement.py`. Integration: image schemas/routes/renderer, generated TypeScript contracts, API client and Studio state.

## Verification

The backend regression suite covers existing uploads, profiles, orientation, access tokens, lifecycle, crop, manual presets and error behavior, plus new photographic properties:

- Underexposed gradients become brighter without new clipping or reversed tone order.
- Night gradients stay dark; warm/saturated scene colors do not trigger inappropriate automatic neutralization.
- Plausible neutral casts reduce conservatively; flat and balanced images avoid aggressive corrections.
- Extreme bounded tone curves remain finite, monotone and neutral on grayscale ramps.
- Saturated green gradients retain variation rather than flattening at the gamut boundary.
- Strength varies continuously, and zero is exactly neutral.
- Strip rendering matches whole-array evaluation without seams.
- A frozen recipe is repeatable, crop-consistent, and produces close preview/export pixels at different resolutions.
- Unknown versions, nonfinite values and oversized/invalid parameters are rejected before rendering.

Frontend checks exercise strength, manual refinement, repeated analysis, presets/reset, identical export state, stale analysis, crop, mobile reflow and accessibility. The existing editor regression suite checks upload failures, response races, keyboard/touch behavior and downloads. These are technical/behavioral checks, not a professional blind preference study.

Verification completed locally: **125 backend tests and 530 subtests**, **11 frontend unit tests**, generated-contract check, and production build passed. Both new enhancement scenarios passed in Chrome, Firefox and WebKit (six browser cases). The existing ten-case Chrome editor suite and two Chrome crop cases also passed.

Reproduce from `backend/`:

```powershell
uv run --locked pytest -q
uv run --locked python -m scripts.benchmark_enhancement
uv run --locked python -m scripts.benchmark_enhancement --benchmark-24mp
```

The comparison script saves an Original / Previous Auto / Natural v1 contact sheet, individual JPEGs and recipe/timing receipts in `backend/.runtime/enhancement-report/`, outside the served web root. The bundled examples are diagnostic coverage, not a representative acceptance-rate benchmark. The previous column reproduces the previous four-statistic suggestions for comparison.

From `frontend/`, run the unit tests, contract check and build. Connected browser tests use the repository's loopback-only `scripts.e2e_server`, with simulated database resources; do not deploy that test server.

```powershell
npm test
npm run contracts:check
npm run build
npx playwright test tests/e2e/enhancement.spec.ts --project=chromium --project=firefox --project=webkit
```

## Local resource measurement

One final local synthetic 6000×4000 export with nonzero exposure, shadow/highlight, contrast, vibrance and white-balance parameters took **10.232 seconds**, with **298.2 MiB process peak working set** and a 17,281,483-byte JPEG. This is a single fresh-process diagnostic on Windows/Python 3.11.9, reporting 12 logical CPUs (Intel family 6/model 141); it is not p95, a production SLA, or a 4-vCPU benchmark. The synthetic PNG setup and source generation are outside the reported export timer; process peak memory includes setup. Run the command on the actual deployment hardware before changing concurrency or capacity.

Profiling identified generic three-channel reductions as a material cost. Fixed-channel extrema and luminance operations reduce that cost while retaining the photographic property tests. No approximation of the transfer functions or model quantization was introduced. Concurrency under simultaneous preview/export workloads still needs deployment-specific capacity measurement.

## Remaining work and practical limits

The source is still the existing normalized 8-bit RGB working image, and the output remains an SDR JPEG. Float32 correction prevents intermediate rounding inside the new automatic stage; it cannot recover source precision already lost at decoding or restore clipped sensor data. Manual legacy controls still use their existing processing path.

Low/high-key and neutral-pixel rules are conservative heuristics, not semantic understanding. They can confuse intentional color/lighting with capture errors; the strength control and original comparison remain important. Full-resolution noise estimation, semantic/skin masks, local subject corrections, RAW development, higher-bit-depth export and async model jobs are not implemented in this increment. No new trained-model dependency or inference service was installed.

The next learned stage requires rights-cleared professional editing pairs, matched Lightroom references, and the blind evaluation specified in the roadmap. Production training on the reviewed FiveK/PPR10K data remains excluded without separate permission. The present regression tests establish useful photographic invariants and integration correctness; they do not establish a near-final acceptance percentage or Lightroom parity.
