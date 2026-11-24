"""Report-ready UML use case diagram of the implemented LumaLab interface."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, Rectangle

OUT = Path(__file__).resolve().parent
INK = "#172B40"
plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})


def render():
    fig, ax = plt.subplots(figsize=(13, 19))
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.98)
    ax.set(xlim=(0, 13), ylim=(0, 19), aspect="equal")
    ax.axis("off")
    ax.text(0.5, 18.35, "LumaLab | Use Case Diagram", fontsize=23, weight="bold", color=INK)
    ax.text(0.5, 17.85, "UML notation · implemented photo editing features", fontsize=12, color="#526477")

    # A system boundary contains use cases; the human actor stays outside it.
    ax.add_patch(Rectangle((4.4, 2.8), 8.1, 14.5, fill=False, edgecolor=INK, lw=1.4))
    ax.text(8.45, 16.94, "LumaLab Photo Editing System", ha="center", va="center", fontsize=14, weight="bold", color=INK)

    # Standard UML human actor.
    x, y = 1.75, 10.0
    ax.add_patch(Circle((x, y+0.75), 0.24, fill=False, edgecolor=INK, lw=1.6))
    ax.plot([x, x], [y+0.51, y-0.24], color=INK, lw=1.6)
    ax.plot([x-0.55, x+0.55], [y+0.22, y+0.22], color=INK, lw=1.6)
    ax.plot([x-0.46, x, x+0.46], [y-0.92, y-0.24, y-0.92], color=INK, lw=1.6)
    ax.text(x, y-1.25, "User", ha="center", va="center", fontsize=14, weight="bold", color=INK)

    use_cases = [
        "Upload or replace\na photograph",
        "Try a sample photograph",
        "Apply a preset",
        "Adjust light, colour\nand detail",
        "Adjust RGB curves",
        "Crop a photograph",
        "Automatically enhance\na photograph",
        "Compare original\nand edited images",
        "Inspect image at\n100% detail",
        "Reset adjustments",
        "Export edited image\nas JPEG",
    ]
    for i, label in enumerate(use_cases):
        cy = 16.0-i*1.22
        # Undirected solid associations show participation, not sequence/data flow.
        ax.plot([x+0.55, 5.5], [y+0.22, cy], color=INK, lw=1.1, zorder=1)
        ax.add_patch(Ellipse((8.45, cy), 5.9, 0.91, facecolor="white", edgecolor=INK, lw=1.4, zorder=2))
        ax.text(8.45, cy, label, ha="center", va="center", fontsize=12.5, color=INK, linespacing=1.25, zorder=3)

    notes = [
        "Notation: stick figure = actor; oval = use case; rectangle = system boundary.",
        "Solid lines are actor–use case associations; they do not indicate execution order.",
        "Precondition for editing, comparison, reset and export: a photograph is loaded.",
        "All features are available without an account. One actor represents the photo editor.",
    ]
    for i, note in enumerate(notes):
        ax.text(0.5, 2.0-i*0.36, note, fontsize=10.4, color="#526477")

    for ext in ("png", "svg"):
        fig.savefig(OUT / f"lumalab_use_case_diagram.{ext}", dpi=240, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    render()
    print(f"Generated UML use case diagram in {OUT}")
