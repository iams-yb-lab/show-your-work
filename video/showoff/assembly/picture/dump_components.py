"""Dump the board's component list -- designators and all -- for the animation.

The .pcb3d carries geometry but no designators: pcb2blender instances components by
3D-model filename, so the Blender scene has an object called `LFCSP-32_L5.0-W5.0-H0.8-P0.50`
and no idea that it is the ADC. This writes the missing half, straight out of the board
file, so `animate_assembly.py` can group parts by what they *are* rather than by how they
look.

Positions are millimetres in KiCad's own frame (y grows downward). The 3D-model offset is
included because it moves the imported object's origin away from the footprint origin --
J8's Harting model is offset 1.25 mm in y, which is exactly the residual you see if you
match on footprint position alone.

`--swap-model` takes the same arguments as `export_pcb3d.py`, and must be given the same ones:
this file describes what was *exported*, and if the export swapped a part's model then a dump
that still names the board's own model will not match the scene. Both callers get them from
`tools/model-swaps.ps1`, so they cannot drift apart.

Run with KiCad's bundled Python (it needs `pcbnew`):

    "C:/Program Files/KiCad/10.0/bin/python.exe" dump_components.py \
        ../PCB_new.kicad_pcb out/scene/components.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pcbnew

from export_pcb3d import _parse_swaps  # same syntax, parsed in exactly one place

TO_MM = 1e-6  # pcbnew internal units (nm) -> mm


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("board", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--swap-model", action="append",
                    metavar="REF=PATH[@ox,oy,oz,rx,ry,rz[,s]]",
                    help="the same swaps the export was given")
    args = ap.parse_args()
    board_path, output = args.board.resolve(), args.output.resolve()
    swaps = _parse_swaps(args.swap_model)
    board = pcbnew.LoadBoard(str(board_path))

    parts = []
    for fp in board.Footprints():
        attrs = fp.GetAttributes()
        ref = fp.GetReference()
        if ref in swaps:
            models = [{"file": Path(path.replace("\\", "/")).stem,
                       "offset": [t[0], t[1], t[2]]} for path, t in swaps[ref]]
            print(f"  {ref}: {len(models)} swapped model(s): "
                  f"{', '.join(m['file'] for m in models)}")
        else:
            models = [{
                "file": Path(str(model.m_Filename).replace("\\", "/")).stem,
                # KiCad states the model offset in mm in the footprint's own frame,
                # before the footprint's rotation is applied.
                "offset": [model.m_Offset[0], model.m_Offset[1], model.m_Offset[2]],
            } for model in fp.Models()]
        pos = fp.GetPosition()
        parts.append({
            "ref": ref,
            "value": fp.GetValue(),
            "footprint": str(fp.GetFPIDAsString()),
            "x": pos.x * TO_MM,
            "y": pos.y * TO_MM,
            "rot": fp.GetOrientationDegrees(),
            "back": bool(fp.IsFlipped()),
            "dnp": bool(attrs & pcbnew.FP_DNP),
            "models": models,
        })

    box = board.ComputeBoundingBox(aBoardEdgesOnly=True)
    data = {
        "board": str(board_path.name),
        "kicad": pcbnew.GetBuildVersion(),
        # The importer centres the board on the origin, so this is what maps a board
        # coordinate onto a Blender one. animate_assembly.py checks it rather than
        # trusting it -- see recover_offset().
        "edge_bbox_mm": {
            "left": box.GetLeft() * TO_MM,
            "top": box.GetTop() * TO_MM,
            "width": box.GetWidth() * TO_MM,
            "height": box.GetHeight() * TO_MM,
        },
        "parts": parts,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=1), encoding="utf-8")

    placed = [p for p in parts if p["models"] and not p["dnp"]]
    n_models = sum(len(p["models"]) for p in placed)
    print(f"{output.name}: {len(parts)} footprints, "
          f"{len(placed)} placed ({n_models} model instances), "
          f"board {data['edge_bbox_mm']['width']:.1f} x {data['edge_bbox_mm']['height']:.1f} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
