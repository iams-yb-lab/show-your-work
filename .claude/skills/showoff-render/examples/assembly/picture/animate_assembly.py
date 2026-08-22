"""Assembly animation: bare board -> populated controller, keyframed and deterministic.

Builds on `blender_scene.py` rather than duplicating it -- the import, the material
corrections, the four-light studio and the exposure calibration all live there, and this
script imports them. What it adds is time.

    blender --background --factory-startup --python animate_assembly.py -- \
        --pcb3d out/scene/pcb_purple.pcb3d --parts out/scene/components.json \
        --blend out/scene/anim_purple.blend --outdir out/anim/purple

Three ideas carry the whole thing:

  Components are moved by their *delta* transform, never their real one. delta_location
  and delta_rotation_euler compose on top of the imported transform, so "landed" is
  delta = 0 and the last frame reconstructs the real board exactly, to the bit. Nothing
  here can drift a part off its pads.

  Parts are identified from the board, not from the render. `components.json`
  (see dump_components.py) carries designators, footprints and part numbers; objects carry
  only 3D-model filenames. match_objects() joins the two by position and reports the
  residual, so a mis-identified ADC is a loud failure rather than a wrong hero shot.

  Groups land one at a time. The schedule is *accumulated* from PLACEMENT rather than
  written out as frame numbers, so a group physically cannot start before the one in front
  of it has finished. Retiming a group pushes everything after it along, camera included.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
import blender_scene as studio  # noqa: E402

FPS = 30
LOOK = "product"
BACKDROP = "mood"   # graded floor pool + cool world gradient; see blender_scene.BACKDROPS
SEED = 20260810

BARE_HOLD = 60    # frames of bare board before the first part moves
FINAL_HOLD = 64   # frames held on the finished board, for cutting into the next scene

# The three parts that get their own introduction, keyed on the part number in the board's
# Value field rather than on a designator -- designators get renumbered, and this repo has
# already moved one four times. Resolved to designators at runtime and printed.
HEROES = (
    ("adc", "AD7124"),      # AD7124-8BCPZ, the ADC
    ("driver", "MAX1968"),  # MAX1968EUI+T, the TEC driver
    ("mcu", "Teensy"),      # Teensy 4.1, the controller module
)

# Placement order, and the only place it is written down. Every group finishes before the
# next one starts: `schedule()` accumulates these, so no arithmetic mistake can make two
# groups overlap. Chip resistors first, then ceramics, then progressively larger parts.
#
#   stagger  frames between the first and the last part of the group setting off
#   travel   frames one part takes to come down -- long, because the motion should read as
#            placement rather than as dropping
#   gap      clear air after the group has landed, before the next one moves
#   rise     how far above its pads a part starts, in mm (range, jittered per part)
#   spin     degrees of yaw it turns through on the way down
#   tilt     degrees of lean it comes in with, straightening as it lands
PLACEMENT = (
    ("resistors", dict(stagger=66, travel=30, gap=6, rise=(9, 15), spin=6, tilt=(0.0, 0.0))),
    ("ceramics", dict(stagger=84, travel=30, gap=6, rise=(9, 17), spin=6, tilt=(0.0, 0.0))),
    ("semis", dict(stagger=22, travel=30, gap=6, rise=(17, 25), spin=8, tilt=(2.0, -1.5))),
    ("headers", dict(stagger=20, travel=36, gap=6, rise=(26, 33), spin=7, tilt=(-3.0, 2.0))),
    ("terminals", dict(stagger=20, travel=40, gap=6, rise=(32, 39), spin=5, tilt=(2.5, -2.0))),
    ("power", dict(stagger=26, travel=42, gap=6, rise=(30, 42), spin=8, tilt=(-2.0, -3.0))),
    ("harting", dict(stagger=8, travel=48, gap=12, rise=(54, 58), spin=3, tilt=(1.5, -1.0))),
)

# Which parts belong to which group, tested against the board's own footprint field so the
# grouping is a fact about the part rather than a list to maintain. First match wins; the
# heroes are removed before any of this runs.
GROUP_TESTS = (
    ("resistors", ("Resistor_SMD:R_",)),
    ("ceramics", ("Capacitor_SMD:C_",)),
    ("semis", ("D_SOD", "LED-SMD", "SOT-23", "SOIC-8")),
    ("headers", ("PinHeader",)),
    ("terminals", ("TerminalBlock",)),
    # Inductors, the bulk electrolytic, the slide switch and the three trimmers.
    ("power", ("IND-SMD", "CAP-SMD_BD", "SW-SMD", "RES-ADJ")),
    ("harting", ("HARTING",)),
)

# The hero entrances, in order. Slower and taller than anything before them, and each one
# different in character while staying in the same language.
HERO_MOVES = (
    ("adc", dict(lead=16, travel=68, gap=16, rise=52, spin=22, tilt=(2.5, -1.5))),
    ("driver", dict(lead=16, travel=70, gap=16, rise=58, spin=-14, tilt=(-1.5, 2.0))),
    ("mcu", dict(lead=18, travel=80, gap=0, rise=82, spin=8, tilt=(1.2, -0.8))),
)


def schedule(groups: dict) -> tuple[dict, int]:
    """Turn PLACEMENT into (first move, last move, last landing) per group, in frames.

    Sequential by construction, which is the point: the next group's first part does not
    move until the previous group's last part has landed.
    """
    out, f = {}, BARE_HOLD
    for label, spec in PLACEMENT:
        if not groups.get(label):
            continue
        first, last = f, f + spec["stagger"]
        out[label] = (first, last, last + spec["travel"])
        f = out[label][2] + spec["gap"]
    return out, f


def hero_schedule(start: int) -> tuple[dict, int]:
    """Same accumulation for the three hero entrances. `lead` is the head start the camera
    gets, so it has arrived before the part comes into frame."""
    out, f = {}, start
    for name, m in HERO_MOVES:
        out[name] = (f + m["lead"], f + m["lead"] + m["travel"])
        f = out[name][1] + m["gap"]
    return out, f


# ------------------------------------------------------------------- board <-> scene join


def model_stem(obj, known) -> str:
    """The 3D-model filename this object was imported from.

    Read off the *mesh*, not the object. Instances of one model share its mesh datablock,
    which keeps the filename intact, while the object names are mangled two ways: Blender
    truncates a name to make room for its `.001` duplicate suffix (so three of the four
    Phoenix blocks are called `..._Horizont`, `..._Horizont.001` and `..._Horizonta`) and
    it *replaces* a trailing numeric-looking suffix, which turns a second
    `IND-SMD_L6.0-W6.0-H4.5` into `IND-SMD_L6.0-W6.0-H4.001`.

    Meshes can still be truncated at 63 characters, so fall back to a unique prefix match.
    """
    name = re.sub(r"\.\d{3}$", "", obj.data.name)
    if name in known:
        return name
    hits = [k for k in known if k.startswith(name)]
    return hits[0] if len(hits) == 1 else name


def match_objects(components, parts, offset_mm):
    """Assign every component object a designator, by position within its own model class.

    Restricting candidates to footprints that reference the same 3D model is what makes
    this exact rather than approximate: 29 C_0402 objects are matched against the 29
    C_0402 footprints and nothing else, so a 0.4 mm neighbour cannot steal a match.
    """
    wanted = {}
    for part in parts:
        for model in part["models"]:
            wanted.setdefault(model["file"], []).append(part)

    matched, worst, unmatched = {}, (0.0, None), []
    counts = {}
    for obj in components:
        stem = model_stem(obj, wanted)
        cands = wanted.get(stem)
        if not cands:
            unmatched.append((obj.name, "no footprint uses this model"))
            continue
        here = Vector(obj.matrix_world.translation[:2]) * 1000.0 - offset_mm
        best = min(cands, key=lambda p: (p["x"] - here.x) ** 2 + (-p["y"] - here.y) ** 2)
        d = math.dist((best["x"], -best["y"]), (here.x, here.y))
        matched[obj.name] = best["ref"]
        counts[best["ref"]] = counts.get(best["ref"], 0) + 1
        # Position only has a job when a model class has more than one candidate -- it is
        # what tells 29 identical 0402s apart. With a single candidate the model name has
        # already decided it, and the distance is expected to be non-zero: a footprint's
        # `(offset)` moves the object's origin off the footprint origin, which is 1.25 mm
        # for J8's Harting and 31.7 mm for a swapped-in model placed by its corner.
        if len(cands) > 1 and d > worst[0]:
            worst = (d, f'{obj.name} -> {best["ref"]}')

    # Every placed footprint must collect exactly as many objects as it has models.
    for part in parts:
        want = len(part["models"])
        got = counts.get(part["ref"], 0)
        if got != want:
            unmatched.append((part["ref"], f"{got} objects, expected {want}"))

    print(f"  matched {len(matched)}/{len(components)} objects to {len(counts)} designators, "
          f"worst ambiguous-class residual {worst[0]:.3f} mm ({worst[1]})")
    if unmatched:
        for name, why in unmatched[:12]:
            print(f"    UNMATCHED {name}: {why}")
        sys.exit(f"component matching failed on {len(unmatched)} item(s)")
    return matched


def recover_offset(components, parts) -> Vector:
    """Find the board-centring offset by vote instead of assuming it.

    The importer centres the board on the origin, so a Blender position is a board
    position minus the board's bounding-box centre. Rather than trust that, every
    (object, footprint) pair casts a vote for the offset it would imply; the true offset
    is the one ~100 parts agree on. It is then averaged over its own voters for precision,
    and cross-checked against the board's measured centre.
    """
    exp = [(p["x"], -p["y"]) for p in parts for _ in p["models"]]
    obs = [(o.matrix_world.translation.x * 1000.0, o.matrix_world.translation.y * 1000.0)
           for o in components]
    votes = {}
    for ox, oy in obs:
        for ex, ey in exp:
            votes.setdefault((round((ox - ex) / 0.5), round((oy - ey) / 0.5)), []).append(
                (ox - ex, oy - ey))
    key = max(votes, key=lambda k: len(votes[k]))
    winners = votes[key]
    offset = Vector((sum(v[0] for v in winners) / len(winners),
                     sum(v[1] for v in winners) / len(winners)))
    print(f"  centring offset {offset.x:+.3f}, {offset.y:+.3f} mm "
          f"({len(winners)}/{len(obs)} parts agree)")
    return offset


def resolve_heroes(parts):
    found = {}
    for name, needle in HEROES:
        hits = [p for p in parts if needle.lower() in p["value"].lower()]
        if len(hits) != 1:
            sys.exit(f"hero '{name}': {len(hits)} parts match {needle!r} "
                     f"({[h['ref'] for h in hits]}) -- expected exactly one")
        found[name] = hits[0]["ref"]
    return found


def group_parts(components, matched, parts, heroes, order_key):
    """Sort the parts into hero, placement group, or unclassified.

    Objects are collected per designator first, so a part built from several meshes moves
    as one thing -- which is the whole reason for going through designators rather than
    objects.
    """
    by_ref = {}
    for obj in components:
        by_ref.setdefault(matched[obj.name], []).append(obj)

    part_of = {p["ref"]: p for p in parts}
    hero_refs = set(heroes.values())
    groups, seen = {}, set(hero_refs)
    for label, needles in GROUP_TESTS:
        picked = [r for r in by_ref
                  if r not in seen
                  and any(n in part_of[r]["footprint"] for n in needles)]
        groups[label] = sorted(picked, key=order_key)
        seen.update(picked)

    # Anything the tests missed still has to be placed, or it would appear from nowhere at
    # frame 1. It goes down with `power`, and is named so the group tests can be extended.
    leftover = sorted(set(by_ref) - seen, key=order_key)
    if leftover:
        print(f"  note: {len(leftover)} part(s) matched no group test, placed with 'power': "
              f"{', '.join(leftover)}")
        groups["power"] = groups.get("power", []) + leftover

    print(f"  {len(by_ref)} parts placed in {len([g for g in groups.values() if g])} groups "
          f"+ {len(hero_refs)} heroes")
    for label, _ in PLACEMENT:
        refs = groups.get(label) or []
        if refs:
            print(f"    {label:10s} {len(refs):3d}  {', '.join(refs[:8])}"
                  f"{' ...' if len(refs) > 8 else ''}")
    for name, ref in heroes.items():
        print(f"    hero {name:5s} = {ref} ({part_of[ref]['value']})")
    return by_ref, groups


# --------------------------------------------------------------------------- keyframing


def fcurves_of(obj):
    """Blender 4.4 moved fcurves into action layers/slots and kept `action.fcurves` as a
    compatibility view that is empty for slotted actions. Try both."""
    ad = obj.animation_data
    if not ad or not ad.action:
        return []
    out = list(getattr(ad.action, "fcurves", []))
    if out:
        return out
    for layer in getattr(ad.action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    return out


def shape(obj, path, frame, interp="BEZIER", easing="AUTO"):
    """Set how the curve leaves the key at `frame` -- Blender takes a segment's easing
    from its left-hand keyframe."""
    for fc in fcurves_of(obj):
        if fc.data_path != path:
            continue
        for kp in fc.keyframe_points:
            if abs(kp.co.x - frame) < 0.5:
                kp.interpolation = interp
                kp.easing = easing


def key_visibility(obj, frame):
    """Hidden until `frame`, visible from it. Stepped, so nothing half-fades in."""
    for path, before, after in (("hide_render", True, False),
                                ("hide_viewport", True, False)):
        setattr(obj, path, before)
        obj.keyframe_insert(path, frame=max(1, frame - 1))
        setattr(obj, path, after)
        obj.keyframe_insert(path, frame=frame)
        shape(obj, path, max(1, frame - 1), interp="CONSTANT")
        shape(obj, path, frame, interp="CONSTANT")


def drop(objs, start, land, rise_mm, drift_mm, spin_deg, tilt_deg, interp="CUBIC"):
    """Bring one logical part down onto its pads, decelerating the whole way.

    No overshoot and no rebound: the part slows continuously and stops on the pads, which
    is what placing a component looks like. `land` is the only frame that matters for
    accuracy -- every delta is zero there, so the landed state is the real board.

    The reveal sits at the start of the move, where an ease-out curve is at its fastest and
    the motion blur is longest: the part is already travelling when it appears, which reads
    as entering rather than popping into existence.
    """
    for obj in objs:
        key_visibility(obj, start)
        obj.delta_location = (drift_mm[0] / 1000.0, drift_mm[1] / 1000.0, rise_mm / 1000.0)
        obj.delta_rotation_euler = (math.radians(tilt_deg[0]), math.radians(tilt_deg[1]),
                                    math.radians(spin_deg))
        obj.keyframe_insert("delta_location", frame=start)
        obj.keyframe_insert("delta_rotation_euler", frame=start)
        shape(obj, "delta_location", start, interp=interp, easing="EASE_OUT")
        shape(obj, "delta_rotation_euler", start, interp=interp, easing="EASE_OUT")

        obj.delta_location = (0.0, 0.0, 0.0)
        obj.delta_rotation_euler = (0.0, 0.0, 0.0)
        obj.keyframe_insert("delta_location", frame=land)
        obj.keyframe_insert("delta_rotation_euler", frame=land)


def animate_components(by_ref, groups, joints, heroes, sched, hero_sched):
    """Group by group, then the three hero entrances. Nothing overlaps a group boundary."""
    rng = random.Random(SEED)
    land_frame = {}

    for label, spec in PLACEMENT:
        refs = groups.get(label) or []
        if not refs:
            continue
        first, last, _ = sched[label]
        step = (last - first) / max(1, len(refs) - 1)
        for i, ref in enumerate(refs):
            start = int(round(first + i * step))
            drop(by_ref[ref], start, start + spec["travel"],
                 rise_mm=rng.uniform(*spec["rise"]),
                 drift_mm=(rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)),
                 spin_deg=rng.uniform(-spec["spin"], spec["spin"]),
                 tilt_deg=spec["tilt"])
            land_frame[ref] = start + spec["travel"]

    # The heroes come down slower still, on a quartic ease so the last third of the travel
    # is very nearly a hover before it touches.
    for name, m in HERO_MOVES:
        start, land = hero_sched[name]
        drop(by_ref[heroes[name]], start, land, rise_mm=m["rise"], drift_mm=(0.0, 0.0),
             spin_deg=m["spin"], tilt_deg=m["tilt"], interp="QUART")
        land_frame[heroes[name]] = land

    # Solder joints belong to the part above them, so they appear when it lands. A fillet
    # sitting on a bare pad with nothing on it looks like a defect.
    orphan = 0
    for ref, objs in joints.items():
        frame = land_frame.get(ref)
        if frame is None:
            orphan += 1
            continue
        for obj in objs:
            key_visibility(obj, frame)
    if orphan:
        print(f"  note: {orphan} designator(s) with solder joints but no part animation")
    return land_frame


# ------------------------------------------------------------------------------- camera


def camera_beats(sched, hero_sched, end):
    """Camera beats, anchored to the placement schedule rather than to frame numbers.

    Each beat is (frame, azimuth, elevation, field width in mm at the target, lens, f-stop,
    exposure ride, target). Azimuth/elevation follow blender_scene's convention. `width`
    sets the distance -- it is how much of the board the frame spans, which is what
    actually matters for readability. Because the frames come out of `sched`, retiming a
    group moves the camera with it.

    `light` multiplies the calibrated rig. The calibration is per *frame content*, not per
    scene: the wide shots are half dark background and land at mean luma ~0.21, but a 48 mm
    close-up fills the frame with lit soldermask and measures 0.53 against a 0.16-0.34
    band. Riding it down into the close-ups is what a camera operator would do, and over
    30+ frames the ramp is invisible.
    """
    def at(label, which):
        return sched[label][which] if label in sched else BARE_HOLD

    def beat(f, az, el, width, lens, fstop, light, target):
        return dict(f=max(1, int(f)), az=az, el=el, width=width, lens=lens,
                    fstop=fstop, light=light, at=target)

    adc, driver, mcu = hero_sched["adc"], hero_sched["driver"], hero_sched["mcu"]
    return (
        # The board phase travels 104 degrees of azimuth and climbs 24, so the camera is
        # always moving somewhere -- but slowly, and always in the same direction, which is
        # what keeps a long populate sequence from feeling like a turntable.
        beat(1, -70, 20, 208, 60, 9.0, 1.00, "board"),
        beat(BARE_HOLD, -54, 26, 200, 64, 9.0, 0.97, "board"),
        beat(at("resistors", 2), -34, 34, 193, 68, 9.0, 0.92, "board"),
        beat(at("ceramics", 1), -12, 41, 188, 70, 9.0, 0.89, "board"),
        beat(at("ceramics", 2), 0, 44, 186, 70, 9.0, 0.88, "board"),
        beat(at("headers", 2), 18, 40, 181, 73, 8.0, 0.88, "board"),
        beat(at("terminals", 2), 27, 35, 179, 74, 8.0, 0.88, "board"),
        beat(at("harting", 2), 34, 31, 178, 74, 8.0, 0.88, "board"),
        # Three beats per hero, not two: the camera keeps pushing *through* the landing
        # instead of arriving early and sitting still while the part comes down.
        beat(adc[0], 6, 39, 92, 88, 6.3, 0.66, "adc"),
        beat(adc[0] + 42, -14, 37, 62, 95, 5.6, 0.57, "adc"),
        beat(adc[1] + 12, -4, 30, 46, 95, 5.6, 0.57, "adc"),
        beat(driver[0], -30, 37, 70, 95, 5.6, 0.60, "driver"),
        beat(driver[1], -48, 30, 52, 95, 5.6, 0.60, "driver"),
        # The widest, fastest move in the piece, and the only place that earns one: the
        # pull-back and swing right that reveals where the controller is about to land.
        beat(mcu[0], 6, 36, 150, 85, 7.1, 0.80, "mcu"),
        beat(mcu[1] - 20, 26, 31, 124, 85, 6.3, 0.74, "mcu"),
        beat(mcu[1] + 12, 40, 27, 106, 85, 6.3, 0.74, "mcu"),
        beat(end - FINAL_HOLD // 2, 32, 37, 190, 78, 9.0, 0.94, "board"),
        beat(end, 16, 44, 184, 78, 9.0, 0.94, "board"),
    )


def smootherstep(t: float) -> float:
    """C2-continuous ease. Its second derivative vanishes at both ends, so a camera
    crossing a beat has no visible kick in speed -- which smoothstep does have."""
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def orbit(center: Vector, az_deg: float, el_deg: float, radius: float) -> Vector:
    az, el = math.radians(az_deg), math.radians(el_deg)
    return center + Vector((math.sin(az) * math.cos(el),
                            -math.cos(az) * math.cos(el),
                            math.sin(el))) * radius


def build_camera(targets: dict, lights: dict, beats, end: int):
    """One camera, one tracked empty, and the whole move baked per frame.

    The camera is aimed by a Track To constraint on TARGET rather than by keyed rotation,
    so retargeting a beat at a component cannot leave the board tumbling out of frame.
    Depth of field focuses on the same empty, which means whatever the camera is looking
    at is what is sharp.
    """
    cam_data = bpy.data.cameras.new("CAM_ANIM")
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.dof.use_dof = True
    cam = bpy.data.objects.new("CAM_ANIM", cam_data)
    bpy.context.scene.collection.objects.link(cam)

    target = bpy.data.objects.new("TARGET", None)
    target.empty_display_size = 0.01
    bpy.context.scene.collection.objects.link(target)
    cam_data.dof.focus_object = target

    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    beats = sorted(beats, key=lambda b: b["f"])
    for frame in range(1, end + 1):
        lo = max((b for b in beats if b["f"] <= frame), key=lambda b: b["f"],
                 default=beats[0])
        hi = min((b for b in beats if b["f"] > frame), key=lambda b: b["f"], default=None)
        a = lo
        t = 0.0 if hi is None else smootherstep((frame - lo["f"]) / (hi["f"] - lo["f"]))
        b = hi or lo

        def mix(key):
            return a[key] + (b[key] - a[key]) * t

        aim = targets[a["at"]].lerp(targets[b["at"]], t)
        lens = mix("lens")
        # width is the horizontal field at the target, so the distance follows from the
        # lens rather than being guessed: half-width / tan(half-FOV).
        tan_h = (cam_data.sensor_width * 0.5) / lens
        radius = (mix("width") / 2000.0) / tan_h

        cam_data.lens = lens
        cam_data.dof.aperture_fstop = mix("fstop")
        target.location = aim
        cam.location = orbit(aim, mix("az"), mix("el"), radius)

        cam.keyframe_insert("location", frame=frame)
        target.keyframe_insert("location", frame=frame)
        cam_data.keyframe_insert("lens", frame=frame)
        cam_data.dof.keyframe_insert("aperture_fstop", frame=frame)

        # The look's ratio and the calibrated level are already in the light's energy;
        # this only rides the whole rig up and down, so the ratios survive.
        ride = mix("light")
        for name, obj in lights.items():
            obj.data.energy = obj.data["base_energy"] * studio.LOOKS[LOOK][name] * ride
            obj.data.keyframe_insert("energy", frame=frame)

    for obj in (cam, target, cam_data, *(o.data for o in lights.values())):
        for fc in fcurves_of(obj):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"  # the path is already smooth; don't overshoot
    print(f"  camera: {len(beats)} beats baked over {end} frames")
    return cam


# --------------------------------------------------------------------------------- main


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcb3d", type=Path, required=True)
    ap.add_argument("--parts", type=Path, required=True, help="components.json")
    ap.add_argument("--blend", type=Path)
    ap.add_argument("--outdir", type=Path, default=Path("out/anim"))
    ap.add_argument("--width", type=int, default=2560)
    ap.add_argument("--height", type=int, default=1440)
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--light-strength", type=float, default=0.60)  # purple, calibrated
    ap.add_argument("--frames", default="all",
                    help="'all', 'a-b', or a comma list of single frames")
    ap.add_argument("--no-motion-blur", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args(argv)

    print(f"building assembly animation from {args.pcb3d.name}")
    studio.reset_scene()
    objects = studio.import_pcb3d(args.pcb3d, 1016.0, "RASTERIZED")
    studio.fix_imported_normals(objects, 30.0)
    studio.restyle_components(objects)

    board = [o for o in objects if o.name.startswith("PCB_")]
    joints_by_ref, components = {}, []
    for obj in objects:
        if obj in board or obj.type != "MESH":
            continue
        if obj.name.startswith("SOLDER_"):
            # SOLDER_<value>_<ref>_<i>_<j>, from the exporter's pad naming.
            m = re.search(r"_([A-Za-z]+\d+)_(\d+)_(\d+)$", obj.name)
            if m:
                joints_by_ref.setdefault(m.group(1), []).append(obj)
            continue
        components.append(obj)
    print(f"  {len(board)} board object(s), {len(components)} component instances, "
          f"{sum(len(v) for v in joints_by_ref.values())} solder joints")
    for b in board:
        if max(abs(v) for v in b.rotation_euler) > 1e-6 or \
                (b.scale - Vector((1, 1, 1))).length > 1e-6:
            sys.exit(f"{b.name} is rotated or scaled; component deltas assume it is not")

    data = json.loads(args.parts.read_text(encoding="utf-8-sig"))
    parts = [p for p in data["parts"] if p["models"] and not p["dnp"]]
    print(f"  {args.parts.name}: {len(parts)} placed footprints from "
          f"{data['board']} (KiCad {data['kicad']})")

    offset = recover_offset(components, parts)
    bbox = data["edge_bbox_mm"]
    measured = Vector((bbox["left"] + bbox["width"] / 2,
                       -(bbox["top"] + bbox["height"] / 2)))
    if (offset + measured).length > 0.5:
        print(f"  warning: recovered offset disagrees with the board centre "
              f"{(-measured).x:+.3f}, {(-measured).y:+.3f} mm")
    matched = match_objects(components, parts, offset)
    heroes = resolve_heroes(parts)

    # A rotated sweep axis, so a group arrives as a diagonal front across the board rather
    # than as a column marching sideways.
    phi = math.radians(20)
    pos = {p["ref"]: (p["x"], -p["y"]) for p in parts}

    def order_key(ref):
        x, y = pos[ref]
        return x * math.cos(phi) + y * math.sin(phi)

    by_ref, groups = group_parts(components, matched, parts, heroes, order_key)
    sched, after_groups = schedule(groups)
    hero_sched, after_heroes = hero_schedule(after_groups)
    end = after_heroes + FINAL_HOLD
    print(f"  schedule ({end} frames, {end / FPS:.1f} s at {FPS} fps):")
    for label, _ in PLACEMENT:
        if label in sched:
            first, last, landed = sched[label]
            print(f"    {label:10s} moves {first:4d}-{last:4d}, all down by {landed:4d}")
    for name, _ in HERO_MOVES:
        print(f"    hero {name:5s} {hero_sched[name][0]:4d} -> {hero_sched[name][1]:4d}")

    lo, hi = studio.world_bbox(objects)
    lights = studio.build_lighting(lo, hi, args.light_strength)
    floor = studio.build_backdrop(lo, hi, 0.0)
    studio.configure_render(args.width, args.height, args.samples, not args.cpu)
    studio.apply_look(lights, LOOK)
    studio.set_backdrop(floor, BACKDROP)

    animate_components(by_ref, groups, joints_by_ref, heroes, sched, hero_sched)

    targets = {"board": (lo + hi) * 0.5}
    for name, ref in heroes.items():
        # Aim a little above the part: at these focal lengths, aiming at the pads puts the
        # part in the lower half of the frame.
        top = max(o.matrix_world.translation.z for o in by_ref[ref])
        centre = sum((o.matrix_world.translation for o in by_ref[ref]),
                     Vector()) / len(by_ref[ref])
        targets[name] = Vector((centre.x, centre.y, top + 0.004))
    cam = build_camera(targets, lights, camera_beats(sched, hero_sched, end), end)

    scene = bpy.context.scene
    scene.camera = cam
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, end
    scene.render.use_motion_blur = not args.no_motion_blur
    scene.render.motion_blur_shutter = 0.5
    scene.render.use_persistent_data = True   # keep the BVH between frames
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str((args.outdir / "frame_").resolve())

    if args.blend:
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
        print(f"  saved {args.blend}")
    if args.no_render:
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    print(f"  rendering {args.frames} at {args.width}x{args.height}, "
          f"{args.samples} samples, {FPS} fps")
    if args.frames == "all":
        bpy.ops.render.render(animation=True)
    elif "-" in args.frames:
        a, b = (int(v) for v in args.frames.split("-"))
        scene.frame_start, scene.frame_end = a, b
        bpy.ops.render.render(animation=True)
    else:
        for f in (int(v) for v in args.frames.split(",")):
            scene.frame_set(f)
            scene.render.filepath = str((args.outdir / f"frame_{f:04d}").resolve())
            bpy.ops.render.render(write_still=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
