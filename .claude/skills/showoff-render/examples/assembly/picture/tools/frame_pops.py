"""Find one-frame discontinuities in a rendered sequence -- pops, snaps and steps.

    python tools/frame_pops.py --frames out/anim/purple_v2 [--top 20] [--ratio 2.0]

System Python plus PIL and numpy. Deliberately not Blender: this reads the frames that were
actually produced, which is the whole point.

`camera_flow.py` measures the camera and `--plan-only` measures the schedule, and both of them
will pass while a board-sized purple sheet appears out of nothing in a single frame. That
happened, at f525 and f531, and it was found by a person watching the draft rather than by
anything here. `key_visibility` is a hard step -- it has to be, since a fully transparent
surface still costs rays -- so keying a mask film visible *and* opaque on the same frame popped
it into the middle of the shot. No amount of reasoning about beat tables can see that.
Differencing the rendered frames can.

Two signals per transition, ranked on whichever is worse:

    dRGB   mean per-pixel worst-channel difference, against the *local* median rather than a
           global one. A fast pan legitimately differs a lot everywhere; a pop differs far
           more than its own neighbours do.
    new    fraction of pixels that were backdrop-dark and are now clearly lit -- "something
           arrived where there was nothing". A pan moves already-lit pixels around instead of
           creating them. This matters because the first thing this tool was pointed at was a
           dark purple sheet on a black backdrop: a large change in blue and a small one in
           brightness. A luma metric ranked it 6th; this ranks it 1st, at 21x.
    iso    the same signal against the two *adjacent* transitions instead of a 31-frame
           median, and the column that actually decides. A pop happens in one frame, so its
           neighbours are quiet. A connector entering from off-frame lights up just as much
           backdrop but does it every frame for a second, so `iso` sits near 1. `score` is the
           smaller of the two ratios, so both have to be high to be reported.

Sustained motion appears in the ranking too, and `iso` is what separates it from a pop: a
connector entering, the Teensy crossing frame over 16 frames, a solder fillet appearing under a
part that has just landed. Before that column existed a full-piece run reported 49 transitions
of which 2 were pops, and sorting them meant opening frames by hand.

**A low `iso` means "not a one-frame pop", NOT "fine".** Do not read this tool as clearing
anything. `key_visibility` is a hard step for every one of the ~110 parts, so a part does appear
from nothing, and whether that reads depends on how big it is and on where it appears. On draft 2
the terminal blocks and the trimmers were called out by eye as visibly popping in at the edge,
after this tool had ranked the same events as sustained motion and after they had been written up
here as correct. Seventeen parts were on screen the frame they appeared, up to 0.56 of a half-frame
in. The fault was real and this file did not and cannot find it: a swarm is busy everywhere, so one
more part arriving is not *isolated*. What finds it is geometry rather than pixels -- the
entrances-and-landings table `animate_assembly_v2.py` prints, from each part's projected bounding
box on the frame it becomes visible. Two tools, two questions; neither one is the verdict.

What it cannot see is anything smoothly wrong. A mushy transition or a bad composition differs
from its neighbours by very little, by construction.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Downscaled before differencing: a pop is a large-area event and the noise floor of a 32-sample
# draft is not, so throwing away resolution improves the signal as well as the speed.
WORK = (320, 180)


def load(path: Path) -> np.ndarray:
    """RGB, downscaled, float. RGB and not luma on purpose: the first thing this tool was
    pointed at was a dark purple sheet appearing over a black backdrop, which is a large
    change in blue and a small one in luma. Measuring brightness would have under-reported
    the very event it was written to find."""
    im = Image.open(path).convert("RGB").resize(WORK, Image.BOX)
    return np.asarray(im, dtype=np.float32)


def bbox(mask: np.ndarray):
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if not rows.size:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=Path, required=True)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--ratio", type=float, default=2.0,
                    help="report a frame when its difference exceeds this multiple of the "
                         "local median difference")
    ap.add_argument("--window", type=int, default=15, help="half-width of the local baseline")
    ap.add_argument("--floor", type=float, default=0.8,
                    help="ignore transitions quieter than this absolute mean difference (0-255), so "
                         "a still stretch does not report its own sampling noise as pops")
    args = ap.parse_args()

    files = sorted(args.frames.glob("frame_*.png"),
                   key=lambda p: int(re.search(r"(\d+)", p.name).group(1)))
    if len(files) < 3:
        sys.exit(f"need at least 3 frames in {args.frames}, found {len(files)}")
    nums = [int(re.search(r"(\d+)", p.name).group(1)) for p in files]
    if nums != list(range(nums[0], nums[0] + len(nums))):
        print(f"  note: sequence has gaps ({nums[0]}..{nums[-1]}, {len(nums)} files); "
              f"differences across a gap are meaningless and are skipped")

    # pairs[j] describes the transition nums[j] -> nums[j+1]. Keeping that indexing explicit
    # because the first version of this file printed nums[j]-1 -> nums[j] and so named every
    # pop one frame early -- a diagnostic that misreports where the fault is costs more time
    # than no diagnostic at all.
    diffs, boxes, appeared = [], [], []
    prev = load(files[0])
    for i in range(1, len(files)):
        cur = load(files[i])
        if nums[i] != nums[i - 1] + 1:
            diffs.append(None); boxes.append(None); appeared.append(None)
        else:
            d = np.abs(cur - prev).max(axis=2)          # worst channel, per pixel
            diffs.append(float(d.mean()))
            hot = d > 24.0
            boxes.append(bbox(hot))
            # "Something arrived where there was nothing": pixels that were backdrop-dark and
            # are now clearly lit. This is what separates a pop from a fast pan, which moves
            # already-lit pixels around instead of creating them.
            was_dark = prev.max(axis=2) < 22.0
            now_lit = cur.max(axis=2) > 42.0
            appeared.append(float((was_dark & now_lit).mean()))
        prev = cur

    real = [d for d in diffs if d is not None]
    med = sorted(real)[len(real) // 2]
    print(f"\n  {len(files)} frames ({nums[0]}..{nums[-1]})   median frame-to-frame "
          f"difference {med:.3f} of 255")

    scored = []
    for i, d in enumerate(diffs):
        if d is None or d < args.floor:
            continue
        lo, hi = max(0, i - args.window), min(len(diffs), i + args.window + 1)
        near = sorted(x for j, x in enumerate(diffs[lo:hi], lo) if x is not None and j != i)
        nb = sorted(x for j, x in enumerate(appeared[lo:hi], lo)
                    if x is not None and j != i)
        if not near:
            continue
        base = near[len(near) // 2]
        if base <= 1e-6:
            continue
        app_base = nb[len(nb) // 2] if nb else 0.0
        app_ratio = appeared[i] / max(app_base, 0.0008)
        # Isolation: the same signal against its *immediate* neighbours rather than a 31-frame
        # median. This is the column that decides, and without it the tool is not conclusive --
        # the first full-piece run flagged 49 transitions of which 2 were faults, and telling
        # them apart meant opening frames by hand. A pop happens in one frame, so its
        # neighbours are quiet and `iso` is large. A connector entering from off-frame, or the
        # Teensy crossing frame over 16 frames, lights up just as much backdrop but does it
        # every frame, so `iso` sits near 1. Flagged only when both are high.
        near_new = [appeared[j] for j in (i - 1, i + 1)
                    if 0 <= j < len(appeared) and appeared[j] is not None]
        iso = appeared[i] / max(max(near_new) if near_new else 0.0, 0.0008)
        scored.append((min(max(d / base, app_ratio), iso), d / base, app_ratio, iso,
                       d, base, nums[i], nums[i + 1], boxes[i]))

    scored.sort(reverse=True)
    flagged = [s for s in scored if s[0] >= args.ratio]
    print(f"  {len(flagged)} frame(s) above {args.ratio}x their local baseline\n")
    print(f"    {'transition':>14s} {'score':>6s} {'dRGB':>6s} {'new':>6s} {'iso':>6s} "
          f"{'diff':>7s}   changed region in a {WORK[0]}x{WORK[1]} grid")
    for score, dr, ar, iso, d, base, a, b, box in scored[:args.top]:
        mark = " <== POP " if score >= args.ratio else "         "
        print(f"    {a:6d}->{b:<6d} {score:6.1f} {dr:6.1f} {ar:6.1f} {iso:6.1f} "
              f"{d:7.3f}{mark}{box if box else '-'}")
    if not flagged:
        print("\n  nothing above the threshold: no frame differs from its neighbours by more "
              f"than {args.ratio}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
