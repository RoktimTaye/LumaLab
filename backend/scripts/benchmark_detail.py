"""Save actual export-resolution detail crops with and without v3 texture."""

from io import BytesIO
import json
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw

from app.config import PROJECT_DIR, RUNTIME_DIR, Settings
from app.services.enhancement import NEUTRAL, analyze
from app.services.images import normalize, render


def main():
    settings = Settings(_env_file=None, database_url="postgresql://test:test@db.invalid/test?sslmode=require")
    source_path = PROJECT_DIR / "frontend/public/images/tea-garden-background.jpg"
    output_dir = RUNTIME_DIR / "detail-review"
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1560, 1130), "#111815")
    draw = ImageDraw.Draw(sheet)
    for column, label in enumerate(("Original export — 100%", "Same edit, texture off — 100%", "V3 texture on — 100%")):
        draw.text((column * 520 + 8, 12), label, fill="white")
    with tempfile.TemporaryDirectory(prefix="detail-review-") as temporary:
        source_file, proxy_file = Path(temporary, "source.png"), Path(temporary, "proxy.png")
        image, _ = normalize(source_path.read_bytes(), source_path.name, settings)
        width, height = image.size
        image.save(source_file)
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        image.save(proxy_file)
        image.close()
        result = analyze(proxy_file, detail_path=source_file)
        recipe = result.recipe
        without = recipe.model_copy(update={"texture": 0.0, "microcontrast": 0.0})
        records = []
        for column, layer in enumerate((None, without, recipe)):
            data = render(source_file, NEUTRAL, settings, preview=False, enhancement=layer)
            with Image.open(BytesIO(data)) as exported:
                for row, cy in enumerate((0.5, 0.75)):
                    left = max(0, width // 2 - 256)
                    top = max(0, min(height - 512, round(height * cy) - 256))
                    box = (left, top, left + 512, top + 512)
                    with exported.crop(box) as crop:
                        sheet.paste(crop, (column * 520 + 4, row * 548 + 36))
                        crop.save(output_dir / f"crop-{row + 1}-stage-{column}.png")
                    if column == 0:
                        records.append({"crop": row + 1, "source_box": box})
        draw.text((8, 1100), "Actual 512 x 512 source-pixel crops; no enlargement. Texture contrast is not a measure of aesthetic quality.", fill="white")
        sheet.save(output_dir / "detail-comparison.png")
        sheet.close()
        (output_dir / "recipe.json").write_text(json.dumps({"source": source_path.name, "crops": records,
            "result": result.model_dump()}, indent=2), encoding="utf-8")
    print(str((output_dir / "detail-comparison.png").resolve()))


if __name__ == "__main__":
    main()
