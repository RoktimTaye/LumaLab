# LumaLab vs Snapseed — remaining feature checklist

Compared on 24 November 2026 against the current repository, Google Play listing and official Snapseed Help. This is a feature inventory, not a claim that algorithms or rendering match. Android/iOS versions can differ; Google’s older Help index and current store listing do not enumerate exactly the same tools. Entries below combine both references. Unverified platform-specific details remain explicitly conditional.

Checked boxes describe existing LumaLab capabilities observed in code, not pixel-for-pixel Snapseed parity. Unchecked boxes are remaining implementation work. Sub-controls below are proposed acceptance criteria for LumaLab unless the linked reference explicitly documents them. A preset with a matching name does not implement the corresponding effect.

## Already available

- [x] JPG, PNG and WebP upload with format and dimension validation.
- [x] Manual brightness, contrast and saturation.
- [x] Manual temperature/warmth and green–magenta tint.
- [x] Manual sharpening.
- [x] Crop with freeform and common aspect ratios.
- [x] Master RGB and individual channel curves, including point deletion.
- [x] Fixed-centre darkening vignette.
- [x] Automatic tonal enhancement with adjustable strength.
- [x] Built-in preset catalogue with grouped, collapsible sections.
- [x] Load an individual saved backend preset on selection.
- [x] Immediate local adjustment/curve previews and server-rendered previews.
- [x] Before/after split comparison.
- [x] Full-resolution detail inspection.
- [x] JPEG download at fixed quality.
- [x] Reset current adjustments while retaining the original image.

## 1. Tune Image — partial

Brightness, contrast, saturation and warmth exist. Remaining controls follow the [Tune Image reference](https://support.google.com/snapseed/answer/6157802); ordinary brightness is not a substitute for RAW exposure.

- [x] Independent highlights adjustment.
- [x] Independent shadows adjustment.
- [x] Ambiance-style tonal balancing.
- [x] An explicit exposure control, with its behaviour documented.
- [x] Live histogram with clipping feedback.
- [ ] Per-tool reset without clearing unrelated edits.

## 2. Details — partial

Sharpening exists; automatic enhancement contains texture processing, but users cannot edit it as an independent Details tool. See the [official tool index](https://support.google.com/snapseed/answer/6183571?hl=en).

- [x] Independent Structure/texture slider.
- [x] Separate structure and sharpening controls.
- [ ] Preview fine detail at native scale while adjusting.

## 3. Crop, rotate and geometry — partial

Crop exists. The geometry work below must define its order relative to crop and future masks; see [Snapseed’s current listing](https://play.google.com/store/apps/details?id=com.niksoftware.snapseed&hl=en).

- [x] Rotate left/right in 90-degree steps.
- [x] Free-angle straightening.
- [x] Horizontal/vertical flip as a geometry extension.
- [ ] Automatic horizon alignment, if supported by a suitable detector.
- [ ] Vertical perspective correction.
- [ ] Horizontal perspective correction.
- [ ] Scale and free-corner geometry controls.
- [ ] Optional edge filling after perspective correction.
- [ ] Canvas expansion with plain fills.
- [ ] Content-aware filling for expanded edges.
- [x] Consistent crop coordinates and export dimensions after transforms.

## 4. White balance — partial

Manual temperature and tint exist; neutral-point automation remains separate work.

- [x] Neutral-point eyedropper.
- [x] Dedicated automatic white-balance action.
- [x] Sample from the correct original/working colour space.
- [ ] Reset white balance independently.

## 5. Brush and local adjustments — missing

Brush, Selective and Healing are listed in the [official tool index](https://support.google.com/snapseed/answer/6183571?hl=en). Proposed interaction requirements:

- [ ] Brush exposure/dodge and burn.
- [ ] Brush brightness, saturation and temperature.
- [ ] Brush size, strength and feathering.
- [ ] Mask eraser and visible mask overlay.
- [ ] Stroke undo/redo.
- [ ] Touch-safe zoom/pan while painting.
- [ ] Selective control points placed on the photo.
- [ ] Point radius and brightness/contrast/saturation controls.
- [ ] Move, duplicate and delete control points.
- [ ] Selection based on colour/tonal similarity rather than radius alone.
- [ ] Healing brush and spot removal.
- [ ] Healing stroke history and undo.
- [ ] Preview/export consistency for every mask and healing operation.

## 6. Vignette — partial

The current slider only darkens fixed corners. The [Vignette reference](https://support.google.com/snapseed/answer/6181707) documents movable centre, size, and separate inner/outer brightness.

- [ ] Move the vignette centre.
- [ ] Change its size/radius.
- [ ] Brighten or darken the outer region.
- [ ] Adjust inner brightness separately.
- [ ] Touch controls and independent reset.

## 7. Text, frames and compositing — missing

Text/Frames appear in the [tool index](https://support.google.com/snapseed/answer/6183571?hl=en); Double Exposure appears in the [store listing](https://play.google.com/store/apps/details?id=com.niksoftware.snapseed&hl=en). Proposed controls:

- [ ] Text entry and font/style selection.
- [ ] Text colour, opacity, alignment and size.
- [ ] Move, rotate and delete text overlays.
- [ ] Frame styles and adjustable border width.
- [ ] Import a second image for double exposure.
- [ ] Align, scale and rotate the second image.
- [ ] Blend modes and opacity.
- [ ] Mask the composite locally.
- [ ] Export overlays at full resolution without low-resolution text or borders.

## 8. Classic adjustable effects — missing or partial

Named looks already exist, but these tool families from the [official index](https://support.google.com/snapseed/answer/6183571?hl=en) need dedicated adjustable rendering:

- [ ] Lens Blur with focus region and transition controls.
- [ ] Glamour Glow.
- [ ] Tonal Contrast.
- [ ] HDR Scape-style tone mapping.
- [ ] Drama.
- [ ] Grunge.
- [ ] Grainy Film.
- [ ] Vintage.
- [ ] Retrolux.
- [ ] Noir.
- [ ] Black & White with tonal/filter choices beyond saturation zero.
- [ ] Independent intensity/reset for each effect.
- [ ] Stable grain/texture between preview and export.

## 9. Newer colour and optical tools — missing

These families appear in the [current Google Play listing](https://play.google.com/store/apps/details?id=com.niksoftware.snapseed&hl=en), updated 16 November 2026. Implementations below need explicit quality targets; their presence in the listing does not establish algorithm equivalence.

- [ ] Per-colour HSL adjustments.
- [ ] Tonal-range colour grading: shadows, midtones and highlights.
- [ ] Dehaze.
- [ ] Film-stock simulation engine beyond six-slider presets.
- [ ] Halation.
- [ ] Bloom.
- [ ] Independent film grain controls.
- [ ] Directional motion blur.
- [ ] Motion effect targeting subject, background or scene.
- [ ] Depth-aware lens blur/bokeh.
- [ ] One-tap subject/background masks.
- [ ] Manual refinement of automatically generated masks.

## 10. Portrait and face tools — missing

Face/Portrait are documented in the [tool index](https://support.google.com/snapseed/answer/6183571?hl=en) and current listing. Specific controls and parity need evaluation against the chosen platform version.

- [ ] Face detection with selectable subjects.
- [ ] Face-aware lighting adjustments.
- [ ] Skin smoothing that preserves texture.
- [ ] Eye-detail enhancement.
- [ ] Head pose correction.
- [ ] Facial-feature refinement controls.
- [ ] Graceful behaviour when no usable face is detected.

## 11. RAW development — missing

LumaLab currently accepts raster images only. Google documents platform-dependent RAW support and a development stage in [Develop: RAW Editing](https://support.google.com/snapseed/answer/6312515?hl=en&ref_topic=6155507).

- [ ] Define and document supported RAW camera formats.
- [ ] Decode DNG and supported camera RAW files.
- [ ] Preserve high-bit-depth data during development.
- [ ] RAW exposure adjustment.
- [ ] RAW highlight/shadow recovery.
- [ ] RAW contrast and structure.
- [ ] RAW temperature/tint before conversion to the working image.
- [ ] Safe decoding limits and unsupported-format feedback.

## 12. History, Stacks and saved projects — missing

Reset exists, but editable history does not. [Stacks](https://support.google.com/snapseed/answer/6155543?hl=en&ref_topic=6155507) supports revisiting applied operations and copying edits between photos. Proposed LumaLab requirements:

- [x] Undo and redo across edits.
- [ ] Editable ordered operation stack.
- [ ] Reopen and change an applied operation.
- [ ] Remove or disable an operation.
- [ ] Insert an operation at a defined stage.
- [ ] Per-operation masking and mask inspection.
- [ ] Copy/paste edits between photos.
- [ ] Revert the complete project, including crop and future masks.
- [ ] Save and reopen editable projects beyond the temporary session.
- [ ] Recover unsaved work after refresh or interruption.

## 13. Looks, LUTs, sharing and batch editing — missing

The [current listing](https://play.google.com/store/apps/details?id=com.niksoftware.snapseed&hl=en) names custom presets, LUTs, QR Looks, packs, community looks and batch editing. The existing backend catalogue covers built-in presets only.

- [ ] Save a custom look from current edits.
- [ ] Name, rename and delete user looks.
- [ ] Adjust look intensity.
- [ ] Import XMP presets with an explicit supported-property mapping.
- [ ] Import/export QR Looks where the format is available and compatible.
- [ ] Import CUBE and PNG LUTs.
- [ ] LUT intensity and colour-space handling.
- [ ] Import ZIP packs with bounded extraction and validation.
- [ ] Share/export custom looks.
- [ ] Community discovery equivalent, including publishing and moderation requirements.
- [ ] Select multiple photos and apply a look/stack in a batch.
- [ ] Batch progress, cancellation and individual failure reporting.
- [ ] Download batch results without losing individual image resolution.

## 14. Viewer, export and device workflow — partial

Split comparison, detail view and JPEG export already exist. Google documents [editing gestures](https://support.google.com/snapseed/answer/6155517?hl=en) and [save/share/export](https://support.google.com/snapseed/answer/6155519?hl=en&ref_topic=6155507). Remaining tasks combine comparable workflows and practical browser requirements:

- [ ] Continuous pinch-to-zoom and pan in the main canvas.
- [ ] Press-and-hold original comparison.
- [ ] Export size controls.
- [ ] Export quality controls.
- [ ] Save an editable version separately from a flattened copy.
- [ ] Share through supported device/browser sharing APIs.
- [ ] Document colour profile and metadata behaviour at export.
- [ ] Camera capture with editable real-time looks, where browser support permits.
- [ ] Document native camera/file-system features that cannot be reproduced by this web app.

## Delivery order and completion rule

1. Geometry, independent tone controls, white-balance automation and histogram.
2. History/Stacks before adding complex local or layered edits.
3. Brush, Selective, Healing and improved vignette.
4. Text, frames, double exposure and classic effects.
5. HSL, grading, advanced optical effects and smart masks.
6. RAW, portrait models, user libraries, batch and device workflows.

A feature is complete only when its controls, validation, immediate preview strategy, server render, full-resolution export, reset/history behaviour and touch interaction are implemented. Compare quality against representative photos rather than a matching tool name. This checklist is an inventory and proposed implementation scope, not an assertion that every item exists on every Snapseed platform or that undocumented proprietary behaviour is reproducible.

## Foundation batch implementation notes

Implemented: highlights, shadows, ambience-style tone mapping, exposure in EV, structure, 90-degree rotation, flips, manual straightening, preview histogram, white-balance sampling/estimation and session undo/redo. The tone mapping and structure algorithms are LumaLab implementations, not Snapseed algorithm parity.

Exposure multiplies normalized code values by 2^EV before the other manual tone controls; this is a raster exposure simulation, not RAW sensor recovery. Straightening trims a conservative centre rectangle; crop is evaluated in original coordinates before geometry. Histogram updates immediately from a bounded local pixel sample during edits, including tone and curve changes. It identifies the local estimate as Live and refines the measurements from the server JPEG when ready. White balance samples the normalized original preview; auto estimates grey-world balance from midtones and can be wrong for strongly coloured scenes.

Group Reset buttons reset Light, Colour or Detail values independently; a separate geometry reset is available. RGB curves retain their own resets. Global reset now also clears crop. Undo/redo records settled snapshots (200ms grouping, up to 100 states per uploaded image); it is not an editable operation stack or a saved project. Reset of future masks remains open.

Validation: production build, three backend tests for tone mapping/geometry/validation, and a Chrome workflow check covering upload, exposure, undo/redo, rotation, straightening, preview readiness, automatic white balance and viewport overflow at desktop/mobile sizes. Local structure preview is approximate; export uses the source-scale server implementation. Additional browser engines and large-image stress checks remain outstanding.
