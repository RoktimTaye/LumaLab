# Photographic enhancement v2

Historical implementation record. The current engine is [Photographic v3](PHOTO_ENHANCEMENT_V3.md).

Implemented 22 November 2026. This upgrade addresses the reported near-invisible effect of Natural v1. It diagnoses measurable deficits and excesses, builds a versioned edit plan, and renders the same plan at preview/export resolution. It uses explicit photographic rules and source-derived maps; it is not a learned retouching model or a claim of Lightroom parity.

## Decisions now made

| Observed signal | Chosen response |
| --- | --- |
| Dark or overly bright midtones | Increase or decrease exposure with a smooth highlight shoulder |
| Dense shadows with retained variation | Open existing detail; limit lifting when resized-image noise indicators are high |
| Strong bright tones | Pull back the upper tonal range in perceptual luminance |
| Lifted black floor / weak bright anchor | Deepen dark-tone separation or gently expand restrained whites |
| Weak or excessive midtone range | Add or soften contrast, rather than always increasing it |
| Different regional brightness | Apply a smooth source-derived exposure field with pixel-luminance guidance |
| Excessive saturation in individual hue ranges | Reduce those colors selectively; keep warm-hue changes conservative |
| Subdued color | Use restrained vibrance, weighted away from already saturated pixels |
| Soft local separation with little noise evidence | Add bounded local definition; suppress changes across strong boundaries |
| Grain-like variation, low/high-key intent, uniform ramps | Reduce or skip corrections that would amplify noise or force a style |

These signals are editing hypotheses, not semantic certainty. Green is not automatically identified as foliage, and a bright upper region is not asserted to be sky. The engine does not detect faces, recognize objects, reconstruct missing detail, remove noise or erase objects.

## Research applied

The [collected evidence](PHOTO_ENHANCEMENT_RESEARCH.md) distinguishes global color/tone transforms from spatial corrections and restoration. Adobe documents separate global controls and local masks; HDRNet and LUTwithBGrid motivate predicting compact transformations from a smaller image and applying them at full resolution. This implementation uses its own deterministic regional field and bounded guide-based operators; it does not load those projects' pretrained models or claim their published benchmark results. [Adobe controls](https://helpx.adobe.com/lightroom/desktop/edit-photos/edit-photos.html), [Adobe masking](https://helpx.adobe.com/lightroom/desktop/edit-photos/masking.html), [HDRNet](https://github.com/mgharbi/hdrnet), [LUTwithBGrid](https://github.com/WontaeaeKim/LUTwithBGrid).

The data/weight restrictions established during research remain in force. No FiveK/PPR10K photos or unverified retouching checkpoints were added to production training or inference. No user photos are uploaded to an external model by this implementation.

## Render and state contract

`NaturalEnhancement.version` now supports `natural-v1` and `natural-v2`. Existing v1 recipes keep their previous renderer; omitted version still defaults to v1 for compatibility. New automatic analysis explicitly emits v2. New photographic fields are rejected on v1 recipes to prevent ambiguous interpretation.

V2 adds black/white anchors, signed midtone contrast, local definition, six circular hue-chroma controls, an 8×8 regional exposure map, and an optional 32×32 luminance guide. Arrays have exact permitted lengths, finite bounded values, and no filesystem/model references. Both maps are derived once from the original, not independently from preview/export/cropped pixels.

The exposure field is bilinearly sampled in full-source normalized coordinates. Positive values predominantly affect darker pixels; negative values predominantly affect bright pixels. Local definition uses a bilateral-smoothed guide with an edge gate and a bounded delta, reducing halos when the coarse guide disagrees with sharp source boundaries. The source-coordinate region is carried through crop and strip rendering, which prevents cropped images from stretching the maps across a new frame.

Tone changes operate on perceptual luminance after explicit linear-light exposure/white-balance operations. Chroma is adjusted around the target luminance, with soft circular interpolation between hue controls. Gamut compression retains hue and avoids independent channel clipping. Strength blends the completed encoded-sRGB transformation continuously with the original. Float intermediates remain strip-bounded; the existing manual six-control stage follows.

`/enhance` also returns `assessment`: bounded issue/action records for the automatic base. The editor displays these as **Editing decisions**, retains them during manual refinement/crop, and clears them with reset/presets/replacement. It identifies a zero-strength layer as off. Findings describe the chosen automatic plan, not an independent expert quality score.

## Tea-garden regression

The matching bundled tea-garden image now receives highlight control, a deeper black anchor, regional lighting correction, approximately 15% negative green-chroma control, and bounded local definition. Exposure is not arbitrarily raised and every color is not globally boosted.

On a 768-edge diagnostic copy, the mean absolute RGB-channel change from the original increased from **2.40/255 with v1 to 8.99/255 with v2**. This checks that the reported near-invisible behavior changed; larger pixel differences do not establish better aesthetics. Actual before/after review remains necessary. The generated comparison includes Original / Previous Natural v1 / Photographic v2 for tea garden, alpine, forest, sunset road and evening water scenes.

Reproduce from `backend/`:

```powershell
uv run --locked python -m scripts.benchmark_enhancement --report-dir .runtime/photographic-v2-review
```

The contact sheet, individual JPEGs and source/recipe receipts stay outside the served web root in `.runtime/photographic-v2-review/`.

## Verification and resource limits

Property tests cover different corrections for the same color in different regions, hue-specific excess reduction, conservative warm colors, noise-gated definition, opposite edit plans for different inputs, continuous strength, monotone tonal extremes, exact source-map coordinates, strip/crop consistency, malformed/oversized/nonfinite fields, and the reported tea-garden case. Tests also retain the original balanced-ramp/night/neutral-color invariants. These checks do not substitute for professional preference evaluation.

The full backend suite passed with **134 tests and 530 subtests**, along with **11 frontend unit tests**, generated-contract checks and production build. Three connected enhancement scenarios passed in Chrome, Firefox and WebKit (nine browser cases): strength/manual/export/reset; visible tea-garden assessment plus crop/export; and stale-response/mobile behavior. Browser checks used isolated ports so the existing editor's sessions were not reset.

A fresh-process synthetic 24 MP render with all v2 feature types enabled took **17.499 seconds** and **327.1 MiB peak working set** on the local Windows/Python 3.11.9 environment. This is a stress diagnostic, not p95 or a deployment SLA; the noise fixture deliberately exercises a full recipe rather than its normal noise-aware automatic decision. Its extra quality stages cost more compute than v1. Measure actual service load before increasing concurrency.

## Applying to the running editor

The backend must restart or reload to load the new Python code. A read-only check during development found the existing port-8000 backend still advertised `natural-v1` only. Updating the frontend alone therefore does not enable the new editing decisions.

Backend sessions are process-local and temporary. Export desired work before restarting; refresh Studio and upload the original again afterward. The original file on the user's device is unaffected. For future local development, `uv run --locked python -m app --reload` enables code reload, which also ends process-local sessions when backend files change.

## Remaining limits

Input still passes through the existing normalized 8-bit RGB source and output is SDR JPEG. Region/noise/color indicators are heuristic and can misread intent. Noise is estimated on a resized view, not at source-scale; it gates amplification rather than performing denoising. Spatial maps are smooth tonal guides, not semantic subject/skin masks. High-bit-depth RAW processing, trained expert preferences, true restoration and a matched Lightroom/human study remain separate roadmap work. The amount slider and original comparison remain available for subjective decisions.
