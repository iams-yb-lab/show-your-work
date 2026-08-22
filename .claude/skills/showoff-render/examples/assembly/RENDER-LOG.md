# Render log

Self-contained handoff for the PCB render work. This plus `README.md` is everything.

## Next up

**The 1440p final landed** 2026-08-12 14:02 — `../../out/showoff/anim/assembly_purple_v2.mp4`, 2520 frames,
`frame_pops.py` clean over all of them (`../../out/showoff/anim/FINAL-REPORT.txt`). The picture is finished and
approved. Length and phases: [`README.md`](README.md).

1. **The soundtrack landed too** — v7.2, approved 2026-08-12, after ten rejected narration attempts.
   The record is in [`AUDIO-LOG.md`](audio/AUDIO-LOG.md) and [`VOICE-LOG.md`](audio/VOICE-LOG.md);
   the method that finally worked is [`../../natural-voice/README.md`](../../../natural-voice/method/README.md).
   **Load the `natural-voice` skill before touching any voice work.**
2. **Four checks, different questions:** `-PlanOnly` schedule and geometry, `camera_flow.py` the
   *move*, `frame_pops.py` one-frame discontinuities in the frames that came out (0 over the
   final's 2520), and the **entrances-and-landings table the build prints** from the real
   silhouettes. None sees anything *smoothly* wrong, and a low `frame_pops` score means "not a
   pop", not "fine" — see *Things that cost time*.
3. **Drafts and v1 are parked** in `../../out/showoff/anim/_superseded/`, with a README saying what each is —
   moved there session 57. 🔴 **`assembly_purple.mp4` (v1) cannot be re-rendered**: its pipeline
   targets a board revision this repo has moved past, so that MP4 is the only copy. **Every frame
   sequence was deleted 2026-08-13** — both films were decode-verified first, and the MP4s are the
   films now. Re-rendering the final costs 16.1 h. Any camera edit voids every rendered frame —
   deterministic scene, so an edited script splices two animations.

**Purple is the chosen colour**, its four stills committed in `gallery/`; red and green rendered
locally only. Purple has the best trace contrast and part separation — red's traces don't read, and
green loses its boundaries because mask, Phoenix blocks and Teensy compete. Reproduce all 12 with
`picture/render.ps1 -Variants red,purple,green -SkipExport`: 24 min on a 4070 Laptop, 9 on a 4080 SUPER.
`../../out/showoff/` is gitignored — only `gallery/` is tracked. **Point smoke tests at a throwaway `-OutDir`:**
a draft at the default once overwrote a finished 4K still with a 960×540 one.

## State as of 2026-08-10

Working end to end, both stills and animation, unattended from `PCB_new.kicad_pcb`.

- **Stills:** red, purple and green, four shots each (`slide`, `cinematic`, `showcase`, `demo`),
  3840×2160, 256 samples, in `../../out/showoff/stills/`; scenes saved as `../../out/showoff/scene/pcb_<variant>.blend`. Four
  purple ones are committed in `gallery/`, ~33 MB. **Dropped:** black and blue — black hides the
  copper, which defeats the point of the shots.
- **Animation:** v1 and v2 — lengths and phases in [`README.md`](README.md), not repeated here.
  For either, the tables at the top of the script are the whole design: retiming means editing
  those, not the code. v1's narration: [`narration-assembly.md`](script/narration-assembly.md).
- **Two machines, both verified.** Laptop: KiCad 10.0.4 and Blender 4.4.3 in Program Files.
  Desktop (RTX 4080 SUPER): KiCad 10.0.5 and Blender 4.5.10 LTS portable under `C:\tools`, no
  installer and no administrator rights — how, and why it works, is in [`README.md`](README.md).
- **Blender 4.5.10 renders identically to 4.4.3** — mean |Δ| 0.0024, i.e. sampling noise. The
  desktop's 5.2.0 (MCP bridge) sits deliberately outside `find-tools.ps1`'s `blender-5.*` glob:
  under it, renders silently switch to a Blender that cannot import a board. Why they cannot be
  one install is under *Things that cost time*; shots are in [`README.md`](README.md).

## The Teensy, and why the gallery did not reproduce

Re-rendering `purple_showcase` missed the committed `gallery/purple_showcase.png` by mean |Δ|
0.030 on the board, surviving every control — both Blender versions, the pre-removal board
revision, the best whole-image shift — so neither framing nor the renderer. **It was the Teensy,
and the tell was in this directory all along:** `blender_scene.py` documents its mask as linear
(0, 0.497, 0) while `gen_teensy41.py`'s output — dimensionally right, visually plain — is
(0.055, 0.32, 0.14), and regenerating gave a file bit-identical to the committed `.wrl`. So
generator and model agreed and both disagreed with the stills. **A comment can be the evidence.**
The model the rules were written for is a vendor Teensy 3.6 assembly reading exactly (0, 0.497, 0),
now in `kicad-libs/teensy.3dshapes/`; rendering it is a *swap*, not a board edit.
[`picture/tools/model-swaps.ps1`](picture/tools/model-swaps.ps1) is dot-sourced by both entry points so stills and
animations cannot disagree, and carries the provenance, transform and why a 3.6 stands in for a
4.1. Two things cost real time: KiCad's STEP → VRML **fragments it into 4157 shapes** (light
geometry, but ~20 min and 5 GB per import — `merge_wrl_shapes.py` flattens it per material,
applying the transform stack, since two sub-assemblies carry real rotations), and **it has no
headers**, so it floated until `gen_teensy_headers.py` emitted the 0.1 inch standoff (two strips,
48 posts) with every dimension imported from `gen_teensy41.py`.

## Open

1. `--pcb-material 3D` crashes Blender 4.4 (`EXCEPTION_ACCESS_VIOLATION` during import). The
   importer caps retries at < 5.1, so only a 4.5.x retry is open; `RASTERIZED` looks fine.
2. Cosmetic log noise: `id_us_min` on a `NTMAT4CAD_*` tree, and `Failed to remove ... PIL`.
3. The sweep strip peaks at `e` 0.97 where the table authors 0.90 and 0.70: a natural cubic rings
   after a short steep segment. Left alone — that is what the first draft already looked like.

## Things that cost time, so they don't cost it twice

The ones that generalise past this board are now the `showoff-render` skill, which front-loads them
as a CAD-readiness gate. **Start there for a new film**; this section is the evidence behind it.

- **A C2 camera spline is not a claim about the shot.** The first v2 camera was continuous in
  position, velocity and acceleration everywhere and still read as several shots stitched together,
  because what a viewer integrates is the camera's azimuth **minus the board's yaw** — the world
  frame holds only the lights — and that difference reversed six times: the 180-degree rule broken
  mid-take. `mix` made it easy to get wrong by splitting the shot across two smooth channels whose
  *difference* nobody watched; `orb` authors it directly, monotone. `picture/tools/camera_flow.py` found all
  of it: momentum change 95 → 3.9, speed range 900:1 → 24:1, reversals 13 → 0.
- **Then a mask film popped into mid-frame and both checks passed anyway**, because neither
  looks at the rendered frames — and the student found it by watching. `picture/tools/frame_pops.py`
  differences the frames that came out. **But a low score there means "not a one-frame pop", not
  "fine":** it ranked the trimmers and terminal blocks popping in at the frame edge as ordinary
  sustained motion, and they are a real fault. Tools bound what they measure, not what is wrong.
- **An entry distance solved for a point is not solved for a part.** 1.08 half-widths is 5 mm of
  margin for a screw terminal whose own half-width is 11 mm, and for the sectors pointing into
  foreground or background it buys **no vertical clearance at all** — 100 mm towards the camera is
  below the frame bottom at nearly zero horizontal offset. 17 of 110 parts were on screen the frame
  they appeared. `entry_basis` now grows the distance until all eight projected box corners clear
  one frame edge: ×1.55 at worst, peak part speed 1.24 → 1.45 frame-widths/s, and printed per part.
- **A hover at the flight height happens above the top of the frame.** Heroes fly in 22–40 mm up to
  clear what is already down, and a hero frame is 47–76 mm tall, so holding that height put the ADC
  at v 1.21 and the Teensy at 2.05 — out of shot, then dropping in from above. `hover_at` is a
  separate lower height, reached over the approach. The bulge and the arc had to move onto the
  approach's own clock too, or the part hovers *beside* its pads — at u = 0.62 the bulge is still
  52 % of its peak.
- **The camera could not present the Harting, and the fix was not in the camera.** 75 mm off
  centre, 94 mm long, landing into a 135 mm frame with the aim on the damped swarm centroid: its
  centre sat 1.12 frame-widths off screen. The path was fine — the **subject track had never named
  the part**. Naming it buys an excursion out and back, i.e. a reversal in the aim's own travel,
  so it was spent deliberately and measured: 0 reversals still, and its two handoffs (3.8 s, 4.0 s)
  land in the same flow band as the hero traverses. `SUBJECT_AIM` carries why the aim goes *short*
  of the connector and why the −16 mm nudge is 16 and not 20 — at 20 the aim turns 121° at f1478.
- **Do not aim a shot at `board_facing` ≈ 0.** The mask films were timed to touch at dead edge-on,
  the one attitude in which both read as arriving from opposite sides at once — and also the one
  in which the board is a bright line one pixel wide with nothing to land on. Probe frames caught
  it; a plan table cannot, because −0.07 reads as a fine number.
- **The Teensy's micro-USB shell rendered like crumpled foil for three separate reasons**, and
  only the first was diagnosed as such — so fixing one at a time looked like no progress. All
  three are fixed. 1. KiCad writes a `creaseAngle` into the VRML and Blender's importer turns it
  into custom split normals with **every** polygon flagged smooth, so genuinely sharp bends get
  shaded across; chunky plastic survives that and thin sheet metal does not. `fix_imported_normals`
  clears them and re-derives sharpness at 30°, on the 13 meshes that came through STEP. 2. The
  shell was **plastic**, not metal — next entry. 3. `make_metal` deleted the Material Output
  node, so it rendered pure black whatever its BSDF said — two entries down.
- **pcb2blender's `enhance_materials` gave every shape on every component
  `MAT4CAD_plastic-custom_*-semi_matte`.** It could not infer a material family from the VRML,
  so the USB shell, the gold pads, the header pins, the trimpot screws and the terminal block
  screws were all plastic. `COMPONENT_RULES` in `blender_scene.py` restyles them and carries the
  two colour corrections below. Three things about that table:
  - rules are **scoped by object name**, because a colour test alone is ambiguous board-wide:
    the neutral light grey that means "screw cage" on the terminal block is white plastic on
    the Teensy, and the brass of a trimpot screw is also an LED lens.
  - for the metal rules, apart from the Teensy's shell, they **keep the model's colour** and
    change only the shading model, since "this should be metal" is a claim about the shader.
  - the name match is a **substring**, which reaches further than you expect: generated
    solder fillets are named after their footprint, so the rule keyed on "Teensy" repainted
    every joint on the part with the USB shell's nickel. `SOLDER_*` is now skipped outright —
    the importer gives those a purpose-built material already.
- **Two model colours were wrong for the parts we fitted**, both large in frame, both decided
  against photographs rather than from the model: the Harting DIN 41612 body ships near-white and
  took over every shot (real ones are beige), and the Phoenix MKDS ships pale mint, right hue and
  wrong saturation. See `HARTING_BODY`, `HARTING_SHROUD`, `PHOENIX_GREEN`; the Harting needs
  `pale` before `neutral_light`, since they overlap and slots are consumed in order.
- **Blender RNA wrappers have no stable Python identity.** Two lookups of the same node can return
  different objects, so `if node is not keeper: tree.nodes.remove(node)` removes the keeper too.
  This deleted the Material Output and cost a four-way finish sweep whose tiles all came back
  identical — a material with no output is black. Go through node **names**, not references.
- **Material slot order is not stable between two imports of the same `.pcb3d`.** Slot 0 was
  `SHAPE_677` on one import and `SHAPE_1037` on the next. Identify slots by what they measurably
  are (area, height, colour), which is what `select_slots` does — never by index or `SHAPE_nnn`.
- **Use `object.shade_smooth_by_angle`, not `object.shade_auto_smooth`.** The latter adds a
  geometry-nodes modifier pulled from the essentials asset library, not a safe bet under
  `--factory-startup`; the former writes sharp-edge flags into the mesh. Both exist in 4.4.3.
- **Exposure is calibrated to a measured number, not by eye**, via `picture/tools/measure_exposure.py`.
  Mask albedo and light level have to move together: the rig that exposes black correctly is a
  stop hot on red, purple or green and washes the traces out — hence the per-variant `Light` in
  `$VariantSpec`. On the 4K finals, showcase 0.192 / 0.195 / 0.212 and cinematic 0.243 / 0.248 /
  0.257 for red / purple / green, all inside the 0.16–0.34 band with ≤0.01 % clipped — three
  variants within 0.02 of each other is the calibration working. **The band does not apply to
  `demo`**, which sits on a bright sweep and measures 0.54 by design.
- **`picture/tools/crop_tile.py` tiles the same crop from several renders into one image**, with
  `--shrink` to block-average 4K frames down to something viewable. Judging a 20 mm connector
  inside a 170 mm board means looking at ~3 % of the frame.
- **pcb2blender parents every component and solder joint to the PCB object, and that object is
  what centres the board.** A component's own basis is in the un-centred mesh frame
  (58.6, −43.8) mm and only the board's transform puts it at (−22.9, 6.2), so re-parenting one
  onto a rig while keeping its basis moves it half a board — the v2 draft shipped once with every
  part outside the outline. Parent the *board* to the rig and leave its children alone. **And
  check it board-relative:** the check this passed at `|Δ| = 0.0` compared each part's basis with
  a copy of *itself* taken after re-parenting. A check that cannot fail is not a check; `on_board`
  and the outline guard replaced it.
- **A light that rides with the board must be normalised to its own distance.**
  `build_lighting`'s `(d / 0.2) ** 2` makes irradiance depend on the base watts alone, so reusing
  the studio's `d` for v2's sweep strip 42 mm off the board over-lit it by (220/42)² = 27×. That
  came back as white components and blown silkscreen, and read as a *material* bug for a while.
- **Hero close-ups are macro, and Blender's depth of field is physical.** It is
  2·N·c·(1+m)/m² with m = 36/width, so at width 46 mm f/7.1 gives about 1 mm — every landed part
  20 mm from the ADC became a bokeh blob. Pick the stop from that formula, per beat, and let
  `frame_coverage()` size the field: an eyeballed one is not trustworthy at 3.4 board-lengths.
- **The importer and the MCP add-on cannot share a Blender.** `pcb3d_importer` is
  `blender_version_max = "5.1.0"` *exclusive* and Blender Lab's `mcp` add-on is
  `blender_version_min = "5.1.0"` — disjoint, with 5.1 itself satisfying neither. The bridge can
  still open a saved `.blend` for geometry and framing, but every pcb2blender material arrives as
  `NodeUndefined`, so it says nothing about the look. Renders stay on 4.5.10.
- **Don't pass `--backdrop`** to `blender_scene.py` from `render.ps1`. Each shot carries its own
  (`slide` transparent, `demo` a bright sweep, rest dark) and passing one overrides all of them —
  that bug shipped a `slide` with a background in it.
- The rest live in [`README.md`](README.md#gotchas), which is where they belong: the KiCad 10
  exporter patches and the `PAD_DRILL_SHAPE` renumber; saving the board before exporting, and
  re-colouring without one; a "slow frame" being OptiX compiling kernels; identifying a part by
  its **mesh** name; a stale scratch directory silently dropping one, and checking the instance
  count rather than quoting it; and designators coming from the board, not the scene.
