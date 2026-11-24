"""Render the report DFDs from the implemented LumaLab data flows."""
from pathlib import Path
from math import sqrt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyArrowPatch

OUT = Path(__file__).resolve().parent
INK = "#172B40"
BLUE = "#EAF2FA"
plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})


def canvas(width, height, title, subtitle):
    fig, ax = plt.subplots(figsize=(width, height))
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.02, top=0.98)
    ax.set(xlim=(0, width), ylim=(0, height), aspect="equal")
    ax.axis("off")
    ax.text(0.5, height - 0.6, title, fontsize=23, weight="bold", color=INK)
    ax.text(0.5, height - 1.06, subtitle, fontsize=11, color="#526477")
    return fig, ax


def entity(ax, x, y, w, h, label, repeated=False):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=INK, lw=1.5))
    ax.text(x+w/2, y+h/2, label, ha="center", va="center", fontsize=12, color=INK)
    if repeated:
        ax.plot([x+w-0.25, x+w], [y, y+0.25], color=INK, lw=1.2)


def process(ax, cx, cy, radius, number, label):
    ax.add_patch(Circle((cx, cy), radius, facecolor="white", edgecolor=INK, lw=1.5))
    ax.text(cx, cy+radius*0.58, number, ha="center", va="center", fontsize=12, weight="bold", color=INK)
    ax.text(cx, cy-radius*0.12, label, ha="center", va="center", fontsize=11, color=INK, linespacing=1.25)


def store(ax, x, y, w, h, number, label):
    # Yourdon-DeMarco: two parallel lines, with neither side closed.
    ax.plot([x, x+w], [y, y], color=INK, lw=1.5)
    ax.plot([x, x+w], [y+h, y+h], color=INK, lw=1.5)
    ax.text(x+w/2, y+h/2, number+"\n"+label, ha="center", va="center", fontsize=11, color=INK, linespacing=1.25)


def flow(ax, x1, x2, y, label, below=False, size=10):
    ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>", mutation_scale=13, lw=1.15, color=INK, shrinkA=2, shrinkB=2))
    ax.text((x1+x2)/2, y+(-0.13 if below else 0.13), label, ha="center", va="top" if below else "bottom", fontsize=size, color=INK, linespacing=1.35)


def save(fig, name):
    for extension in ("svg", "png"):
        fig.savefig(OUT / f"{name}.{extension}", dpi=240, facecolor="white")
    plt.close(fig)


def level0():
    fig, ax = canvas(17, 9, "LumaLab | DFD Level 0", "Context diagram · Yourdon–DeMarco notation")
    entity(ax, 0.6, 1.8, 2.8, 5.6, "E1\n\nUser\n(photo editor)")
    process(ax, 13.1, 4.6, 3.1, "0", "LumaLab\nPhoto Editing\nSystem")
    flows = [
        (6.9, True, "Photograph and filename"),
        (6.05, False, "Image session details and access token"),
        (5.2, True, "Preset request; enhancement request;\nedit settings and preview request"),
        (4.2, False, "Preset definitions; enhancement recipe and findings;\noriginal and edited previews"),
        (3.25, True, "Export settings and request; deletion request"),
        (2.35, False, "Full-resolution JPEG; deletion status;\nvalidation and operation errors"),
    ]
    for y, incoming, label in flows:
        boundary = 13.1-sqrt(3.1**2-(y-4.6)**2)
        flow(ax, 3.4 if incoming else boundary, boundary if incoming else 3.4, y, label, size=11)
    ax.text(0.6, 1.1, "Image-scoped requests include the image ID and bearer token returned at upload.", fontsize=11, color=INK)
    ax.text(0.6, 0.65, "Internal storage is expanded in Level 1. The current application has no user accounts.", fontsize=10.5, color="#526477")
    save(fig, "lumalab_dfd_level_0")


def level1():
    fig, ax = canvas(19, 19, "LumaLab | DFD Level 1", "Decomposition of process 0 · Yourdon–DeMarco notation")
    rows = [
        ("1.0", "Validate Upload &\nCreate Image Session", "Photograph and filename", "Session details and access token", "D1", "Temporary image /\nsession store", None, "Original, normalized images,\npreview copies and session record"),
        ("2.0", "Retrieve Preset\nCatalogue", "Preset catalogue request", "Preset definitions", "D2", "Preset catalogue\n(PostgreSQL)", "Names, descriptions and\nadjustment values", None),
        ("3.0", "Analyze Photo &\nSuggest Enhancement", "Enhancement request", "Enhancement recipe, adjustments\nand assessment findings", "D1", "Temporary image /\nsession store", "Source images and\nsession metadata", None),
        ("4.0", "Render Editing\nPreviews", "Edit settings and preview request", "Original and edited JPEG previews", "D1", "Temporary image /\nsession store", "Preview source image and\nsession metadata", None),
        ("5.0", "Render & Export\nFinished Image", "Export settings and request", "Full-resolution JPEG", "D1", "Temporary image /\nsession store", "Normalized source image and\nsession metadata", None),
        ("6.0", "Delete Image\nSession", "Deletion request", "Deletion status", "D1", "Temporary image /\nsession store", "Session metadata", "Image files and session\nrecord removal"),
    ]
    for index, (number, title, request, response, sid, sname, read, write) in enumerate(rows):
        y = 16.5-index*2.5
        entity(ax, 0.5, y-0.63, 2.0, 1.26, "E1\nUser", repeated=index > 0)
        titles = ["Validate Upload\n& Create\nImage Session", "Retrieve Preset\nCatalogue", "Analyze Photo\n& Suggest\nEnhancement", "Render Editing\nPreviews", "Render & Export\nFinished Image", "Delete Image\nSession"]
        process(ax, 8.85, y, 1.15, number, titles[index])
        store(ax, 15.1, y-0.63, 3.4, 1.26, sid, sname)
        left = 8.85-sqrt(1.15**2-0.31**2)
        right = 8.85+sqrt(1.15**2-0.31**2)
        flow(ax, 2.5, left, y+0.31, request, size=10)
        flow(ax, left, 2.5, y-0.31, response, below=True, size=10)
        if read and write:
            flow(ax, 15.1, right, y+0.31, read, size=10)
            flow(ax, right, 15.1, y-0.31, write, below=True, size=10)
        elif read:
            flow(ax, 15.1, 10.0, y, read, size=10)
        else:
            flow(ax, 10.0, 15.1, y, write, size=10)
    notes = [
        "Symbols: rectangle = external entity; circle = process; parallel lines = data store; labeled arrow = data flow.",
        "E1 and D1 are repeated for clarity (the same user and store). A diagonal corner marks repeated external entities.",
        "D1 combines private temporary image files on disk with process-local session metadata (token hash, dimensions and expiry).",
        "Edit / export settings include adjustments, RGB curves, crop and the optional enhancement recipe and strength.",
        "Requests to 3.0–6.0 carry an image ID and bearer token. Each process may return validation or operation errors to E1.",
        "Preset selection and reset update browser-held settings; settings accompany render requests. Edits are not stored in PostgreSQL.",
        "Session expiry and application cleanup also remove D1 data; these internal lifecycle activities are omitted from the user flows.",
    ]
    for index, note in enumerate(notes):
        ax.text(0.5, 2.1-index*0.25, note, fontsize=9.4, color="#526477")
    save(fig, "lumalab_dfd_level_1")


if __name__ == "__main__":
    level0()
    level1()
    print(f"Generated Level 0 and Level 1 PNG and SVG diagrams in {OUT}")
