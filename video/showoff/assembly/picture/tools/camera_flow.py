"""Measure what the camera move *looks like*, not whether its curves are continuous.

    blender --background --factory-startup --python tools/camera_flow.py -- [--csv f.csv]

A natural cubic spline through a beat table is C2 everywhere, so "the curves are smooth" is
not a claim about the shot: the v2 draft was C2 and still read as several shots joined by
splines. What a viewer actually integrates is the motion of board features *across the
frame*, so that is what this measures -- board-local sample points projected through the
real `Camera` and differenced frame to frame.

Three numbers per frame, all in frame-widths per second so they are comparable across a
zoom:

    flow   mean |dp| over the sample points: total screen motion, including the radial
           component a push-in produces. Dead air is flow ~ 0; a whip is a spike.
    pan    |mean dp|: the net translation, i.e. how much the whole frame is sliding. A pure
           zoom has flow > 0 and pan ~ 0, which is why both are needed.
    dir    direction of that net translation, in degrees. This is the channel the draft
           failed: an orbit reversal is a 180 deg turn in `dir` at non-trivial `pan`, and it
           reads as the camera stopping and going back the way it came.

and two derived checks:

    lurch  |d flow / dt|, normalised by the median flow. Momentum changes the eye can see.
    turn   |d dir / dt| weighted by pan -- a direction change only counts if the frame was
           actually moving when it happened.

The report ends with the handoff table, because the specific fault being hunted is a target
change that coincides with a zoom or an orbit-rate change: subject, framing and speed all
moving at once is what makes a continuous spline read as a cut.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import animate_assembly_v2 as v2  # noqa: E402

ASPECT = 16 / 9
# Board-local sample points: a grid on the mask plus a raised copy, so the metric sees the
# parallax between the surface and the parts standing on it rather than a flat plate.
GRID = 5
PART_H_MM = 14.0


def sample_points(size_mm):
    w, h = size_mm[0] / 1000.0, size_mm[1] / 1000.0
    pts = []
    for i in range(GRID):
        for j in range(GRID):
            x = (i / (GRID - 1) - 0.5) * w * 0.86
            y = (j / (GRID - 1) - 0.5) * h * 0.86
            pts.append(Vector((x, y, 0.004)))
            pts.append(Vector((x, y, 0.004 + PART_H_MM / 1000.0)))
    return pts


def screen(cam, rig, frame, pts):
    """Sample points -> frame-width units, isotropic (tan_h for both axes)."""
    st = cam.state(frame)
    to_cam = Matrix.LocRotScale(st["loc"], st["quat"], None).inverted()
    k = 2.0 * st["tan_h"]
    out = []
    for p in pts:
        c = to_cam @ rig.to_world(frame, p)
        depth = max(1e-6, -c.z)
        out.append((c.x / (depth * k), c.y / (depth * k)))
    return out


def series(cam, rig, end, pts):
    prev, flow, pan, dirs = None, [0.0], [0.0], [None]
    for f in range(1, end + 1):
        cur = screen(cam, rig, f, pts)
        if prev is not None:
            dx = [b[0] - a[0] for a, b in zip(prev, cur)]
            dy = [b[1] - a[1] for a, b in zip(prev, cur)]
            n = len(dx)
            flow.append(sum(math.hypot(x, y) for x, y in zip(dx, dy)) / n * v2.FPS)
            mx, my = sum(dx) / n, sum(dy) / n
            pan.append(math.hypot(mx, my) * v2.FPS)
            dirs.append(math.degrees(math.atan2(my, mx)))
        prev = cur
    flow[0], pan[0], dirs[0] = flow[1], pan[1], dirs[1]
    return flow, pan, dirs


def unwrap(dirs):
    out = [dirs[0]]
    for d in dirs[1:]:
        prev = out[-1]
        k = round((prev - d) / 360.0)
        out.append(d + 360.0 * k)
    return out


def spark(vals, lo=None, hi=None, width=118):
    """One character per bucket, so the *shape* of a 2600-frame series is visible at once."""
    ramp = " .:-=+*#%@"
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    span = max(1e-12, hi - lo)
    step = len(vals) / width
    out = []
    for i in range(width):
        a, b = int(i * step), max(int(i * step) + 1, int((i + 1) * step))
        v = sum(vals[a:b]) / (b - a)
        out.append(ramp[min(len(ramp) - 1, max(0, int((v - lo) / span * (len(ramp) - 1))))])
    return "".join(out)


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--parts", type=Path, default=Path("out/scene/components_v2.json"))
    ap.add_argument("--size", default="163.1x100.1", help="layer bounds, mm")
    args = ap.parse_args(argv)
    size_mm = tuple(float(v) for v in args.size.split("x"))

    end = int(v2.CAM_BEATS[-1][0])
    rig = v2.Rig(Vector((0.0, 0.0, 0.0)))
    # The `swarm` target rides the centroid of what is airborne and the hero targets are board
    # positions, so both come from the board's own dump when it is there -- a flow metric run
    # against a stand-in swarm would be measuring a different camera from the one that renders.
    subjects_local, plan, pos_local = dict(SUBJECTS_LOCAL), {}, {}
    if args.parts.exists():
        subjects_local, plan, pos_local = from_board(args.parts, size_mm)
        print(f"  targets from {args.parts} ({len(plan)} scheduled parts)")
    else:
        print(f"  {args.parts} missing -- subject targets from the table in this file, "
              f"swarm target pinned to the board centre")
    cam = v2.Camera(rig, v2.build_targets(subjects_local, plan, pos_local, size_mm, end))

    pts = sample_points(size_mm)
    flow, pan, dirs = series(cam, rig, end, pts)
    udir = unwrap(dirs)
    med = sorted(flow)[len(flow) // 2]
    lurch = [0.0] + [abs(flow[i] - flow[i - 1]) * v2.FPS / max(1e-9, med)
                     for i in range(1, len(flow))]
    # Gated on the frame actually translating, for the reason spelled out at the reversal
    # check below: the direction of a near-zero mean displacement is noise, and an ungated
    # `turn` reports a pure orbit as thousands of degrees per second of direction change.
    turn = [0.0] + [abs(udir[i] - udir[i - 1]) * v2.FPS * min(1.0, pan[i] / max(1e-9, med))
                    * (1.0 if pan[i] > 0.55 * flow[i] else 0.0)
                    for i in range(1, len(udir))]

    print(f"\n  {end} frames, {end / v2.FPS:.2f} s at {v2.FPS} fps"
          f"   sample points {len(pts)}")
    print(f"  flow  median {med:.4f}  min {min(flow):.4f}  max {max(flow):.4f}   "
          f"frame-widths/s")
    print(f"  pan   median {sorted(pan)[len(pan) // 2]:.4f}  max {max(pan):.4f}")
    print(f"  lurch max {max(lurch):.2f} at frame {lurch.index(max(lurch)) + 1}"
          f"   turn max {max(turn):.0f} deg/s at frame {turn.index(max(turn)) + 1}")

    print("\n  flow (screen motion energy), frame 1 -> end")
    print("    " + spark(flow, 0.0, max(flow)))
    print("  pan (net frame translation)")
    print("    " + spark(pan, 0.0, max(flow)))
    print("  |d dir/dt| weighted by pan  (spikes = the frame changed direction while moving)")
    print("    " + spark(turn, 0.0, max(60.0, max(turn))))

    # Dead air and whips, as spans rather than single frames: one quiet frame is nothing, a
    # quiet second is a stopped camera.
    def spans(pred, minlen):
        runs, run = [], None
        for i, ok in enumerate(pred):
            if ok and run is None:
                run = i
            elif not ok and run is not None:
                if i - run >= minlen:
                    runs.append((run + 1, i))
                run = None
        if run is not None and len(pred) - run >= minlen:
            runs.append((run + 1, len(pred)))
        return runs

    dead = spans([f < 0.30 * med for f in flow], 15)
    print(f"\n  dead air (flow < 30 % of median for >= 0.5 s): "
          f"{', '.join(f'{a}-{b}' for a, b in dead) or 'none'}")
    hot = spans([f > 2.6 * med for f in flow], 6)
    print(f"  whips (flow > 2.6x median for >= 0.2 s): "
          f"{', '.join(f'{a}-{b}' for a, b in hot) or 'none'}")

    # Reversals: the net translation turning through more than 120 deg while it is actually
    # translating. Measured over a 20-frame window, because a reversal spread thinly over
    # half a second still reads as one.
    #
    # The `pan > 0.55 * flow` guard is not a fudge, it is the difference between the two
    # things this file measures. Under a pure orbit about a centred target the near half of
    # the board tracks one way across the frame and the far half tracks the other, so the
    # *mean* displacement is near zero however fast the shot is moving -- and the direction
    # of a near-zero vector is noise, which the first version of this check duly reported as
    # eight reversals in a camera whose orbit is monotone by construction. A frame is only
    # translating, and can only reverse, when its net displacement is a real fraction of its
    # total motion.
    rev, w = [], 20
    i = w
    while i < len(udir) - w:
        seg = range(i - w, i + w)
        if all(pan[j] > 0.55 * flow[j] and pan[j] > 0.4 * med for j in seg):
            turned = abs(udir[i + w] - udir[i - w])
            if turned > 120.0:
                rev.append((i + 1, turned))
                i += w
        i += 1
    print(f"  direction reversals (>120 deg over 0.67 s at non-trivial pan): "
          f"{', '.join(f'{f}({t:.0f} deg)' for f, t in rev) or 'none'}")

    # Channel chatter. A sign change in a rate is a direction change in that channel, and the
    # eye reads several of them in a row as the operator nudging the head.
    print("\n  channel direction changes (sign flips in the per-frame rate)")
    for name in v2.CAM_CHANNELS:
        s = cam.ch[name]
        rate = [s(f) - s(f - 1) for f in range(2, end + 1)]
        flips, last = 0, 0
        for r in rate:
            if abs(r) < 1e-7:
                continue
            sgn = 1 if r > 0 else -1
            if last and sgn != last:
                flips += 1
            last = sgn
        print(f"    {name:7s} {flips:3d}   range {min(s(f) for f in range(1, end + 1)):8.2f}"
              f" .. {max(s(f) for f in range(1, end + 1)):8.2f}")
    for name, s in (("yaw", rig.yaw), ("roll", rig.roll)):
        rate = [s(f) - s(f - 1) for f in range(2, end + 1)]
        flips, last = 0, 0
        for r in rate:
            if abs(r) < 1e-7:
                continue
            sgn = 1 if r > 0 else -1
            if last and sgn != last:
                flips += 1
            last = sgn
        print(f"    board {name:4s} {flips:2d}   range {min(s(f) for f in range(1, end + 1)):8.2f}"
              f" .. {max(s(f) for f in range(1, end + 1)):8.2f}")

    # The handoffs, which is where the draft came apart: what else was moving while the
    # subject changed. width_rate is in % of width per second, so it is comparable to a
    # degrees-per-second orbit rate without a unit conversion in the head.
    # The handoffs. What is being hunted is the specific fault that made v2 read as cut
    # together: the subject changing at the same moment as the framing and the speed.
    #
    # Measured at the *midpoint*, where the crossfade weight is moving fastest, not as a max
    # over the window -- a 7 s handoff will always contain the piece's busiest frame
    # somewhere, and reporting that says nothing about the handoff.
    print("\n  subject handoffs -- what else moves while the subject changes")
    print("    frames        secs   from -> to      flow/med  d width %/s  lurch  turn deg/s")
    track = getattr(v2, "TARGET_BEATS", None) or [(b[0], b[-1]) for b in v2.CAM_BEATS]
    for (fa, na), (fb, nb) in zip(track, track[1:]):
        if na == nb:
            continue
        a, b = int(fa), min(int(fb), end)
        mid = (a + b) // 2
        wd = abs(cam.ch["width"](mid) - cam.ch["width"](mid - 1)) / cam.ch["width"](mid) \
            * 100.0 * v2.FPS
        lu = max(lurch[a - 1:b]) if b > a else 0.0
        print(f"    {a:5d}-{b:<5d} {(b - a) / v2.FPS:5.1f}  {na:>7s} -> {nb:<8s} "
              f"{flow[mid - 1] / med:7.2f}  {wd:10.1f}  {lu:6.1f}  {turn[mid - 1]:9.0f}")
    print("    (flow near 1.0 and small numbers beside it = the subject changed while the "
          "camera\n     kept doing what it was already doing)")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        rows = ["frame,flow,pan,dir,lurch,turn,az,el,width,lens,fstop,roll"]
        for i, f in enumerate(range(1, end + 1)):
            rows.append(",".join(str(round(v, 5)) for v in (
                f, flow[i], pan[i], udir[i], lurch[i], turn[i],
                cam.ch[v2.CAM_CHANNELS[0]](f), cam.ch["el"](f), cam.ch["width"](f),
                cam.ch["lens"](f), cam.ch["fstop"](f), cam.ch["roll"](f))))
        args.csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(f"\n  wrote {args.csv}")
    return 0


def from_board(parts_json: Path, size_mm):
    """The real hero positions and wave plan, the same way `--plan-only` gets them."""
    import json

    data = json.loads(parts_json.read_text(encoding="utf-8-sig"))
    parts = [p for p in data["parts"] if p["models"] and not p["dnp"]]
    heroes = v2.resolve_heroes(parts)
    pos_mm, order_key = v2.order_key_factory(parts)
    refs = [p["ref"] for p in parts]
    groups = v2.group_parts(refs, parts, heroes, order_key)
    plan, _sub = v2.wave_schedule(groups, parts, order_key)
    bb = data["edge_bbox_mm"]
    cx, cy = bb["left"] + bb["width"] / 2.0, -(bb["top"] + bb["height"] / 2.0)
    pos_local = {r: Vector(((pos_mm[r][0] - cx) / 1000.0, (pos_mm[r][1] - cy) / 1000.0,
                            0.004)) for r in refs}
    named = {n: pos_local[r] for n, r in heroes.items()}
    named.update(v2.group_targets(groups, pos_local))   # the connector -- see SUBJECT_GROUPS
    return named, plan, pos_local


# Board-local subject positions, in metres, from `dump_components.py` on PCB_new.kicad_pcb --
# see the values printed by `animate_v2.ps1 -PlanOnly`, which reads the board itself. Kept
# here only so this tool runs without an export; it is a convenience, not a second home.
SUBJECTS_LOCAL = {
    "adc": Vector((-0.0396, -0.0210, 0.005)),
    "driver": Vector((-0.0364, 0.0172, 0.006)),
    "mcu": Vector((0.0270, -0.0044, 0.011)),
    "harting": Vector((0.0586, -0.0200, 0.016)),   # already biased -- SUBJECT_AIM
}


if __name__ == "__main__":
    sys.exit(main())
