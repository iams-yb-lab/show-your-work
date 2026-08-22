"""Export a .pcb3d for pcb2blender from KiCad 10, headlessly.

pcb2blender ships a KiCad *GUI* plugin pinned to `kicad_version_max = "9.0"`, so the
Plugin Manager refuses to install it on KiCad 10. Every pcbnew API the plugin uses is
still present and working in 10.0.4 (verified call-by-call) -- the pin is metadata, not
a real incompatibility. So instead of installing the plugin we drive its own exporter
code directly, with a handful of patches:

  0. upstream's fixed scratch directory leaks files between runs  -> use a fresh one.
  1. `pcbnew.GetBoard()` returns None outside the GUI  -> point it at our loaded board.
  2. `pcbnew.ExportVRML()` returns False outside the GUI, because the 3D model path
     resolver has no project loaded and cannot expand ${KICAD10_3DMODEL_DIR} /
     ${KIPRJMOD}  -> shell out to `kicad-cli pcb export vrml`, which loads the project
     properly. The flags below are the exact equivalents of the plugin's call.
  3. KiCad 10 renumbered PAD_DRILL_SHAPE (see DRILL_SHAPE_K10_TO_P2B) -> remap it.
  4. `get_stackup()` reads mask/silk colour out of the board file  -> wrap it so we can
     render colour variants without editing the board.
  5. a part's 3D model is a property of the board file  -> `--swap-model` replaces it in the
     loaded board only, so a better model can be rendered without a board edit.

Everything else -- layer SVG plotting, pad extraction, bounds, the .pcb3d zip layout --
is upstream code in vendor/pcb2blender_export/, called unmodified.

Run with KiCad's bundled Python, not a system Python (it needs `pcbnew`):

    "C:/Program Files/KiCad/10.0/bin/python.exe" export_pcb3d.py \
        ../PCB_new.kicad_pcb out/pcb_black.pcb3d --mask-color BLACK --finish ENIG
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "vendor"))

import pcbnew  # noqa: E402

from pcb2blender_export import export as p2b_export  # noqa: E402
from pcb2blender_export.pcb3d import DrillShape, KiCadColor, Stackup, SurfaceFinish  # noqa: E402

KICAD_CLI_DEFAULT = Path(sys.prefix) / "kicad-cli.exe"

# KiCad 10 renumbered PAD_DRILL_SHAPE: it is now UNDEFINED=0, CIRCLE=1, OBLONG=2, where
# pcb2blender (written against KiCad 9) reads CIRCULAR=0, OVAL=1. Confirmed from the
# drill dimensions themselves rather than from either enum header: on this board all 417
# pads reporting 1 have equal X/Y drill (1.3 x 1.3 mm, round) and the single pad
# reporting 2 is 1.0 x 1.05 mm (genuinely oblong). Unpatched, every round hole in the
# board would be modelled as a slot.
DRILL_SHAPE_K10_TO_P2B = {
    0: DrillShape.CIRCULAR,  # UNDEFINED -- SMD pads, drill size is 0 so shape is moot
    1: DrillShape.CIRCULAR,
    2: DrillShape.OVAL,
}


def export_vrml_via_cli(kicad_cli: Path, board_path: Path):
    """Build a `pcbnew.ExportVRML`-compatible replacement bound to this board.

    Argument mapping, plugin call -> kicad-cli flag:
        aMMtoWRMLunit=0.001    -> --units m       (1 mm = 0.001 scene units)
        aIncludeUnspecified=True  -> (default; --no-unspecified omitted)
        aIncludeDNP=False      -> --no-dnp
        aExport3DFiles=True    -> implied by --models-dir
        aUseRelativePaths=True -> --models-relative
        a3D_Subdir             -> --models-dir
        aXRef/aYRef=0.0        -> --user-origin 0x0mm
    """

    def _export_vrml(
        aFullFileName,
        aMMtoWRMLunit,
        aIncludeUnspecified,
        aIncludeDNP,
        aExport3DFiles,
        aUseRelativePaths,
        a3D_Subdir,
        aXRef,
        aYRef,
    ):
        units = {0.001: "m", 1.0: "mm", 0.0393701: "in"}.get(round(aMMtoWRMLunit, 7))
        if units is None:
            raise ValueError(f"unmapped aMMtoWRMLunit {aMMtoWRMLunit!r}")

        out = Path(aFullFileName)
        out.parent.mkdir(parents=True, exist_ok=True)
        models_dir = Path(a3D_Subdir)

        if models_dir.exists():
            shutil.rmtree(models_dir, ignore_errors=True)

        cmd = [
            str(kicad_cli), "pcb", "export", "vrml",
            "-o", str(out),
            "--units", units,
            # kicad-cli writes the models dir relative to the output file, so pass a
            # bare name and let it land next to pcb.wrl -- which is where the plugin
            # puts it too.
            "--models-dir", models_dir.name,
            "--user-origin", f"{aXRef}x{aYRef}mm",
            "--force",
        ]
        if aUseRelativePaths:
            cmd.append("--models-relative")
        if not aIncludeUnspecified:
            cmd.append("--no-unspecified")
        if not aIncludeDNP:
            cmd.append("--no-dnp")
        cmd.append(str(board_path))

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not out.exists():
            sys.exit(
                f"kicad-cli VRML export failed (exit {result.returncode}):\n"
                f"{result.stdout}\n{result.stderr}"
            )

        produced = out.parent / models_dir.name
        if produced.resolve() != models_dir.resolve():
            produced.replace(models_dir)

        n = len(list(models_dir.glob("*.wrl"))) if models_dir.exists() else 0
        print(f"  VRML: {out.stat().st_size / 1e6:.1f} MB board + {n} component models")
        return True

    return _export_vrml


def override_stackup(mask: str | None, silk: str | None, finish: str | None):
    """Wrap upstream get_stackup so colour variants don't require board edits."""
    upstream = p2b_export.get_stackup

    def _get_stackup(board) -> Stackup:
        stackup = upstream(board)
        if mask:
            stackup.mask_color, stackup.mask_color_custom = _parse_color(mask)
        if silk:
            stackup.silks_color, stackup.silks_color_custom = _parse_color(silk)
        if finish:
            stackup.surface_finish = SurfaceFinish[finish.upper()]
        print(
            f"  stackup: {stackup.thickness_mm:.3f} mm, "
            f"mask={_show(stackup.mask_color, stackup.mask_color_custom)}, "
            f"silk={_show(stackup.silks_color, stackup.silks_color_custom)}, "
            f"finish={stackup.surface_finish.name}"
        )
        return stackup

    return _get_stackup


def swap_models(board, swaps: dict[str, list[tuple[str, tuple[float, ...]]]]):
    """Replace a footprint's 3D model(s) in the loaded board, never on disk.

    Same reasoning as the stackup override: which model renders is a property of the
    *render*, not of the board, and a vendor CAD assembly has no business being wired into
    the design files. The board is opened read-only and closed unwritten either way.

    Several models can be given for one designator, which is how a part gets assembled out
    of pieces -- a vendor board model plus the pin headers it stands on, say.
    """
    seen = set()
    for fp in board.Footprints():
        ref = fp.GetReference()
        if ref not in swaps:
            continue
        seen.add(ref)
        was = [m.m_Filename for m in fp.Models()]
        fp.Models().clear()
        for path, t in swaps[ref]:
            model = pcbnew.FP_3DMODEL()
            model.m_Filename = path
            model.m_Show = True
            model.m_Offset = pcbnew.VECTOR3D(t[0], t[1], t[2])
            model.m_Rotation = pcbnew.VECTOR3D(t[3], t[4], t[5])
            s = t[6] if len(t) > 6 else 1.0
            model.m_Scale = pcbnew.VECTOR3D(s, s, s)
            fp.Models().push_back(model)
            print(f"  {ref}: + {Path(path).name}  offset={t[0:3]} rot={t[3:6]} scale={s}")
        print(f"      (was {', '.join(Path(w).name for w in was) or 'nothing'})")
    missing = set(swaps) - seen
    if missing:
        raise SystemExit(f"--swap-model: no such designator(s) on the board: {sorted(missing)}")


def _parse_swaps(values: list[str]):
    """`REF=PATH[@ox,oy,oz,rx,ry,rz[,scale]]`, repeatable and additive per designator.

    The transform is millimetres and degrees in KiCad's own model frame, exactly as the
    footprint's `(offset)` / `(rotate)` would be -- needed because a vendor CAD model puts
    its origin wherever the assembly happened to be drawn.
    """
    out: dict[str, list[tuple[str, tuple[float, ...]]]] = {}
    for item in values or []:
        if "=" not in item:
            raise SystemExit(f"expected REF=PATH[@transform], got {item!r}")
        ref, rhs = item.split("=", 1)
        path, _, tf = rhs.partition("@")
        nums = tuple(float(v) for v in tf.split(",")) if tf.strip() else (0.0,) * 6
        if len(nums) not in (6, 7):
            raise SystemExit(f"--swap-model {ref}: transform needs 6 or 7 numbers, "
                             f"got {len(nums)}")
        out.setdefault(ref.strip(), []).append((path.strip(), nums))
    return out


def _parse_color(value: str) -> tuple[KiCadColor, tuple[float, ...]]:
    if value.startswith("#"):
        rgb = value.lstrip("#")
        if len(rgb) != 6:
            raise SystemExit(f"custom colour must be #RRGGBB, got {value!r}")
        return KiCadColor.CUSTOM, tuple(int(rgb[i : i + 2], 16) / 255 for i in (0, 2, 4))
    try:
        return KiCadColor[value.upper()], (0.0, 0.0, 0.0)
    except KeyError:
        named = ", ".join(c.name for c in KiCadColor if c is not KiCadColor.CUSTOM)
        raise SystemExit(f"unknown colour {value!r}; use #RRGGBB or one of: {named}")


def remap_drill_shape(raw: int) -> DrillShape:
    shape = DRILL_SHAPE_K10_TO_P2B.get(raw)
    if shape is None:
        print(f"  warning: unmapped KiCad drill shape {raw}, treating as circular")
        return DrillShape.CIRCULAR
    return shape


def _show(color: KiCadColor, custom: tuple[float, ...]) -> str:
    if color is not KiCadColor.CUSTOM:
        return color.name
    return "#" + "".join(f"{round(c * 255):02X}" for c in custom)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("board", type=Path, help="input .kicad_pcb")
    ap.add_argument("output", type=Path, help="output .pcb3d")
    ap.add_argument("--mask-color", help="soldermask: name (BLACK, PURPLE, ...) or #RRGGBB")
    ap.add_argument("--silk-color", help="silkscreen: name or #RRGGBB")
    ap.add_argument("--finish", choices=[f.name for f in SurfaceFinish], help="copper finish")
    ap.add_argument("--kicad-cli", type=Path, default=KICAD_CLI_DEFAULT)
    ap.add_argument("--swap-model", action="append",
                    metavar="REF=PATH[@ox,oy,oz,rx,ry,rz[,s]]",
                    help="render different 3D model(s) for one part, in memory only. "
                         "${KIPRJMOD} and ${KICAD10_3DMODEL_DIR} both expand; repeat the "
                         "flag for the same designator to build it out of several models")
    args = ap.parse_args()
    swaps = _parse_swaps(args.swap_model)

    board_path = args.board.resolve()
    if not board_path.exists():
        return print(f"no such board: {board_path}") or 1
    if not args.kicad_cli.exists():
        return print(f"no kicad-cli at {args.kicad_cli} (pass --kicad-cli)") or 1

    # Resolve before the chdir below, or a relative output lands in the wrong directory.
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"pcbnew {pcbnew.GetBuildVersion()}  ->  {output}")
    board = pcbnew.LoadBoard(str(board_path))

    # Patch 0: upstream reuses one fixed scratch directory and its init_tempdir() gives up
    # silently when the tree is locked ("if this still doesn't work, fuck it"). Anything
    # left behind gets zipped into the next .pcb3d -- we found year-old component models
    # riding along in the archive that way. They are never instanced by pcb.wrl so they
    # don't render, but they bloat the file and read as parts that are still on the board.
    # A fresh directory per run removes the failure mode instead of retrying the cleanup.
    scratch = Path(tempfile.mkdtemp(prefix="pcb2blender_"))
    p2b_export.get_tempdir = lambda: scratch

    # Patch 1: upstream calls pcbnew.GetBoard(), which only works inside the GUI.
    pcbnew.GetBoard = lambda: board
    # Patch 3: KiCad 10 renumbered the drill shape enum out from under pcb2blender.
    p2b_export.DrillShape = remap_drill_shape
    # Patch 4: colour variants without touching the board file.
    p2b_export.get_stackup = override_stackup(args.mask_color, args.silk_color, args.finish)

    # Patch 5: a better model for one part. Everything else here works on the loaded board,
    # but the VRML comes from kicad-cli, which re-reads the board from *disk* -- so an
    # in-memory swap is invisible to it and has to be handed over as a file. Written beside
    # the original, because ${KIPRJMOD} resolves relative to the board's directory, and
    # deleted in the finally below. `PCB_new.kicad_pcb` itself is still never written.
    board_for_vrml, scratch_board = board_path, None
    if swaps:
        swap_models(board, swaps)
        scratch_board = board_path.with_name(f".pcb3d_swap_{os.getpid()}.kicad_pcb")
        pcbnew.SaveBoard(str(scratch_board), board)
        board_for_vrml = scratch_board
    # Patch 2: standalone ExportVRML can't resolve ${KICAD10_3DMODEL_DIR}/${KIPRJMOD}.
    pcbnew.ExportVRML = export_vrml_via_cli(args.kicad_cli, board_for_vrml)

    boarddefs, ignored = p2b_export.get_boarddefs(board)
    if ignored:
        print(f"  ignored PCB3D_ markers: {ignored}")

    # KiCad plots into the CWD-relative output dir in some paths; keep it predictable.
    os.chdir(board_path.parent)
    try:
        p2b_export.export_pcb3d(output, boarddefs)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        if scratch_board is not None:
            # SaveBoard writes a .kicad_pro and .kicad_prl alongside the board, so the
            # cleanup has to take the whole set or the project directory collects litter.
            for suffix in (".kicad_pcb", ".kicad_pro", ".kicad_prl"):
                scratch_board.with_suffix(suffix).unlink(missing_ok=True)

    size = output.stat().st_size / 1e6
    print(f"  wrote {output.name}  ({size:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
