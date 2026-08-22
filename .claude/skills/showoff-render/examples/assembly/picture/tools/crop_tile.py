"""Crop the same region out of several renders and tile them into one comparison image.

    blender --background --factory-startup --python tools/crop_tile.py -- \
        --region 0.40 0.34 0.62 0.64 --cols 2 --zoom 2 \
        --out out/ab/sheet.png out/ab/shell_A.png out/ab/shell_B.png ...

Exists because judging a 20 mm connector inside a 170 mm board means looking at maybe 3 % of
the frame, and flipping between four full renders to compare one detail is both slow and
unreliable -- side by side at the same crop is the only way to see a small difference.

Region is x0 y0 x1 y1 as fractions of the frame with the origin top-left, matching how you'd
describe a spot in an image viewer. Blender's pixel buffer is bottom-up, so this flips.
Uses Blender's own image IO and bundled numpy; PIL is not guaranteed to be present.
"""

import argparse
import sys
from pathlib import Path

import bpy
import numpy as np


def load_rgb(path: Path) -> np.ndarray:
    """Load a PNG as a top-down (rows, cols, 3) float array."""
    img = bpy.data.images.load(str(path.resolve()))
    try:
        w, h = img.size
        px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)
        rgb = px[:, :, :3]
        if img.channels == 4:
            # Composite over mid grey so transparent renders (the `slide` shot) still show.
            a = px[:, :, 3:4]
            rgb = rgb * a + 0.18 * (1.0 - a)
        return rgb[::-1]  # bottom-up -> top-down
    finally:
        bpy.data.images.remove(img)


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", type=float, nargs=4, default=[0.0, 0.0, 1.0, 1.0],
                    metavar=("X0", "Y0", "X1", "Y1"), help="fractions, origin top-left")
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--zoom", type=int, default=1, help="integer upscale of each crop")
    ap.add_argument("--shrink", type=int, default=1,
                    help="integer downscale of each crop, block-averaged. Needed to compare "
                         "whole 4K frames: three of them tiled untouched is 11520 px wide")
    ap.add_argument("--gap", type=int, default=6)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("images", type=Path, nargs="+")
    args = ap.parse_args(argv)

    x0, y0, x1, y1 = args.region
    crops = []
    for path in args.images:
        rgb = load_rgb(path)
        h, w = rgb.shape[:2]
        c = rgb[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
        if c.size == 0:
            return print(f"empty crop from {path}") or 1
        if args.shrink > 1:
            # Block-average rather than decimate, so fine copper detail turns into tone
            # instead of aliasing into moire.
            s = args.shrink
            hh, ww = (c.shape[0] // s) * s, (c.shape[1] // s) * s
            c = c[:hh, :ww].reshape(hh // s, s, ww // s, s, 3).mean(axis=(1, 3))
        if args.zoom > 1:
            c = c.repeat(args.zoom, axis=0).repeat(args.zoom, axis=1)
        crops.append(c)
        print(f"  {path.name}: {w}x{h} -> crop {c.shape[1]}x{c.shape[0]}")

    ch, cw = crops[0].shape[:2]
    cols = min(args.cols, len(crops))
    rows = (len(crops) + cols - 1) // cols
    g = args.gap
    sheet = np.full((rows * ch + (rows - 1) * g, cols * cw + (cols - 1) * g, 3),
                    0.5, dtype=np.float32)
    for i, c in enumerate(crops):
        r, col = divmod(i, cols)
        sheet[r * (ch + g):r * (ch + g) + ch, col * (cw + g):col * (cw + g) + cw] = c

    sh, sw = sheet.shape[:2]
    out_img = bpy.data.images.new("sheet", width=sw, height=sh, alpha=False)
    flat = np.concatenate(
        [sheet[::-1], np.ones((sh, sw, 1), dtype=np.float32)], axis=2).ravel()
    out_img.pixels.foreach_set(flat)
    # The crops are already display-referred, so write them straight through rather than
    # letting Blender apply a second view transform on save.
    out_img.file_format = "PNG"
    out_img.filepath_raw = str(args.out.resolve())
    scene = bpy.context.scene
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    out_img.save()
    print(f"wrote {args.out}  {sw}x{sh}  ({len(crops)} tiles, {cols} cols)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
