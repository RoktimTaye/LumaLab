"""Reproducible local comparisons; no human-quality or Lightroom-parity claim.

Run `python -m scripts.benchmark_enhancement` for the bundled photographs,
or `python -m scripts.benchmark_enhancement --benchmark-24mp` in a fresh process
for peak RSS. Reports stay in private .runtime storage, outside the web root.
"""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import tempfile
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw

from app.config import PROJECT_DIR, RUNTIME_DIR, Settings
from app.schemas.images import Adjustments, NaturalEnhancement
from app.services.enhancement import NEUTRAL, analyze, analyze_v1
from app.services.images import render
from scripts.benchmark_images import peak_rss_bytes


def previous_suggestions(path):
    """Frozen previous four-statistic heuristic for before/after comparison."""
    import cv2
    with Image.open(path) as source:
        image = source.convert("RGB")
    try:
        image.thumbnail((512, 512))
        pixels = np.asarray(image)
        gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV)
        channels = pixels.mean(axis=(0, 1))
        return Adjustments(brightness=int(np.clip(100 + (128 - float(gray.mean())) * .25, 80, 125)),
            contrast=int(np.clip(100 + (50 - float(gray.std())) * .4, 90, 120)),
            saturation=int(np.clip(100 + (90 - float(hsv[:, :, 1].mean())) * .15, 90, 115)),
            warmth=int(np.clip((channels[2] - channels[0]) * .1, -15, 15)), sharpness=0, vignette=0)
    finally:
        image.close()


def benchmark_24mp():
    settings = Settings(_env_file=None, database_url="postgresql://test:test@db.invalid/test?sslmode=require")
    with tempfile.TemporaryDirectory(prefix="enhancement-benchmark-") as temporary:
        path = Path(temporary, "source.png")
        with Image.effect_noise((6000, 4000), 50).convert("RGB") as image:
            image.save(path)
        recipe = NaturalEnhancement(version="natural-v3", exposure_ev=0.65, shadows=0.25, highlights=0.2,
            tone_contrast=0.1, black_point=0.025, clarity=0.15,
            hue_chroma=[0.0, 0.0, -0.1, 0.0, 0.0, 0.0],
            local_exposure=np.linspace(-0.2, 0.2, 64).tolist(), base_luminance=[0.5] * 1024,
            vibrance=0.04, red_gain=1.02, green_gain=1.0, blue_gain=0.98,
            texture=0.4, microcontrast=0.2, detail_noise=0.006, detail_reference_edge=6000)
        start = perf_counter()
        output = render(path, NEUTRAL, settings, preview=False, enhancement=recipe)
        print(json.dumps({"workload": "24mp_natural_recipe_export", "megapixels": 24,
            "export_seconds": round(perf_counter() - start, 3), "jpeg_bytes": len(output),
            "peak_rss_mib": round(peak_rss_bytes() / 1024**2, 1), "engine": "natural-v3",
            "note": "synthetic full-feature render stress test; not an automatic diagnosis of this noise fixture"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="*", type=Path)
    parser.add_argument("--report-dir", type=Path, default=RUNTIME_DIR / "enhancement-report")
    parser.add_argument("--benchmark-24mp", action="store_true")
    args = parser.parse_args()
    if args.benchmark_24mp:
        benchmark_24mp()
        return
    inputs = args.images or [PROJECT_DIR / "frontend/public/images" / name for name in
        ("tea-garden-background.jpg", "alpine.jpg", "forest.jpg", "sunset-road.jpg", "studio-preview-original.jpeg")]
    report = args.report_dir
    report.mkdir(parents=True, exist_ok=True)
    settings = Settings(_env_file=None, database_url="postgresql://test:test@db.invalid/test?sslmode=require")
    sheet = Image.new("RGB", (1260, len(inputs) * 310 + 45), "#111815")
    draw = ImageDraw.Draw(sheet)
    for column, label in enumerate(("Original", "Previous Natural v1", "Photographic v3 (new)")):
        draw.text((column * 420 + 12, 15), label, fill="white")
    records = []
    with tempfile.TemporaryDirectory(prefix="enhancement-review-") as temporary:
        normalized = Path(temporary, "source.png")
        for row, path in enumerate(inputs):
            with Image.open(path) as source:
                original_size = source.size
                image = source.convert("RGB")
            image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            image.save(normalized)
            image.close()
            start = perf_counter()
            result = analyze(normalized, detail_path=path)
            analysis_seconds = perf_counter() - start
            start = perf_counter()
            enhanced = render(normalized, NEUTRAL, settings, preview=True, enhancement=result.recipe)
            preview_seconds = perf_counter() - start
            previous = analyze_v1(normalized)
            outputs = [render(normalized, NEUTRAL, settings, preview=True),
                       render(normalized, NEUTRAL, settings, preview=True, enhancement=previous.recipe), enhanced]
            for column, data in enumerate(outputs):
                with Image.open(BytesIO(data)) as image:
                    image.thumbnail((400, 265), Image.Resampling.LANCZOS)
                    x, y = column * 420 + (420 - image.width) // 2, 50 + row * 310
                    sheet.paste(image, (x, y))
                suffix = ("original", "previous", "natural")[column]
                (report / f"{row + 1}-{suffix}.jpg").write_bytes(data)
            draw.text((12, 50 + row * 310 + 275), path.name, fill="white")
            records.append({"filename": path.name, "source_sha256": sha256(path.read_bytes()).hexdigest(),
                "source_dimensions": original_size, "analysis_seconds": round(analysis_seconds, 4),
                "preview_seconds": round(preview_seconds, 4), "result": result.model_dump()})
    sheet.save(report / "comparison.jpg", quality=95)
    sheet.close()
    (report / "results.json").write_text(json.dumps({"engine": "natural-v3", "scope": "bundled local photos; technical timings only, no human acceptance measurement", "photos": records}, indent=2), encoding="utf-8")
    print(json.dumps({"comparison": str((report / "comparison.jpg").resolve()), "results": str((report / "results.json").resolve()), "photos": len(records)}))


if __name__ == "__main__":
    main()
