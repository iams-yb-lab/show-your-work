# PCB renders

Board → `.pcb3d` → studio-lit Blender scene → presentation stills and an assembly animation,
scripted end to end so anything here can be rebuilt from `PCB_new.kicad_pcb`.

```powershell
.\render.ps1 -Draft      # stills:    960x540 preview of every shot, ~1 min
.\render.ps1             # stills:    3840x2160 finals
.\animate.ps1 -Draft     # animation: 600-frame 960x540 preview + MP4, ~20 min
.\animate.ps1            # animation: 2560x1440, 128 samples
```

## One-time setup

Needs KiCad 10 (for `pcbnew` + `kicad-cli`) and Blender 4.2+. Both are located by
`tools/find-tools.ps1`, which searches Program Files *and* `C:\tools`, newest version first,
so the two machines need no per-machine edits. `-KicadPython`/`-KicadCli`/`-Blender` override.

**Neither needs administrator rights.** Blender ships a portable `.zip`; KiCad's installer
wants elevation, but its payload is an NSIS archive, so `7z x kicad-<ver>-x86_64.exe` unpacks a
working tree — `bin\python.exe` with `pcbnew`, `bin\kicad-cli.exe`, and `share\kicad\3dmodels`.

Install the Blender add-on once:

```powershell
& <blender.exe> --command extension install-file -r user_default -e <pcb2blender_importer_*.zip>
```

Get that zip from [pcb2blender releases](https://github.com/30350n/pcb2blender/releases) —
pick the asset matching your Blender (`_b4-5lts` covers 4.2 → 5.1). Checksums of the
versions this was built against are in `vendor/`; verify against them rather than trusting the
download. `blender_scene.py` enables the add-on itself, so it works under `--factory-startup`
and doesn't depend on your Blender prefs.

## Why this doesn't just use the KiCad plugin

pcb2blender's KiCad-side exporter is pinned `kicad_version_max = "9.0"`, so the Plugin
Manager refuses to install it on KiCad 10. Every `pcbnew` call it makes still works on
10.0.4 — that pin is metadata, not a real incompatibility — so `export_pcb3d.py` drives
upstream's own exporter code directly instead, with four patches:

| Problem on KiCad 10 | Fix |
| --- | --- |
| `pcbnew.GetBoard()` returns `None` outside the GUI | point it at the board we loaded |
| `pcbnew.ExportVRML()` returns `False` outside the GUI — the model resolver has no project, so `${KICAD10_3DMODEL_DIR}` and `${KIPRJMOD}` never expand | shell out to `kicad-cli pcb export vrml`, whose flags map 1:1 onto the plugin's arguments |
| `PAD_DRILL_SHAPE` was renumbered to `UNDEFINED=0, CIRCLE=1, OBLONG=2`, but pcb2blender reads `CIRCULAR=0, OVAL=1` | remap it — unpatched, every round hole on the board is modelled as a slot |
| mask colour is read out of the board file | wrap it, so colour variants need no board edit |

`vendor/pcb2blender_export/` is upstream code, unmodified. `PAD_ATTRIB`, `PAD_SHAPE` and
`PAD_PROP` were each checked against KiCad 10 and still match, so they are left alone.

## Adjusting the scene

`render.ps1` saves `../../../out/showoff/scene/pcb_<variant>.blend`. Open it and everything is named:

| Object | What it does |
| --- | --- |
| `KEY` | front-left main light; defines component shadows |
| `FILL` | broad, dim, opposite the key; lifts the shadow side |
| `RIM` | low and behind; skims the board edge — this is what stops a dark mask disappearing into the background |
| `TOP` | overhead softbox for even sheen across the mask |
| `BACKDROP` | floor plane; roughness is high on purpose (a smooth floor throws a blown-out hotspot at grazing camera angles) |
| `FOCUS` | empty the cameras' depth of field tracks |
| `CAM_<shot>` | one camera per shot |

### The four shots

Each carries its own lighting ratio (`LOOKS`) and backdrop, not just a camera angle, so
they are re-applied per render rather than baked once.

| Shot | For | Look | Backdrop |
| --- | --- | --- | --- |
| `slide` | dropping onto a slide — barely tilted, whole board, no depth of field so every trace stays sharp | `even` | transparent |
| `cinematic` | mood: low, long lens, f/4, board off-centre, lit almost entirely by rim | `dramatic` | dark |
| `showcase` | the interesting angle — board thrown diagonally across frame, strong key-to-fill modelling | `product` | dark |
| `demo` | official product shot, square-on three-quarter on a bright neutral sweep | `clean` | light |

`top` (orthographic), `detail` (cropped in) and `usb` (a diagnostic that frames the Teensy's
micro-USB shell alone, for judging crease shading on thin sheet metal) are also available.
`top` and `slide` are the best views for showing copper: traces read far more clearly looking
straight down than at a hero angle, where the mask relief over copper is nearly edge-on.

Output lands in `../../../out/showoff/stills/`, scene files in `../../../out/showoff/scene/`, comparison sheets in
`../../../out/showoff/compare/`. All of `../../../out/showoff/` is gitignored and regenerable; the chosen final set — purple —
is committed in `../gallery/`.

Light energies scale with board size, so the rig re-exposes itself on a different board.
To rebalance, change `--light-strength` (moves all four, keeps the ratios) rather than editing
one light. Cameras frame themselves from the measured bounding box: `fill` in `SHOTS` is the
fraction of frame the board spans, so `0.93` leaves a margin and `2.15` crops in.

Exposure is tuned to a measured number, not by eye — aim for mean luma 0.16–0.34 with under
1 % clipped. A lighter soldermask reflects much more than a dark one, so mask colour and
`--light-strength` have to move together.

```powershell
& $blender --background --factory-startup --python tools\measure_exposure.py -- out\stills\red_showcase.png
```

## The assembly animation

`animate.ps1` → `animate_assembly.py`: 974 frames, 32.5 s at 30 fps, bare board → populated
controller in one continuous camera move — six staggered waves of passives, four groups of
larger parts, individual entrances for the ADC, the TEC driver and the Teensy, then a held
hero shot. Two tables at the top of the script are the whole design: `T` (the storyboard, in
frames) and `BEATS` (camera azimuth, elevation, field width, lens, f-stop, exposure, target).

Two things make it safe to re-run:

- **Parts move by their delta transform**, so "landed" is delta = 0 and the last frame
  reconstructs the imported board exactly. No retiming can leave a part off its pads.
- **Parts are identified from the board, not from the scene.** `dump_components.py` writes the
  designators the `.pcb3d` doesn't carry, joined by position with the residual reported; the
  ADC and driver are picked by part number (`AD7124`, `MAX1968`), never by designator, since
  those get renumbered. A failed join stops the render.

Frames land in `../../../out/showoff/anim/<variant>/` as PNGs — resumable, unlike rendering straight to video —
and `tools/encode_frames.py` turns them into `../../../out/showoff/anim/assembly_<variant>.mp4` with Blender's
own FFmpeg.

### v2: fabrication, then assembly

`animate_v2.ps1` → `animate_assembly_v2.py`: 2520 frames, 84.0 s at 30 fps, copper laminate →
etched → coated → plated → printed → populated, on a board that spins while the parts land on it,
ending on a slow light rake across the real metal. v1 stays the baseline; every v2 output is named
`*_v2`, so neither overwrites the other.

```powershell
.\animate_v2.ps1 -PlanOnly                  # schedule + diagnostics, no board import
.\animate_v2.ps1 -Frames probe -Samples 32  # storyboard beats -> ../../../out/showoff/anim/probe_v2/
.\animate_v2.ps1 -Draft                     # 960x540 preview + MP4
.\animate_v2.ps1                            # 2560x1440, 128 samples, ~4-5 h
```

**`-Draft` and the final write to the same `../../../out/showoff/anim/purple_v2/`** (deleted after delivery; it is recreated by a run) — clear it between runs or the
encode mixes resolutions.

**Reach for `-PlanOnly` first.** It evaluates the schedule, the board's move and the camera
without importing anything, and prints what a table cannot show: peak angular rates, which face is
towards the camera through fabrication, floor clearance, whether the finale fits in frame, and
where each part sits on the frames it appears and lands — which the build then repeats from the
real silhouettes. Seconds, not minutes: retime there rather than by rendering.

**Then `tools/camera_flow.py`** (`blender --background --python tools\camera_flow.py`), which
answers a different question: `-PlanOnly` says the camera's numbers are sane, this says what
the move *looks like*. It projects board points through the real camera and differences them,
reporting screen motion, its rate of change, and direction reversals — the last being what a
viewer reads as a cut, and what a C2 spline will happily contain. Run it after any camera edit.

The fabrication is the board's own layer data: pcb2blender's material exposes eight per-layer
float sockets fed from the rasterised Gerbers, and v2 rewires them through animated chains.
`tools/probe_sheet.py` tiles a probe directory into one labelled contact sheet.

## Colour variants

Handled at export time, so `PCB_new.kicad_pcb` is never modified — its own stackup colour
is left alone. `render.ps1 -Variants red,purple,blue` uses the named presets; anything
else takes `--mask-color "#RRGGBB"` on `export_pcb3d.py`.

To re-shade without re-exporting — faster, and safe while the board is open in KiCad — patch
the archive's stackup directly:

```powershell
& $kicadPython tools\recolor_pcb3d.py out\scene\pcb_red.pcb3d out\scene\pcb_deep.pcb3d --mask "#A81F16"
```

## Gotchas

- **`--pcb-material 3D` crashes Blender 4.4** (`EXCEPTION_ACCESS_VIOLATION` during import,
  at default texture DPI). `RASTERIZED` is the default and is what all of these use.
- **Texture DPI above the default buys nothing at 4K.** The board spans ~3570 px in a
  3840-wide frame, already ~2× oversampled; raising it mostly costs import time. Only the
  cropped `detail` shot benefits.
- **`--factory-startup` alone will not load the add-on** — user extensions are skipped.
  `blender_scene.py` enables it explicitly; keep that if you copy the script.
- **Save the board before exporting.** The exporter reads the file on disk, so unsaved
  KiCad edits silently render the previous state. Reading is safe while KiCad is open;
  nothing here ever writes to the board.
- **DNP footprints don't render**, because the export runs `--no-dnp` to match upstream.
  On this board that hides the M3 screws and tooling holes, which is what you want for a
  bare-board shot — but it means DNP is the first thing to check if a part is missing.
- **A "slow frame" is usually OptiX compiling kernels, not a slow render.** Early animation
  frames took 3½ minutes each and later ones 2 s. Cycles recompiles when the set of *visible*
  materials changes, and an assembly animation changes it constantly until every part has
  landed. The cache is per Blender version, so an upgrade pays it again. Time a frame from the
  middle of a sequence, never the start.
- **Identify an imported part by its mesh name, never its object name.** Blender truncates a
  name to make room for a `.001` suffix, and *replaces* a trailing numeric-looking one, so a
  second `IND-SMD_L6.0-W6.0-H4.5` becomes `IND-SMD_L6.0-W6.0-H4.001`. Instances share one mesh
  datablock, which keeps the filename intact.
- **Give `dump_components.py` the same `--swap-model` arguments as the export.** It describes
  what was *exported*; a dump naming the board's own model fails the designator join outright,
  which is the correct failure — an animation that cannot name the ADC should not render.
- **A stale scratch directory can silently drop a part.** Upstream reuses one fixed temp directory
  and its cleanup gives up quietly when files are locked, so leftovers get zipped into the next
  `.pcb3d`. Not cosmetic: an export against a polluted one was missing `R25` and carried a `USB_C`
  model no footprint references. The current code exports into a fresh directory. **Check the
  instance count the render prints against the one `dump_components.py` counts** — derived
  independently, so a mismatch is a stale archive. Never hardcode that number: it tracks the board,
  and has been 112, 106 and 111 at different revisions.
