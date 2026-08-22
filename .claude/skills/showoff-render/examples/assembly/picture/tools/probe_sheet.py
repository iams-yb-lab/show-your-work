"""Tile probe frames into one labelled contact sheet, in storyboard order.

    python tools/probe_sheet.py out/anim/probe_v2 --out out/compare/drafts/anim_v2.png \
        --cols 4 --labels labels.txt

`crop_tile.py` is the tool for comparing the *same* crop across several renders; this is the
other job -- twenty-odd different frames of one sequence, each needing to say which frame it
is and which beat it was chosen for, because a contact sheet whose tiles are unlabelled
cannot be reasoned about.

Runs on the system Python with PIL, not inside Blender: the frames are already
display-referred PNGs, so there is nothing here that needs Blender's colour management, and
ImageDraw's text is the whole point.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG = (26, 27, 31)
FG = (232, 233, 238)
DIM = (150, 152, 162)


def font(size: int):
    for name in ("consola.ttf", "DejaVuSansMono.ttf", "cour.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", type=Path, help="directory of frame_NNNN.png")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--labels", type=Path,
                    help="one 'frame  text' line per beat; frames not listed get no caption")
    ap.add_argument("--title", default="")
    ap.add_argument("--pattern", default="frame_*.png",
                    help="glob for the tiles; the LAST run of digits in each name is the "
                         "frame number it is captioned and sorted by -- last, not first, or "
                         "a prefix like v1_0001 captions as frame 1")
    args = ap.parse_args()

    captions = {}
    if args.labels and args.labels.exists():
        for line in args.labels.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                num, _, text = line.strip().partition(" ")
                captions[int(num)] = text.strip()

    paths = sorted((p for p in args.frames.glob(args.pattern)
                    if re.search(r"\d+", p.stem)),
                   key=lambda p: int(re.findall(r"\d+", p.stem)[-1]))
    if not paths:
        return print(f"no {args.pattern} in {args.frames}") or 1

    tiles = []
    for path in paths:
        img = Image.open(path).convert("RGB")
        if args.scale != 1.0:
            img = img.resize((round(img.width * args.scale), round(img.height * args.scale)),
                             Image.LANCZOS)
        tiles.append((int(re.findall(r"\d+", path.stem)[-1]), img))

    tw, th = tiles[0][1].size
    bar, gap, pad = 26, 8, 14
    head = 34 if args.title else 0
    cols = min(args.cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (pad * 2 + cols * tw + (cols - 1) * gap,
                              pad * 2 + head + rows * (th + bar) + (rows - 1) * gap), BG)
    draw = ImageDraw.Draw(sheet)
    small, big = font(14), font(19)
    if args.title:
        draw.text((pad, pad), args.title, font=big, fill=FG)

    for i, (num, img) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c * (tw + gap)
        y = pad + head + r * (th + bar + gap)
        sheet.paste(img, (x, y))
        label = f"{num:>4}  {num / args.fps:5.2f}s"
        draw.text((x + 2, y + th + 5), label, font=small, fill=FG)
        if num in captions:
            draw.text((x + 2 + 96, y + th + 5), captions[num], font=small, fill=DIM)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(f"wrote {args.out}  {sheet.width}x{sheet.height}  ({len(tiles)} tiles, "
          f"{cols} cols)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
