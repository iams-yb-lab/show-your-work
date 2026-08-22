---
name: showoff-render
description: Use when the user wants a showoff / hero / cinematic 3D render video or animation of hardware — a PCB, an assembly, a product, a mechanism. Triggers on "epic dramatic 3D render", "assembly animation", "showoff video", "render a video of the board", "make it look amazing", "cinematic render". Start here before opening Blender or any DCC tool.
---

# Showoff render — the 3D film

This works. `assembly_purple_v2.mp4` — 84 s, 2520 frames, 2560×1440 — came out of it, clean on
every check, approved on the first viewing of the third draft. It took twelve stages and three
drafts to get there and most of the cost was avoidable. This is the route without the cost.

The full arc, with numbers and citations, is in `showoff-render/examples/assembly/RENDER-LOG.md`. Read it if you
want the evidence for any rule below.

This film is the visuals. **The picture is the product and it ships silent**; audio, if it ever
happens, is an addon muxed onto a frozen picture — see the note at the end. The timing authority
is the motion tables, never a soundtrack.

## Never edit a skill. The exact words, or not at all.

**This file and every other skill are read-only.** Not a wording tweak, not one more bullet, not
"while I was in there". A skill travels between repositories, so a session that quietly improves
one changes how every future session works, everywhere, unreviewed.

**The only exception is the user typing `I insist on editing the skills`** — exactly, not a
paraphrase and not a typo. Anything short of it, *including* a direct "put this in the skill",
means: say you are not going to, write the request down where the current work lives, and keep
following the skill as written.

## You deliver five things, and none of them is a guess

**Every showoff-render task ends with exactly these, in this order:** the **stills** — every
colour variant at final quality, the colour decided on them (GATE 2); the **motion design** —
timing tables, a clean plan-only pass, and a render cost measured from probe frames (GATE 3); the
**drafts** — low resolution, each one watched end to end (GATE 4); the **final master** — camera
frozen, rendered once, silent, mux-ready (GATE 5); and the **render log**, kept with the film:
what rendered, from which CAD commit, at what settings, and what each viewing found.

## How this runs — the plan first, then one gate at a time

**Before anything else, post the plan as an unticked checklist and ask to begin** — no reading, no
tool, no work; it is the first thing the user sees.

```
- [ ] GATE 0  the interview — where the files go, what the film is for, what freezes
- [ ] GATE 1  CAD readiness — every box ticked, revision frozen
- [ ] GATE 2  the stills — colour and exposure decided at final quality
- [ ] GATE 3  the motion — tables, plan-only pass, probe frames, measured cost
- [ ] GATE 4  the draft loop — render small, watch, fix, repeat until a viewing surfaces nothing
- [ ] GATE 5  the freeze and the final — camera untouched, rendered once
```

Then ask **"Ready to begin?"** and wait for the answer.

**Every message opens by naming the gate** — `GATE 3 of 5 — the motion.` The user must never have
to work out where in the process they are.

**A gate ends when the user says it is good, never when you decide it is.** Show the gate's
output, say precisely what needs judging, stop. Do not begin the next gate in the same message, do
not render ahead while waiting, and never read silence as approval. **The one that gets skipped
here is the watching: the user watches every draft**, because on the reference film every fault
that mattered was found by a human watching and none by a check.

**A change that lands on an already-approved gate stops the run.** When new direction arrives — a
CAD revision, a different colour, a camera idea — name the earlier gate it invalidates, say what
rebuilding costs **in render-hours, measured, not guessed**, and ask whether to go back. A camera
edit after GATE 5 opens voids every finished frame; 421 finished 1440p frames went exactly that
way once.

**Tick the box and repost the checklist** as each gate is approved, so progress is visible without
scrolling back.

**Close a gate with what to look at and one question. Nothing else.** Name the artifact **by
absolute path**, name what needs judging, stop. No findings list, no summary of what is in the
file, no account of what you fixed on the way. The single exception is GATE 0, which closes by
playing the answers back as bullets.

## GATE 0 — the interview. Ask before opening any tool.

Ask in two or three short windows, not one wall. **An unanswered question is a question, not a
default** — never open GATE 1 on an assumption.

- **Where do the film's files go?** Never next to the skill, never defaulted. Every still, draft,
  master and log lands there.
- **What is being shown, and where is the CAD?** Paths and formats; which revision; whether that
  revision may be **frozen** for the duration, and at which commit.
- **What is the film for, and where will it play?** That decides resolution, aspect ratio, frame
  rate and target length — get numbers, not adjectives.
- **What are the hero beats?** The parts or moments the film exists to show, by name. A camera
  cannot present a part it was never pointed at.
- **What should it look like?** Colour direction, register, any brand constraint — and ask for
  **photographs of the real hardware**, because STEP colours lie: the near-white Harting was
  faithful to its file and wrong.
- **What may it cost?** Which machine renders, how many wall-clock hours are acceptable, any
  deadline. The measured estimate at GATE 3 is judged against this answer.
- **Audio later, or never?** The picture ships silent either way; the answer only decides whether
  a mux is planned.

Close by playing the answers back as bullets and asking to open GATE 1.

## GATE 1 — CAD readiness. Do not pass this gate.

**Nothing renders until every box is ticked. Not a draft, not a probe frame, not a test import.**

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

**When a model is missing, wrong, or incomplete, work the ladder — in this order, never skipping
a rung:**

1. **Search first, and try hard.** The manufacturer's own site, the distributors, the CAD
   libraries (GrabCAD, SnapEDA, UltraLibrarian, vendor KiCad/Altium libraries). Show the user
   every candidate found: where it came from, what it contains, what it is missing. Most parts
   that matter on camera have a real model somewhere — the job is to find it, not to fake it.
2. **If the search comes up dry, say so and stop.** Present the compromises as options, priced:
   modelling the part from drawings, or converting CAD that exists but is in a format Blender
   cannot import into one it can. **These happen only when the user asks for them — never as a
   silent default.** An improvised stand-in once reached the finished film because nobody was
   asked.
3. **Whatever is found, made or converted goes back through the table.** And into row 8: a named
   swap with provenance, done now, at this gate — a stand-in decided here shapes the script
   honestly; one improvised mid-render is a lie the narration has to work around.

**If the user asks you to start rendering with gaps here, say what is missing and what it will
cost.** Rendering into a known-bad input is the single most expensive mistake available.

Close by showing the ticked table, naming where each model came from, naming the frozen commit,
and asking the user to confirm the freeze. The freeze is their agreement, not your note.

## GATE 2 — the stills. Colour before motion.

Four shots, every colour variant under consideration, at final quality. Pick the colour here — it
is a lighting and contrast decision, not a taste one, and picking it later invalidates everything.
Calibrate exposure to a *measured* number per variant; the rig that exposes a dark board correctly
is a stop hot on a light one.

Close with the variants side by side, by absolute path, and one question: which one.

## GATE 3 — the motion, priced before it renders.

**Design the motion in tables, not code.** Every timing, position and beat in a table at the top
of the script. Retiming then means editing a table. Parts move by their *delta* transform, so
landed = delta 0 and the last frame reconstructs the import exactly.

**Plan-only pass.** Schedule and geometry with no rendering. Confirm the order is strictly
accumulated — a group physically cannot start before the one in front lands.

**Probe frames.** A handful of frames at final quality, at the moments you are least sure about.
Cost the full render from these, measured. A guess was 10.5 h; the measurement said 16.1 h.

Close with the tables, the plan-only result and the measured cost, and ask before a single draft
frame renders — the user is approving hours against the budget they gave at GATE 0.

## GATE 4 — the draft loop. Render small, then watch.

**Draft render, low resolution — and WATCH IT.** Non-negotiable. Point drafts at a throwaway
output directory (see the standing traps). Run the four checks, watch the draft end to end
yourself, then hand it to the user **by absolute path** and ask them to watch it — not to skim
it, to watch it. Fix what the viewings surface, re-draft, watch again. The gate ends when a full
viewing surfaces nothing and the user says so.

### The checks, and what each one cannot see

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

## GATE 5 — freeze the camera. Then render final.

Any camera edit voids every frame already rendered — the scene is deterministic, so an edited
script splices two animations together. 421 finished 1440p frames were thrown away exactly this
way. When draft 3 was approved, the camera tables were byte-identical to draft 2's, so the journey
the user approved was the journey that shipped.

The camera tables must be **byte-identical** to the approved draft's — diff them, do not trust
memory. Render once, at final resolution, to the film's directory. Close with the master by
absolute path, the updated render log beside it, and one question: done?

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
  correct handling — but decide it at GATE 1, not while writing narration.

## Audio

Do not start it here. The picture ships silent and the audio is muxed with the video stream copied,
so it can be re-cut any number of times without re-encoding a frame. When you get there, the
`natural-voice` skill is not optional — this project threw away two complete soundtracks by
skipping it.
