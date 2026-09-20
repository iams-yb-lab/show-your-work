---
name: showoff-render
description: Use when the user wants a showcase or cinematic 3D render video or animation of hardware — a PCB, an assembly, a product, a mechanism. Triggers on "epic dramatic 3D render", "assembly animation", "showoff video", "render a video of the board", "make it look amazing", "cinematic render". Start here before opening Blender or any DCC tool.
---

# Showoff render — process notes

Notes from a finished film: an 84 s, 2520-frame, 2560×1440 assembly animation that passed every
check and was approved on the first viewing of its third draft. Getting there took three drafts and
most of the cost was avoidable. The full record, with numbers, is in
`showoff-render/examples/assembly/RENDER-LOG.md`.

The picture is the product and it ships silent. Sound, if wanted later, is muxed onto a frozen
picture with the video stream copied. The timing authority is the motion tables, never a soundtrack.

This file is a toolbox, not a procedure to recite. What the film shows and how it should look are
the user's decisions; follow the project's style guide if it has one, and ask if it does not.

## What to settle first

Read the project first; ask only what it leaves open, in plain prose.

- **Where the film's files go.** Every still, draft, master and log lands there, never beside this
  skill.
- **What is being shown and where the CAD is**: paths, formats, revision; and whether that
  revision can be frozen for the duration, at which commit.
- **What the film is for and where it will play**, which fixes resolution, aspect ratio, frame rate
  and target length as numbers.
- **Which parts or moments the film exists to show**, by name. A camera cannot present a part it was
  never pointed at.
- **What it should look like**: colour direction, any brand constraint, and photographs of the real
  hardware. STEP colours are often wrong; a near-white connector that was faithful to its file was
  beige in reality.
- **What it may cost**: which machine renders, acceptable wall-clock hours, deadline. The measured
  estimate from probe frames is judged against this.
- **Whether audio is planned later.** The picture ships silent either way.

Write the answers down with the film's files.

## CAD readiness — nothing renders before this is done

Not a draft, not a probe frame, not a test import.

| check | how | why it exists |
|---|---|---|
| every part on camera has a 3D model present on disk | open the file; do not trust the reference | rules were once written for a model that was never in the repository; nobody noticed until stills failed to reproduce |
| no model sits behind a gitignored path | `git check-ignore` every model path | a board's own model sat at a `*.step` path the ignore file excluded, invisible to `git status` |
| every model is complete as an assembly input | check each part's height against the board face | a vendor model without its headers floated until a standoff was generated |
| model colours checked against photographs | compare with a real photo of the part | the largest object in frame shipped near-white and took over every shot |
| instance count derived independently and compared | count from the board, count from the export | it varied 112, 106, 111 across revisions; a polluted scratch directory once dropped a part silently |
| do-not-place parts accounted for | they do not render | this hid screws and tooling holes; check it first when a part is missing |
| the CAD revision is frozen for the duration | agree it with the user; note the commit | a board change landed mid-render and left the animation four parts behind |
| any swap or generated part is done now, named, with provenance | a swap script, not an inline hack | a stand-in improvised mid-render is a fact the narration then has to work around |

When a model is missing, wrong or incomplete, in this order: search hard (the manufacturer, the
distributors, the CAD libraries) and show the user every candidate with its source and gaps; if the
search fails, say so and offer the options with their cost (model from drawings; convert a format
Blender cannot import) and do them only if asked; and put whatever is found or made back through the
table as a named swap. If the user asks to render with gaps, say what is missing and what it will
cost. Rendering into a known-bad input is the most expensive mistake available.

## Stills before motion

Four shots, every colour variant under consideration, at final quality. Pick the colour here; it is a
lighting and contrast decision, and picking it later invalidates everything after. Calibrate exposure
to a measured number per variant: the rig that exposes a dark board correctly is a stop too bright on
a light one. Show the variants side by side, by absolute path, and ask which.

## Motion, priced before it renders

- **Design the motion in tables, not code.** Every timing, position and beat in a table at the top of
  the script; retiming is then an edit to a table. Parts move by their delta transform, so a landed
  part is at delta zero and the last frame reconstructs the import exactly.
- **Plan-only pass**: schedule and geometry with no rendering. Confirm the order is strictly
  accumulated; a group cannot start before the one in front lands.
- **Probe frames**: a handful at final quality, at the moments you are least sure of. Cost the full
  render from these, measured. A guess was 10.5 h; the measurement said 16.1 h.
- Show the tables, the plan-only result and the measured cost before a single draft frame renders;
  the user is approving hours against the budget they gave.

## The draft loop

Render at low resolution to a throwaway directory. Run the checks, watch the draft end to end
yourself, then hand it to the user by absolute path and ask them to watch it end to end. Fix what the
viewings surface, re-draft, watch again, until a full viewing surfaces nothing.

| check | answers | cannot see |
|---|---|---|
| plan-only | is the schedule ordered and the geometry sane | anything about the image |
| camera flow | is the move coherent: reversals, momentum, speed range | anything about the image |
| frame differencing | one-frame discontinuities | sustained faults; anything that is not a pop |
| entrance and landing table | is each part clear of frame when it appears | whether it looks right |

Three facts from the reference film. Every fault that mattered was found by a person watching, none
by a check: parts off the board, a film popping in mid-frame, parts appearing at the frame edge, an
occluded connector all passed the checks. A check that cannot fail is not a check: a verification once
compared each part's basis against a copy of itself taken after the operation and reported zero error
on a draft with every part off the board; ask of every check what input makes it fail. A low score
means "not this fault", not "fine".

## Freeze the camera, then render once

Any camera edit invalidates every frame already rendered, because the scene is deterministic and an
edited script splices two animations. 421 finished 1440p frames were lost that way once. The camera
tables of the final must be byte-identical to the approved draft's; diff them. Render once, at final
resolution, into the film's directory, and update the render log beside it: what rendered, from
which CAD commit, at what settings, and what each viewing found.

## What the three drafts taught

- Draft 1: every part off the board, and a camera that read as several shots stitched together
  although it was continuous in every channel. What a viewer integrates is camera azimuth minus the
  subject's own rotation, and that difference reversed six times. Authoring the camera in the
  subject's frame, monotone, took reversals from 13 to 0 and screen-speed range from 900:1 to 24:1.
- Draft 2: six faults no table could see, among them a visibility step and an alpha key on the same
  frame, 17 of 110 parts on screen the frame they became visible, and the largest part landing
  off-screen because the subject track never named it.
- Draft 3 fixed all of it without touching the camera and was approved. Solve entry distance against a
  part's eight projected bounding-box corners, never its centre. Name every featured part in the
  subject track. A hover at flight height happens above the top of the frame; hover height is its
  own number.

## Standing traps

- Point smoke tests at a throwaway output directory; a draft once overwrote a finished 4K still.
- Imported CAD arrives with no usable materials; restyle by scoped object-name rules, remembering
  that name matching is substring.
- Identify material slots by what they measurably are, never by index or name; slot order is not
  stable between imports.
- Identify parts by mesh name, not object name; object names get truncated and renumbered.
- Re-parent the container, not its children; re-parenting a child while keeping its basis moves it
  half a board.
- A light that rides with the subject must be normalised to its own distance.
- Close-ups are macro and depth of field is physical; compute the stop per beat.
- A stand-in model constrains the narration; decide stand-ins at the CAD readiness table, not while
  writing.

## Audio

Not here. The picture ships silent; sound is muxed later with the video stream copied. When that
time comes, load the `natural-voice` skill before generating any speech.
