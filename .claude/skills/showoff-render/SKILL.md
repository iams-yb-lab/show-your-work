---
name: showoff-render
description: Use when the user wants a showoff / hero / cinematic 3D render video or animation of hardware — a PCB, an assembly, a product, a mechanism. Triggers on "epic dramatic 3D render", "assembly animation", "showoff video", "render a video of the board", "make it look amazing", "cinematic render". Start here before opening Blender or any DCC tool.
---

# Showoff render — the 3D film

This works. `assembly_purple_v2.mp4` — 84 s, 2520 frames, 2560×1440 — came out of it, clean on
every check, approved on the first viewing of the third draft. It took twelve stages and three
drafts to get there and most of the cost was avoidable. This is the route without the cost.

The full arc, with numbers and citations, is in `video/showoff/assembly/RENDER-LOG.md`. Read it if you
want the evidence for any rule below.

---

## GATE 0 — CAD readiness. Do not pass this gate.

**Nothing renders until every box is ticked. Not a draft, not a probe frame, not a test import.**

If a model is missing, wrong, or incomplete, **STOP and tell the user.** Ask them to supply the
real CAD. Do not model it yourself, do not substitute something that looks close, do not
"just get something in there for now" and fix it later. Every one of those costs a re-render of
everything downstream, and on this project one improvised stand-in reached the finished film.

| # | check | how to check it | why |
|---|---|---|---|
| 1 | Every part that appears on camera has a real 3D model **present on disk** | open the file, do not trust the reference | Rules were written for a Teensy model that was never in the repo. Nobody noticed until committed stills failed to reproduce by mean \|Δ\| 0.030 |
| 2 | No model lives behind a gitignored path | `git check-ignore` every model path | The board's own U1 model sits at a `*.step` path `.gitignore` excludes. A missing CAD input here is invisible to `git status` |
| 3 | Every model is **complete as an assembly input** | check each part's z against the board face | The vendor Teensy has no headers of its own and floated until a 0.1 inch standoff was generated for it |
| 4 | Model colours checked against **photographs**, not against the model | eyeball a real photo of the part | The Harting body ships near-white (real ones are beige) and, as the largest object in frame, took over every shot. The Phoenix ships pale mint — right hue, wrong saturation. Both were faithful to their STEP colours and both were wrong |
| 5 | Instance count derived independently and compared | count from the board, count from the export, compare | It has been 112, 106 and 111 across three revisions. Never hardcode it. A polluted scratch directory once dropped `R25` from the export silently |
| 6 | DNP parts accounted for | they do not render | On this board that hides the M3 screws and tooling holes. First thing to check when a part is missing from a frame |
| 7 | The source CAD revision is **frozen** for the duration | agree it with the user, note the commit | A board change landed from the other machine mid-render and left the animation four parts behind the board |
| 8 | Any swap or generated part is done **now**, named, with provenance | a swap script, not an inline hack | And give the swap to the designator dump too — a dump naming the board's own model fails the join, which is the correct failure and caught this before a three-hour render |

**If the user asks you to start rendering with gaps here, say what is missing and what it will
cost.** Rendering into a known-bad input is the single most expensive mistake available.

---

## Then, in order

**1. Stills before motion.** Four shots, every colour variant under consideration, at final
quality. Pick the colour here — it is a lighting and contrast decision, not a taste one, and
picking it later invalidates everything. Calibrate exposure to a *measured* number per variant;
the rig that exposes a dark board correctly is a stop hot on a light one.

**2. Design the motion in tables, not code.** Every timing, position and beat in a table at the
top of the script. Retiming then means editing a table. Parts move by their *delta* transform, so
landed = delta 0 and the last frame reconstructs the import exactly.

**3. Plan-only pass.** Schedule and geometry with no rendering. Confirm the order is strictly
accumulated — a group physically cannot start before the one in front lands.

**4. Probe frames.** A handful of frames at final quality, at the moments you are least sure
about. Cost the full render from these, measured. A guess was 10.5 h; the measurement said 16.1 h.

**5. Draft render, low resolution — and WATCH IT.** Non-negotiable. See below.

**6. Fix, re-draft, watch again.** Repeat until a viewing surfaces nothing.

**7. Freeze the camera. Then render final.** Any camera edit voids every frame already rendered —
the scene is deterministic, so an edited script splices two animations together. 421 finished
1440p frames were thrown away exactly this way. When draft 3 was approved, the camera tables were
byte-identical to draft 2's, so the journey the user approved was the journey that shipped.

---

## The checks, and what each one cannot see

Four different questions. None of them is "is it good".

| check | answers | blind to |
|---|---|---|
| plan-only | is the schedule ordered and the geometry sane | anything about the image |
| camera flow | is the *move* coherent — reversals, momentum, speed range | anything about the image |
| frame differencing | one-frame discontinuities in frames that exist | sustained faults, and anything that is not a pop |
| entrances/landings table | is each part clear of frame when it appears | whether it looks right |

🔴 **Every fault that mattered was found by a human watching.** The parts-off-the-board draft, the
mask film popping into mid-frame, the trimmers appearing at the frame edge, the occluded connector
— all of them passed the automated checks and were caught by eye.

🔴 **A check that cannot fail is not a check.** A draft shipped with every part off the board while
the verification reported `|Δ| = 0.0`, because it compared each part's basis against a copy of
*itself* taken after the operation. Ask of every check: what input makes this fail?

🔴 **A low score means "not this fault", not "fine".** The frame differencer ranked terminal blocks
popping in at the frame edge as ordinary sustained motion. They were a real fault. Tools bound what
they measure, not what is wrong.

---

## What draft 1 got wrong, and why draft 3 was right

**Draft 1** shipped with every part off the board, and its camera read as several shots stitched
together despite being C2-continuous in every channel. Continuity in the tables is not a claim
about the shot: what a viewer integrates is camera azimuth *minus* the subject's own rotation, and
that difference reversed six times — the 180-degree rule broken mid-take. Authoring the camera in
the subject's frame directly, monotone, took reversals 13 → 0 and screen-speed range 900:1 → 24:1.

**Draft 2** had six faults no table could see: a board-sized film popped in at full opacity because
a visibility step and an alpha key landed on the same frame; 17 of 110 parts were on screen the
frame they became visible; the biggest part on the board landed off-screen because the subject
track had never named it; the heroes swooped in continuously instead of hovering and descending.

**Draft 3** fixed all of it *without touching the camera*, and was approved. Three lessons carried:
solve entry distance against a part's eight projected bounding-box corners, never against its
centre point — 1.08 half-widths is 5 mm of margin for a part whose own half-width is 11 mm.
Name every hero in the subject track; a camera cannot present a part it was never pointed at.
And a hover at the flight height happens above the top of the frame — hover height is its own number.

---

## Standing traps

- **Point smoke tests at a throwaway output directory.** A draft at the default once overwrote a
  finished 4K still with a 960×540 one. Draft and final writing to the same directory mixes
  resolutions into one encode.
- **Imported CAD arrives with no usable materials.** Expect every shape to come in as one generic
  plastic — metal shells, gold pads, screws, lenses, all of it. Restyle by scoped object-name
  rules, and remember name matching is substring: a rule keyed on a module's name repainted every
  solder joint on that part.
- **Identify material slots by what they measurably are, never by index or name.** Slot order is
  not stable between two imports of the same file.
- **Identify parts by mesh name, not object name.** Object names get truncated and numeric
  suffixes replaced; instances share one mesh datablock, which keeps the name intact.
- **Re-parent the container, not its children.** A component's basis is in the un-centred frame;
  re-parenting one while keeping its basis moves it half a board.
- **A light that rides with the subject must be normalised to its own distance.** Reusing a
  studio distance for a strip 42 mm away over-lit it 27×, and it read as a material bug for a while.
- **Close-ups are macro and depth of field is physical.** Compute the stop from the formula per
  beat; at 46 mm width f/7.1 gives about 1 mm of depth and everything else is a bokeh blob.
- **A stand-in model constrains the script.** The film's finale shows a deliberate stand-in for the
  real module, so the narration says "the controller" rather than naming the part. That is the
  correct handling — but decide it at GATE 0, not while writing narration.

---

## Audio

Do not start it here. The picture ships silent and the audio is muxed with the video stream copied,
so it can be re-cut any number of times without re-encoding a frame. When you get there, the
`natural-voice` skill is not optional — this project threw away two complete soundtracks by
skipping it.
