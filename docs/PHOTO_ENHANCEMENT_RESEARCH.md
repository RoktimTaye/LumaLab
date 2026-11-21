# Photo enhancement evidence and research decisions

Reviewed on 21 November 2026 for the [implementation plan](PHOTO_ENHANCEMENT_PLAN.md). This record separates source facts from engineering proposals. It is not a report of trained-model performance.

## Evidence used

| Source | Verified fact relevant to this plan | How it changes implementation |
| --- | --- | --- |
| [Adobe Enhance documentation](https://helpx.adobe.com/lightroom/desktop/edit-photos/enhance-details.html) | Denoise, Raw Details, and Super Resolution are distinct functions with format constraints | Separate auto color/tone enhancement from detail restoration and enlargement |
| [Adobe editing controls](https://helpx.adobe.com/lightroom/desktop/edit-photos/edit-photos.html) | Exposure/tone/color/detail and optics are separate parts of the editor | Six existing percentage sliders are insufficient as the full recipe contract |
| [Adobe masks](https://helpx.adobe.com/lightroom/desktop/edit-photos/masking.html) | Local masks support targeted adjustments and mask refinement | Selective editing needs mask artifacts, geometry and explicit local layers |
| [Adobe AI order of operations](https://www.adobe.com/learn/lightroom-cc/web/lightroom-ai-order-of-operations) | Upstream edits can invalidate downstream AI results | Version the graph and invalidate dependent masks/analysis rather than reusing stale outputs |
| [Image-Adaptive 3DLUT](https://github.com/HuiZeng/Image-Adaptive-3DLUT) | Low-resolution network predicts a full-resolution color transform; repository supplies training/inference implementations | Good first global learned baseline; reported GPU timing is not an application SLA |
| [LUTwithBGrid](https://github.com/WontaeaeKim/LUTwithBGrid) | Spatial information is added through bilateral grids; implementation needs compiled extensions | Benchmark as spatial challenger and budget kernel portability |
| [SVDLUT](https://github.com/WontaeaeKim/SVDLUT) | ICCV 2025 repository presents a decomposed spatial LUT design and custom slicing/LUT kernel | Compare current spatial alternative instead of assuming the older global baseline is best |
| [HDRNet](https://github.com/mgharbi/hdrnet) | Reference implementation uses custom TensorFlow operators and documents GPU-only BilateralSliceApply | Use the idea as evidence; do not drop legacy code directly into this CPU container |
| [NILUT](https://github.com/mv-lab/nilut) | Represents continuous color mappings/styles; bundled photo data retains FiveK terms | Useful style component, with separate data restrictions and no automatic scene-understanding guarantee |
| [NAFNet](https://github.com/megvii-research/NAFNet) | Publishes task-specific restoration configurations/checkpoints | Evaluate actual denoising checkpoint in the trained domain, not a generic enhancement label |
| [Restormer](https://github.com/swz30/Restormer) | Official project publishes restoration tasks/checkpoints and inference tooling | Optional restoration challenger, not proof of superior final photographic edits |
| [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Practical restoration/super-resolution using synthetic degradation | Enlargement is optional and separate; inspect invented texture/detail risk |
| [FiveK dataset](https://data.csail.mit.edu/graphics/fivek/) | Expert-edited RAW photography benchmark; two linked Research Licenses govern different image lists | Trace permissions to the applicable data license, not the institution name |
| [FiveK Adobe license](https://data.csail.mit.edu/graphics/fivek/legal/LicenseAdobe.txt), [Adobe/MIT license](https://data.csail.mit.edu/graphics/fivek/legal/LicenseAdobeMIT.txt) | Both limit licensed image use to research without commercial advantage | Exclude from commercial production training without separately resolved permission |
| [PPR10K official README](https://raw.githubusercontent.com/csjliang/PPR10K/master/README.md) | Dataset Agreement limits files to noncommercial research and restricts commercial exploitation of images/derived data; project license is separately Apache 2.0 | The dataset Agreement controls the corpus decision; do not infer commercial photo rights from code license |
| [SIDD official page](https://abdokamel.github.io/sidd/#license) | Explicitly states dataset and associated code repositories are under MIT License | Candidate denoising data with archived notices; do not conflate with independent checkpoint provenance |
| [HDR+ dataset](https://hdrplusdata.org/dataset.html) | Official dataset page specifies CC BY-SA 4.0 and describes burst imagery | Useful burst/RAW resource with attribution/share-alike review, not expert-retouching supervision |
| [libvips internals](https://www.libvips.org/API/current/How-it-works.html), [ICC API](https://www.libvips.org/API/current/method.Image.icc_transform.html) | Region/demand-driven processing and an ICC conversion operation are documented | Prototype a precise, memory-conscious renderer; measure actual pipelines and native dependency behavior |
| [rawpy API](https://letmaik.github.io/rawpy/api/rawpy.Params.html), [official repository](https://github.com/letmaik/rawpy) | Bit depth, transfer/WB/brightness choices are configurable; OpenMP/fork caveat is documented | RAW development needs explicit settings and compatible process startup |
| [ONNX Runtime quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html) | Accuracy and speed vary with quantization method/model/hardware | Establish float reference before adopting quantized inference |
| [LPIPS primary implementation](https://github.com/richzhang/PerceptualSimilarity) | Defines perceptual-comparison tooling and version/input conventions | Use as a diagnostic alongside human review, with exact component/version provenance |
| [IQA-PyTorch](https://github.com/chaofengc/IQA-PyTorch) | Current repository describes PolyForm Noncommercial and applicable additional terms | Do not assume the whole convenience package is freely usable in this commercial workflow |

## Code and checkpoint licensing decisions

The following are inspected source-code terms, except SAM 2 where the official README explicitly includes checkpoints. These findings are not blanket clearance of arbitrary pretrained weights or training data. Select exact commits/artifacts and retain their notices during implementation.

| Component | Reviewed evidence | Decision |
| --- | --- | --- |
| Adaptive 3DLUT | [Apache 2.0 LICENSE](https://raw.githubusercontent.com/HuiZeng/Image-Adaptive-3DLUT/master/LICENSE) | Code candidate; do not assume FiveK-trained weights are cleared |
| LUTwithBGrid | [Apache 2.0 LICENSE](https://raw.githubusercontent.com/WontaeaeKim/LUTwithBGrid/main/LICENSE) | Code candidate; separate FiveK/PPR10K checkpoint lineage |
| SVDLUT | [Official repository license designation](https://github.com/WontaeaeKim/SVDLUT) | Apache 2.0 code candidate; inspect pinned license and dependencies before packaging |
| HDRNet | [Official repository license designation](https://github.com/mgharbi/hdrnet) | Apache 2.0 reference; substantial runtime porting risk |
| NILUT | [MIT LICENSE](https://raw.githubusercontent.com/mv-lab/nilut/main/LICENSE) | Code candidate; bundled FiveK-derived images remain restricted |
| NAFNet | [MIT terms and BasicSR notices](https://raw.githubusercontent.com/megvii-research/NAFNet/master/LICENSE) | Code candidate; audit selected checkpoint separately |
| Restormer | [Official MIT LICENSE.md](https://raw.githubusercontent.com/swz30/Restormer/main/LICENSE.md) | Code candidate; publication license is not the software license |
| Real-ESRGAN | [BSD 3-Clause LICENSE](https://raw.githubusercontent.com/xinntao/Real-ESRGAN/master/LICENSE) | Code candidate; verify precise selected checkpoint scope and upstream components |
| SAM 2 | [README License section](https://github.com/facebookresearch/sam2#license) | Explicit Apache 2.0 for model checkpoints/training/demo code; optional third-party components retain their own terms |
| rawpy | [Official repository](https://github.com/letmaik/rawpy) | Wrapper MIT with bundled/native dependency terms including LibRaw; use documented wheel configuration and retain notices |
| LPIPS | [Official repository](https://github.com/richzhang/PerceptualSimilarity) | BSD-2-Clause repository designation; inspect backbone/weight terms for selected metric artifact |

## Reconciliation of Firecrawl and Nimble findings

The [saved Nimble synthesis](../.nimble/photo-enhancement-research.json) is an intermediate generated research product, not a controlling source. [Firecrawl retrieval receipts](../.nimble/photo-enhancement-firecrawl-receipt.json) preserve the retrieval references. Source descriptions in this document and the plan are the reviewed conclusions.

- **PPR10K:** the initial repository license display looked permissive, but Nimble flagged a separate Agreement. Reading the raw official README confirmed the noncommercial dataset restriction. The final plan excludes those images/derived data from commercial training absent separate permission.
- **SIDD:** the initial excerpt did not establish permissions. Reading the official page's License section confirmed its MIT statement; the final plan records that fact rather than leaving all dataset rights unknown.
- **Restormer:** the Nimble synthesis mixed a paper's license and third-party repository metadata with the code decision. A direct read of the official `LICENSE.md` established MIT software terms. Paper licensing is not used to infer code/weight terms.
- **NILUT:** generated suggestions describing pixelwise transforms as artifact-free are not adopted. A color transform can still create clipping, poor skin hue, banding or gamut problems; the plan requires numerical and human verification.
- **Tiling:** arbitrary overlaps, per-tile histogram matching, and ComfyUI workflow advice are not adopted as production guarantees. Each checkpoint must pass full-frame/tile and local-statistics checks. Independent tile color matching can itself damage photographic consistency.
- **Restoration permissions:** the synthesis's broad claim that all Real-ESRGAN weights are covered by the repository license is not taken as sufficient clearance for every artifact. The chosen checkpoint and dependencies need an explicit record.
- **Study claims:** generated performance numbers and recent preprint skin-metric thresholds were not imported as application benchmarks. The plan's targets are explicitly proposed and require matched local measurement.
- **Sequencing:** Nimble suggested RAW-first development. The repository currently supports rendered images and has a CPU-oriented service; the plan instead prioritizes that existing use case, then adds RAW as a separate measured capability.
- **FiveK internal use:** the generated synthesis broadly suggested internal prototyping. The actual Research License is the controlling evidence; the plan does not assume internal commercial R&D is automatically authorized.

## Repository evidence and calculation checks

Inspected current implementation: `backend/app/services/images.py`, image schemas/routes/storage/config/lifespan, dependency/container declarations, benchmark/tests, generated-contract tooling, `frontend/src/lib/api.ts`, `editor.ts`, `Studio.tsx`, and existing technical documentation. Existing uncommitted crop/application work was observed and preserved. No image-quality benchmark was run because this task creates a plan and does not change runtime behavior.

Transparent planning calculations:

- 24,000,000 pixels × 3 channels × 4 bytes = 288,000,000 bytes = 274.6582 MiB per RGB float32 buffer.
- Four buffers = 1,152,000,000 bytes = 1.0729 GiB, before other process/model allocations.
- Proposed corpus split: 1,400 + 200 + 400 = 2,000 photographs; actual partitioning must preserve groups.
- Illustrative editing labor: 2,000 × 1 target × 5 minutes / 60 = 166.6667 hours, excluding review/rework.

No external timing, acceptance, or dollar-cost claim is presented as measured for this app. Published model speed claims were not translated into service latency promises. Actual data, hardware, permissions and human study outcomes remain implementation inputs.

## Coverage limits

Primary docs/repositories and explicit license text were prioritized. This is a focused engineering investigation, not an exhaustive survey of every enhancement paper or a legal opinion. Page retrievals that returned a 404/error document were excluded as evidence; canonical repository pages or correctly cased/located files supplied the relevant facts. Metadata/UI dates on GitHub are not treated as reproducible artifact version pins. Implementation must select exact commits and weight hashes.

Some Adobe documentation contains inconsistent legacy workflow text and format lists. The plan relies on the general separation of capabilities, not a blanket claim of all supported Lightroom RAW formats. Camera support and release-specific behavior must be checked for the actual comparison build.
