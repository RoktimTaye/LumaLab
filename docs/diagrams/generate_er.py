"""Chen ER diagram of the database actually defined by the SQL migrations."""
from math import cos, sin, radians
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Ellipse

OUT = Path(__file__).resolve().parent
INK = "#172B40"
plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})


def render():
    fig, ax = plt.subplots(figsize=(18, 12))
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.98)
    ax.set(xlim=(0, 18), ylim=(0, 12), aspect="equal")
    ax.axis("off")
    ax.text(0.5, 11.35, "LumaLab | Entity–Relationship Diagram", fontsize=23, weight="bold", color=INK)
    ax.text(0.5, 10.85, "Implemented PostgreSQL schema · Chen notation", fontsize=12, color="#526477")

    underlines = []

    def entity(cx, cy, name, attrs, rx, ry):
        # Plain lines indicate attribute membership; these are not data-flow arrows.
        positions = []
        for name_attr, angle, key in attrs:
            px, py = cx+rx*cos(radians(angle)), cy+ry*sin(radians(angle))
            ax.plot([cx, px], [cy, py], color=INK, lw=1.2, zorder=1)
            positions.append((px, py, name_attr, key))
        ax.add_patch(Rectangle((cx-1.65, cy-0.52), 3.3, 1.04, facecolor="white", edgecolor=INK, lw=1.6, zorder=3))
        ax.text(cx, cy, name, ha="center", va="center", fontsize=13, weight="bold", color=INK, zorder=4)
        for px, py, label, key in positions:
            ax.add_patch(Ellipse((px, py), 2.45, 0.72, facecolor="white", edgecolor=INK, lw=1.3, zorder=3))
            t = ax.text(px, py, label, ha="center", va="center", fontsize=12, color=INK, zorder=4)
            if key:
                underlines.append(t)

    entity(4.8, 6.1, "PRESETS", [
        ("preset_id", 90, True),
        ("preset_name", 50, False),
        ("description", 10, False),
        ("brightness", -30, False),
        ("contrast", -65, False),
        ("saturation", -115, False),
        ("warmth", -150, False),
        ("sharpness", 170, False),
        ("vignette", 130, False),
    ], 3.15, 3.15)

    entity(13.35, 6.1, "SCHEMA_MIGRATIONS", [
        ("version", 90, True),
        ("checksum", 210, False),
        ("applied_at", 330, False),
    ], 2.65, 3.15)

    # Measure actual glyphs so the primary-key underline stays beneath the name.
    fig.canvas.draw()
    for t in underlines:
        box = t.get_window_extent(fig.canvas.get_renderer())
        (x1, y), (x2, _) = ax.transData.inverted().transform([(box.x0, box.y0-2), (box.x1, box.y0-2)])
        ax.plot([x1, x2], [y, y], color=INK, lw=1.15, zorder=5)

    ax.text(0.5, 1.9, "Notation: rectangle = entity; oval = attribute; underlined attribute = primary key; plain line = attribute membership.", fontsize=11, color=INK)
    ax.text(0.5, 1.4, "These tables have no foreign keys or declared relationship; relationship diamonds and cardinalities therefore do not apply.", fontsize=11, color="#526477")
    ax.text(0.5, 0.95, "Photo sessions, image files and editing settings are temporary runtime data, not PostgreSQL tables.", fontsize=11, color="#526477")
    ax.text(0.5, 0.5, "Source: backend/migrations/001_migration_history.sql and backend/migrations/002_presets.sql", fontsize=10, color="#526477")

    for ext in ("png", "svg"):
        fig.savefig(OUT / f"lumalab_er_diagram.{ext}", dpi=240, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    render()
    print(f"Generated Chen ER diagram in {OUT}")
