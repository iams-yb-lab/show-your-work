"""Every sound cue in the assembly film, taken from the tables that produced the pictures.

    blender --background --factory-startup --python tools/audio_cues.py -- \
        --parts out/scene/components_v2.json --out out/audio/cues.json

This imports `animate_assembly_v2` and re-runs its schedule rather than reading frame
numbers off a stopwatch, which is the only way the audio can be *exactly* in sync: the
land frame a tick is placed on is the same integer the renderer keyed the landing to. Retime
the film and regenerate, and every cue moves with it. Nothing here is authored by ear.

It needs no board and no .pcb3d -- the schedule is a pure function of the parts list and the
module's own constants -- so it runs in about a second.

Sector is degrees about the camera's view axis, 0 = frame right, 180 = frame left (see the
comment above HERO_MOVES). That is a real pan value, so it is carried through per part.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "picture"))
import animate_assembly_v2 as v2  # noqa: E402

# Package -> a size class, which the mixer turns into pitch and weight. Ordered: the first
# pattern that matches a footprint wins, so the specific through-hole and module entries have
# to precede the generic metric-package ones.
CLASSES = (
    ("Teensy41", "module"),
    ("HARTING", "connector"),
    ("TerminalBlock", "connector"),
    ("PinHeader", "connector"),
    ("RES-ADJ-TH", "trimmer"),
    ("IND-SMD", "magnetic"),
    ("CAP-SMD_BD", "electrolytic"),
    ("SW-SMD", "switch"),
    ("LFCSP", "ic"),
    ("HTSSOP", "ic"),
    ("SOIC", "ic"),
    ("SOT-23", "semi"),
    ("SOD-123", "semi"),
    ("LED-SMD", "semi"),
    ("_2512_", "chip_large"),
    ("_1206_", "chip_large"),
    ("_0805_", "chip_mid"),
    ("_0603_", "chip_mid"),
    ("_0402_", "chip_small"),
)


def size_class(footprint: str) -> str:
    leaf = footprint.split(":")[-1]
    for pattern, name in CLASSES:
        if pattern in leaf:
            return name
    return "chip_mid"


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", type=Path, default=Path("out/scene/components_v2.json"))
    ap.add_argument("--out", type=Path, default=Path("out/audio/cues.json"))
    args = ap.parse_args(argv)

    data = json.loads(args.parts.read_text(encoding="utf-8-sig"))
    parts = [p for p in data["parts"] if p["models"] and not p["dnp"]]
    part_of = {p["ref"]: p for p in parts}

    heroes = v2.resolve_heroes(parts)
    _pos_mm, order_key = v2.order_key_factory(parts)
    refs = [p["ref"] for p in parts]
    groups = v2.group_parts(refs, parts, heroes, order_key)
    plan, subwaves = v2.wave_schedule(groups, parts, order_key)
    after_waves = max(land for _s, land, _sec, _sp in plan.values())
    hero_sched, _after = v2.hero_schedule(after_waves)
    end = int(v2.CAM_BEATS[-1][0])

    wave_of = {}
    waves = []
    for label, j, sector, band, first, last in subwaves:
        waves.append(dict(label=label, index=j + 1, sector=sector, first=first, last=last,
                          refs=list(band),
                          spawn=min(plan[r][0] for r in band),
                          land_first=min(plan[r][1] for r in band),
                          land_last=max(plan[r][1] for r in band)))
        for r in band:
            wave_of[r] = len(waves) - 1

    supporting = [
        dict(ref=ref, spawn=start, land=land, sector=sector, wave=wave_of.get(ref),
             cls=size_class(part_of[ref]["footprint"]), value=part_of[ref]["value"])
        for ref, (start, land, sector, _spec) in sorted(plan.items())
    ]
    hero_cues = [
        dict(name=name, ref=heroes[name], spawn=start, land=land, sector=spec["sector"],
             cls=size_class(part_of[heroes[name]]["footprint"]),
             value=part_of[heroes[name]]["value"])
        for name, (start, land, spec) in hero_sched.items()
    ]

    cues = dict(
        fps=v2.FPS,
        frames=end,
        duration=end / v2.FPS,
        # Fabrication, straight off the module constants. One home, as ever.
        fab=dict(copper_end=v2.F_COPPER_END,
                 etch_top=list(v2.F_ETCH_TOP), etch_bot=list(v2.F_ETCH_BOT),
                 etch_phi_top=v2.ETCH["phi_top"], etch_phi_bot=v2.ETCH["phi_bot"],
                 film_fly=v2.F_FILM_FLY, film_contact=list(v2.F_FILM_CONTACT),
                 film_handoff=v2.F_HANDOFF,
                 pads=list(v2.F_PADS), silk=list(v2.F_SILK),
                 # Fabrication ends when the last silkscreen travels; population begins when
                 # the first part sets off. The gap between them is the film's one structural
                 # hinge, and the mixer hangs the music grid on it. Both are schedule
                 # numbers -- neither is a frame chosen by watching.
                 done=v2.F_SILK[1],
                 populate=min(s for s, _l, _sec, _sp in plan.values())),
        waves=waves,
        parts=supporting,
        heroes=hero_cues,
        probes=[dict(frame=f, caption=c) for f, c in v2.PROBES],
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(cues, indent=1), encoding="utf-8")

    counts = {}
    for p in supporting:
        counts[p["cls"]] = counts.get(p["cls"], 0) + 1
    print(f"{args.out}: {len(supporting)} supporting + {len(hero_cues)} hero cues over "
          f"{end} frames ({end / v2.FPS:.2f} s)")
    print("  classes: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"  waves: {len(waves)}   fabrication done at frame {cues['fab']['done']} "
          f"({cues['fab']['done'] / v2.FPS:.3f} s)")
    for h in hero_cues:
        print(f"  hero {h['name']:6s} {h['ref']:4s} spawn {h['spawn']:4d} land {h['land']:4d} "
              f"({h['land'] / v2.FPS:6.3f} s)  sector {h['sector']:3.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
