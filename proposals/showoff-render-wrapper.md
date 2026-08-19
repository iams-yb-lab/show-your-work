# Proposal: give `showoff-render` the wrapper `education-video` already has

**Status: APPLIED 2026-08-17.** The user authorized the edit with the exact phrase; the rewrite
below is now live in `.claude/skills/showoff-render/SKILL.md`, hashes re-blessed, divergence from
the source repository recorded in `EXPORT-MANIFEST.md`. This document remains as the rationale.

## Why

`showoff-render` today is a field manual: the strongest single gate in the repo (CAD readiness),
four checks with an honest blind-to column, and every rule priced by a real failure. What it does
not have is a run protocol. It never asks what the film is for, never posts a plan, never names
the stage a message belongs to, never says who ends a stage, and never asks where the film's files
go — the exact gap `CLAUDE.md` warns about. Ask for a showoff render today and Claude improvises
the conversation around good rules, differently every time.

`education-video` has the wrapper: interview → posted checklist → named gates → user-owned
approvals → costed rollbacks. This proposal ports the wrapper, not the content.

## What is deliberately NOT copied

The two are different products, and the deepest difference is a straight inversion of authority:
**education-video is audio-first** — the narration master is the timing authority and the picture
is cut to it; **showoff-render is picture-first** — the visuals are the product, the picture ships
silent, and audio is an addon muxed onto a frozen picture, or never made at all. The wrapper
crosses; the axis of authority must not. Concretely, three of education-video's load-bearing ideas
stay behind:

- **No Claude Design handoff.** In education-video the picture is outsourced and the final
  deliverable is a prompt. Here Claude *is* the picture department; the final deliverable is the
  rendered master itself. No GATE-5-as-prompt.
- **Audio is not the timing authority — the motion tables are.** No gate waits on a soundtrack,
  no scene is timed against one, and "audio later, or never?" is a single interview question, not
  a stage. The existing four-line audio footer stays a footer.
- **The expensive half is different.** Education-video guards the script hardest because
  re-recording is the expensive half. Here the expensive half is the final render — 421 finished
  1440p frames were thrown away to one camera edit — so the gate guarded hardest is the camera
  freeze, and rollback costs are stated in render-hours, not re-record sessions.

## The mapping

| today | proposed | what changes |
|---|---|---|
| — | GATE 0 — the interview | new; includes the where-do-files-go question `CLAUDE.md` requires |
| GATE 0 CAD readiness | GATE 1 — CAD readiness | table word-for-word; "do not model it yourself" becomes a ladder — search online hard first, compromises (Claude models it, or converts unusable CAD, à la Red Pitaya) only on the user's request; closes with user sign-off on the frozen revision |
| step 1 stills | GATE 2 — the stills | same work; closes on a contact sheet path and the colour question |
| steps 2–4 tables / plan-only / probes | GATE 3 — the motion, priced | same work, one gate; user approves the *measured* cost before any draft renders |
| steps 5–6 draft, watch, fix | GATE 4 — the draft loop | watching becomes a formal approval, not advice; checks table lives here |
| step 7 freeze + final | GATE 5 — the freeze and the final | camera tables byte-identical to the approved draft, render once |
| checks / draft-lessons / traps / audio | unchanged | evidence sections stay word-for-word |

One genuinely new deliverable: a **render log** kept with the film (what rendered, from which CAD
commit, at what settings, what each viewing found) — this is what `video/showoff/assembly/RENDER-LOG.md`
already is; the proposal just makes keeping one a rule instead of a habit.

---

## Proposed replacement text for `.claude/skills/showoff-render/SKILL.md`

Frontmatter unchanged. Sections marked *(verbatim)* carry today's text word-for-word.

```markdown
# Showoff render — the 3D film

This works. `assembly_purple_v2.mp4` — 84 s, 2520 frames, 2560×1440 — came out of it, clean on
every check, approved on the first viewing of the third draft. It took twelve stages and three
drafts to get there and most of the cost was avoidable. This is the route without the cost.

The full arc, with numbers and citations, is in `video/showoff/assembly/RENDER-LOG.md`. Read it if
you want the evidence for any rule below.

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

The picture ships silent. Audio, if it ever happens, is muxed later with the video stream copied —
see the audio note at the end.

## How this runs — the plan first, then one gate at a time

**Before anything else, post the plan as an unticked checklist and ask to begin** — no reading, no
tool, no work; it is the first thing the user sees.

    - [ ] GATE 0  the interview — where the files go, what the film is for, what freezes
    - [ ] GATE 1  CAD readiness — every box ticked, revision frozen
    - [ ] GATE 2  the stills — colour and exposure decided at final quality
    - [ ] GATE 3  the motion — tables, plan-only pass, probe frames, measured cost
    - [ ] GATE 4  the draft loop — render small, watch, fix, repeat until a viewing surfaces nothing
    - [ ] GATE 5  the freeze and the final — camera untouched, rendered once

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

*(the existing eight-row table verbatim)*

**When a model is missing, wrong, or incomplete, work the ladder — in this order, never skipping
a rung:**

1. **Search first, and try hard.** The manufacturer's own site, the distributors, the CAD
   libraries (GrabCAD, SnapEDA, UltraLibrarian, vendor KiCad/Altium libraries). Show the user
   every candidate found: where it came from, what it contains, what it is missing. Most parts
   that matter on camera have a real model somewhere — the job is to find it, not to fake it.
2. **If the search comes up dry, say so and stop.** Present the compromises as options, priced:
   Claude modelling the part from drawings, or converting CAD that exists but is in a format
   Blender cannot import into one it can (the way the Red Pitaya model was made). **These happen
   only
   when the user asks for them — never as a silent default.** An improvised stand-in once reached
   the finished film because nobody was asked.
3. **Whatever is found, made or converted goes back through the table.** And into row 8: a named
   swap with provenance, done now, at this gate — a stand-in decided here shapes the script
   honestly; one improvised mid-render is a lie the narration has to work around.

Close by showing the ticked table, naming where each model came from, naming the frozen commit,
and asking the user to confirm the freeze. The freeze is their agreement, not your note.

## GATE 2 — the stills. Colour before motion.

*(existing step 1 verbatim: four shots, every colour variant under consideration, at final
quality; colour is a lighting and contrast decision; exposure calibrated to a measured number per
variant)*

Close with the contact sheet by absolute path and one question: which variant. Picking it later
invalidates everything after this line.

## GATE 3 — the motion, priced before it renders.

*(existing steps 2–4 verbatim: motion designed in tables, not code; parts move by delta transform;
plan-only pass confirming strictly accumulated order; probe frames at final quality at the moments
of least confidence)*

Cost the full render **from the probes, measured**. A guess was 10.5 h; the measurement said
16.1 h. Close with the tables, the plan-only result and the measured cost, and ask before a single
draft frame renders — the user is approving hours against the budget they gave at GATE 0.

## GATE 4 — the draft loop. Render small, then watch.

*(existing steps 5–6 verbatim, plus: point drafts at a throwaway output directory)*

Run the four checks, then watch the draft end to end yourself, then hand it to the user **by
absolute path** and ask them to watch it — not to skim it, to watch it. Fix what the viewings
surface, re-draft, repeat. The gate ends when a full viewing surfaces nothing and the user says
so.

*(the existing "The checks, and what each one cannot see" section verbatim: the four-check table
and the three 🔴 lessons)*

## GATE 5 — freeze the camera. Then render final.

*(existing step 7 verbatim)*

The camera tables must be **byte-identical** to the approved draft's — diff them, do not trust
memory. Render once, at final resolution, to the film's directory. Close with the master by
absolute path, the updated render log beside it, and one question: done?

## What draft 1 got wrong, and why draft 3 was right

*(verbatim)*

## Standing traps

*(verbatim)*

## Audio

*(verbatim)*
```

## Open questions for the user

1. Education-video's interview lives in its own file (`interview.md`). This proposal inlines the
   showoff interview because it is seven questions, not a protocol with forbidden questions. Split
   it out only if it grows.
2. "Done?" at GATE 5 vs. a formal delivery list — education-video ends on a handoff artifact;
   showoff ends on the master itself. Kept minimal here on purpose.
3. The render-log-as-deliverable rule is the one genuinely new obligation. It codifies what the
   reference film already did; strike it if that feels like scope creep.
