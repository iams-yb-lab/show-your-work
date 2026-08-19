# GATE 0 answers — how-to-use-the-skills deck

Interviewed 2026-08-18. These answers are the deck's contract; GATES 1–5 check against them.

## Home
`c:\ai_video_generation_skills\presentation\` — storyline, slide scripts, HTML master,
exports, cross-check tool and cold-pass record all land here. Never next to the skills.

## Mode
**Talk deck — spoken over.** Sparse slides; the meaning lives in the speaker notes.

## Speaker
The repo owner (the user). Notes are written in their voice. GATE 5's timing pass is
measured on them reading one act aloud; the measured pace gets written down here.

## Audience
Newcomers to this repo: colleagues/collaborators who have Claude Code but have never used
these skills.

**May be assumed to know:** engineering practice; what Claude Code is and how to type a
prompt at it; what a report, a slide deck, and a video are.

**Must be taught:** that the four output skills exist and what each one produces; the gate
system (posted checklist, user-owned approvals); source-first (the document under the
deck/video comes before any visuals); the interview (each skill starts by asking, including
where the files go); that the skills are read-only; that the bench — human ears and eyes —
outranks every measurement.

## The one takeaway
> "Name the output, answer the interview, and the gates carry you to a delivered report,
> deck, or video."

Lands as the final headline. GATE 5's cold viewer is judged against it.

## Length and slide budget
~15+ minutes spoken. **Agreed budget: revised at GATE 2 to 16–18 slides** (user's call:
quality over count — diagrams explain, words stay in the speaker notes; the deck's mode is
spoken-over and is never itself mentioned on a slide). Each skill gets an example slide:
the literal prompt you'd type and what Claude returns.

## Screen, aspect, font floor
16:9, authored on a 1920×1080 canvas, played from the HTML master full screen.
**Agreed font-size floor: 28px on the 1080p canvas** (≈21pt). GATE 4 checks nothing
renders below it and nothing overflows a slide.

## Export
**PowerPoint, pixel-faithful kind:** each slide as an image, with the real speaker-notes
text in the PowerPoint notes field. Not hand-editable — an edit lands in the HTML master
and the export is regenerated, never patched.

## Source material and evidence status
- `README.md` — the repo map.
- `.claude/skills/technical-report/SKILL.md`, `.claude/skills/slide-deck/SKILL.md`,
  `.claude/skills/education-video/SKILL.md`, `.claude/skills/showoff-render/SKILL.md`
  — the specification of each process. Status: **specified** (they describe method, not
  measurements).
- `video/education/how-to-make-an-explainer/` — the worked example behind
  education-video. Status: **produced evidence** (a delivered film with its logs).
- The slide-deck skill states it was not distilled from a produced deck; where the deck
  leans on it, the deck says so. (This deck is itself that skill's first evidence.)
- **The two published films on YouTube** — the strongest evidence: one link for the
  education video, one for the showoff render. Status: **produced and published**; URLs
  arrive at the very end of the run. Placeholders in every artifact until then:
  `[YT-EDU-LINK]`, `[YT-SHOWOFF-LINK]`.

Nothing outside these files may be claimed.

## Brand / visual style
No mandated assets. **Light mode — bright and light**, style chosen by Claude: a clean,
airy palette on a light ground, embedded system-safe fonts, restrained accent colour.
Committed at GATE 4; no dark-mode variant.

**Style reference (added during GATE 3, user's direction):** the intro film's picture —
`video/education/intro/picture/Temperature Controller Intro.html` — "really love how it
has many diagrams and the style itself". Extracted tokens the deck builds on: cream paper
`#F5F3EE`, teal accent `#0F766E`, purple secondaries `#6D4AC0`/`#4C3391`, Instrument Sans
for text, JetBrains Mono for numbers; diagram-first composition.

**Diagram-heavy (added during GATE 2):** the deck is mainly about convenient proven
workflows, so most slides carry an embedded diagram — pipelines, gate maps, timelines —
drawn as inline SVG in the master. Asset plan lives in `ASSETS.md`; user-gathered images
land in `presentation/assets/`.

## GATE 5 measured pace
Rehearsed end to end aloud by the speaker, 2026-08-19: **well within the ~15-minute
budget** (speaker's own report; per-act seconds not recorded). A future re-pricing after
edits should re-time one act rather than reuse this.
