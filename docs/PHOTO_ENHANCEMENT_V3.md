# Photographic enhancement v3

Implemented 22 November 2026. V3 adds source-scale texture analysis and restrained fine/medium detail enhancement to the tonal, regional and color decisions in [v2](PHOTO_ENHANCEMENT_V2.md). The editor also provides a **100% detail** view of the actual export, because a scaled preview hides changes to small structures.

## Processing decisions

The analyzer reads up to five distinct 256×256 patches at original resolution from the normalized source: center and quarter positions. It measures medium-band structure, hard-edge coverage and median-residual noise in plausible flat midtones. It uses a lower-quartile estimate among credible noise samples to reduce confusion between foliage texture and noise; uncertain evidence caps the detail response. This is sampled evidence, not a complete noise model or semantic classification.

Fine texture and medium-scale microcontrast are separate luminance bands. Their contribution is gated by local activity, source noise, brightness and edge strength. Strong-edge exclusion extends into the surrounding blur footprint to reduce halos. Warm moderately saturated colors receive less texture through a color proxy; this does not detect skin or faces. Smooth areas stay smooth, and noise-heavy sources skip automatic texture. Each delta is bounded and limited by available channel headroom. No new objects or missing detail are reconstructed.

The recipe records `texture`, `microcontrast`, `detail_noise` and `detail_reference_edge`. Filtering uses source-relative scales so preview/export share a consistent intent. Fine detail is best judged in the native viewer. Automatic settings remain bounded below the maximum API limits; users can blend the complete automatic layer with the strength slider. Old v1/v2 recipes retain their existing rendering behavior and reject v3 detail settings.

The renderer processes 64-row cores with original-pixel neighborhood halos. It retains the original trailing rows before replacing each core, avoiding repeated filtering of already edited pixels. This gives neighboring strips the same input context without allocating full-image floating-point intermediates. Crop coordinates continue to sample the same source-derived tonal maps.

Source analysis shares the heavy upload/export permit because decoding the native image consumes memory. There are still two separate preview permits. Busy operations return the existing retryable capacity error.

## Inspection workflow

1. Upload a photo and apply Auto Enhance.
2. Review Editing decisions, including the native-sampling observation.
3. Open **100% detail**. The modal renders the current crop, manual settings and enhancement through the export endpoint, displays the JPEG at its natural pixel dimensions, and scrolls to inspect it.
4. Close it to refine strength or controls, then export the finished image.

The modal includes loading and failure states, keyboard dismissal, focus restoration and mobile scrolling. It aborts abandoned requests and revokes private blob URLs on cleanup. Server work already dispatched may finish after client cancellation; the existing processing permit remains held until that work finishes. Native rendering is deliberately optional because it is more expensive than the editor preview.

## Verification and reproducibility

- Backend: 142 tests and 530 subtests passed after the detail renderer change; the 49 image API tests and 300 subtests passed again after adding the source-analysis capacity assertion.
- Detail tests cover textured versus smooth regions, noise suppression decisions, warm-color protection, strong-edge halos, strip/whole-image agreement, zero/partial strength, native evidence hidden by a proxy and version/schema compatibility.
- All 11 frontend unit tests, generated API contract validation and production TypeScript/Vite build passed. Both detail-view scenarios passed on Chromium, Firefox and WebKit; three enhancement regression scenarios passed on Chromium. Browser verification covers native pixel sizing, authenticated export settings, accessibility, blob cleanup, keyboard focus, mobile overflow and failure/retry behavior. The native-render test waits for completion with a longer bounded timeout than ordinary preview interactions.
- `python -m scripts.benchmark_detail` generates a source-pixel contact sheet comparing original, the same tonal/color edit without texture, and v3 texture. The bundled tea-garden output is under `backend/.runtime/detail-review/`; these private runtime artifacts are ignored by Git.
- `python -m scripts.benchmark_enhancement --benchmark-24mp` measured **47.784 seconds** and **379.6 MiB peak process working set** for a synthetic 6000×4000 full-feature v3 JPEG render on this Windows machine. This is a local stress workload, not an automatic diagnosis, isolated throughput guarantee, hosted capacity measurement or perceptual quality score. Validate hosting timeouts and memory with real maximum-size inputs.

The research and future learned-model work remain in [the evidence record](PHOTO_ENHANCEMENT_RESEARCH.md) and [the professional plan](PHOTO_ENHANCEMENT_PLAN.md). This release uses deterministic image analysis; it does not install a neural restoration model, denoise the image or establish Lightroom parity. Source blur, compression damage and missing information limit the available result.
