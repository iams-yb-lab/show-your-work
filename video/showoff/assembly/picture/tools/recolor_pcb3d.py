"""Change a .pcb3d's soldermask / silkscreen colour without re-exporting from KiCad.

The colours live in one small member of the archive, layers/stackup.toml, so trying a
different mask shade is a rewrite of that file rather than a full board export. Useful
when iterating on look (and when the board is open in KiCad and shouldn't be touched).

    python tools/recolor_pcb3d.py out/pcb_red.pcb3d out/pcb_deepred.pcb3d --mask "#A81F16"

Plain python -- no pcbnew or bpy needed.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

STACKUP = "layers/stackup.toml"
NAMED = {"CUSTOM", "GREEN", "RED", "BLUE", "PURPLE", "BLACK", "WHITE", "YELLOW"}


def encode(value: str) -> tuple[str, str]:
    """-> (kicad colour name, custom rgb triple as a toml array)."""
    if value.startswith("#"):
        rgb = value.lstrip("#")
        if len(rgb) != 6:
            sys.exit(f"custom colour must be #RRGGBB, got {value!r}")
        triple = ", ".join(f"{int(rgb[i:i + 2], 16) / 255:.6f}" for i in (0, 2, 4))
        return "CUSTOM", f"[ {triple} ]"
    name = value.upper()
    if name not in NAMED:
        sys.exit(f"unknown colour {value!r}; use #RRGGBB or one of {sorted(NAMED - {'CUSTOM'})}")
    return name, "[ 0.0, 0.0, 0.0 ]"


def rewrite(stackup: str, mask: str | None, silk: str | None, finish: str | None) -> str:
    out = []
    for line in stackup.splitlines():
        key = line.split("=", 1)[0].strip()
        if mask and key == "mask_color":
            out.append(f'mask_color = "{encode(mask)[0]}"')
        elif mask and key == "mask_color_custom":
            out.append(f"mask_color_custom = {encode(mask)[1]}")
        elif silk and key == "silks_color":
            out.append(f'silks_color = "{encode(silk)[0]}"')
        elif silk and key == "silks_color_custom":
            out.append(f"silks_color_custom = {encode(silk)[1]}")
        elif finish and key == "surface_finish":
            out.append(f'surface_finish = "{finish.upper()}"')
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", type=Path)
    ap.add_argument("dest", type=Path)
    ap.add_argument("--mask")
    ap.add_argument("--silk")
    ap.add_argument("--finish", choices=["HASL", "ENIG", "NONE"])
    args = ap.parse_args()

    if not any((args.mask, args.silk, args.finish)):
        return print("nothing to change; pass --mask/--silk/--finish") or 1
    if args.source.resolve() == args.dest.resolve():
        return print("refusing to rewrite in place; give a different dest") or 1

    args.dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source, args.dest)

    with ZipFile(args.source) as zf:
        if STACKUP not in zf.namelist():
            return print(f"{args.source} has no {STACKUP}") or 1
        members = [(i, zf.read(i.filename)) for i in zf.infolist()]
        original = zf.read(STACKUP).decode("utf-8")

    updated = rewrite(original, args.mask, args.silk, args.finish)

    # Zip members can't be replaced in place, so rewrite the archive wholesale.
    with ZipFile(args.dest, "w", compression=ZIP_DEFLATED) as out:
        for info, data in members:
            out.writestr(info, updated.encode("utf-8") if info.filename == STACKUP else data)

    print(f"{args.source.name} -> {args.dest.name}")
    for line in updated.splitlines():
        if "color" in line or "finish" in line:
            was = next((o for o in original.splitlines()
                        if o.split("=")[0].strip() == line.split("=")[0].strip()), "")
            print(f"  {line}" + (f"   (was {was.split('=', 1)[1].strip()})" if was != line else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
