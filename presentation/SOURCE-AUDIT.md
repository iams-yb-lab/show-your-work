# Source audit — GATE 1

Audited 2026-08-18 against the GATE 0 source list. Every deck claim must trace to a line in
one of these files; anything they don't support stays out.

## The files and their evidence status

| source | status | what the deck may take from it |
|---|---|---|
| `README.md` | repo map, current | the five skills and what each covers; skills load by opening a session here; `install_skills.py` for elsewhere; the read-only rule; check_links verification |
| `.claude/skills/technical-report/SKILL.md` | **specified** (method distilled from a produced report that lives with its project, not here) | order: evidence → skeleton → sections → cold read; 6 gates; delivers evidence map + report + cold-read record |
| `.claude/skills/slide-deck/SKILL.md` | **specified — no produced deck behind it**; states this itself | order: source → storyline → slide scripts → build → cold pass; 6 gates; delivers storyline + scripts + master + cold-pass record. The deck must carry this caveat where it leans on the skill — and this deck is itself the skill's first evidence |
| `.claude/skills/education-video/SKILL.md` | **specified + produced evidence** (its reference film: 9 scenes, 49 lines — numbers live with that film, elsewhere) | order: document → script → audio → picture; 6 gates; delivers source doc + script + audio master + image manifest + one Claude Design prompt; Claude Design draws the picture, rendering is ours; natural-voice mandatory at audio |
| `.claude/skills/showoff-render/SKILL.md` | **specified + produced evidence** (`assembly_purple_v2.mp4`: 84 s, 2520 frames, 2560×1440, approved on first viewing of draft 3; full arc in `video/showoff/assembly/RENDER-LOG.md`) | order: interview → CAD readiness → stills → motion → drafts → final; ships silent; measured costs (guess 10.5 h vs measured 16.1 h); 421 frames voided by a camera edit; every fault that mattered found by a human watching |
| The two published films on YouTube — `https://www.youtube.com/watch?v=mXi9sxOSgwc` (education) and `https://www.youtube.com/watch?v=5jy-V41uGpI` (showoff) | **produced and published — the strongest evidence**; URLs supplied by the user during GATE 4 and embedded (text + QR) on slides 11, 14 and 18 | the deck may point at the films themselves as proof each workflow delivers; placeholders ride on the two proof slides until the URLs land |
| `video/education/how-to-make-an-explainer/` | **produced evidence, in this repo** | 4:30.3 · 8 scenes · 55 lines · 893 words · 1920×1080 30 fps; the full artifact trail stage by stage (BRIEF → SOURCE/NUMBERS → script → audio tools → MANIFEST → DESIGN-PROMPT → picture → RENDER-LOG); "what is not checked: how it sounds" — approved by ear |
| Three screenshots of this deck's own run, supplied by the user 2026-08-19 (`presentation/assets/deck-run-original.png`, `deck-run-gate2-original.png`, `deck-run-gate5-original.png`) | **produced evidence of the run itself** — added at GATE 4, after this audit; unretouched captures, crops only, nothing composited or retyped | the same run at three moments: posted with all gates open, two gates in, and closed with six ticks and every artifact named. Shown whole and uncropped at the user's direction, so what they may **not** be taken for is *current*: the "26 slides / agreed 25–28" on the second and the "16 slides" on the third were true when captured and are stale now. Corrections are spoken in the notes; the pixels stay untouched |

| Two public r/ClaudeCode posts, screenshotted by the user 2026-08-19 (`presentation/assets/reddit-unreadable-jargon.png`, `reddit-word-salad.png`) | **published third-party criticism**, unretouched, attributed on the slide; added at GATE 4 after this audit | that people find raw model output unreadable — "unreadable jargon", "word salad", "impenetrable" — at 140 and 316 upvotes. **The hard limit:** neither post is about a generated *report* or *deck*. They may not be used to claim that AI-written documents are slop; slide 2's headline is written to claim only legibility, and must not be upgraded in the room |

## Readiness checks

- **Evidence status before claims** — yes: each skill states what it was distilled from;
  slide-deck states its own lack of a produced deck; the explainer README opens on its numbers.
- **Every number has one home** — yes: explainer numbers in its README/NUMBERS.md; showoff
  numbers in its SKILL.md citing RENDER-LOG.md. The deck links each number to that home.
- **Estimates labelled** — the one guess in the sources (10.5 h) is explicitly labelled a guess
  beside its measurement (16.1 h); that contrast is usable as-is.
- **Namesakes — two hazards found, naming rule set:**
  1. *Two explainer films.* education-video's reference film (9 scenes, 49 lines, lives
     elsewhere) is **not** `how-to-make-an-explainer` (8 scenes, 55 lines, lives here). The
     deck uses only the second, named "the how-to-make-an-explainer film", and never blends
     their numbers.
  2. *"GATE n" means a different thing in every skill.* The deck never says a bare "GATE 3";
     gates are always qualified by skill, or discussed as the shared pattern.
- **Mechanism is causal** — yes: each skill states why its order holds (re-recording is the
  expensive half; a camera edit voids finished frames; prose before structure rebuilds).
- **Scope limits explicit** — yes, and the deck inherits them: skills are read-only; films
  never accumulate in the tooling repo; Claude Design draws education-video's picture; the
  human bench outranks measurement; `~/.claude/skills/` install refused.
- **Verdict** — the deck ends on the GATE 0 takeaway, not a comparison verdict; the source
  needs no losers' reasons.

## Ruling

The source is ready. No document fix required before GATE 2.

## Amendment — GATE 4, 2026-08-19

Three sources landed after this audit closed: the user's screenshots in the row above. They
are evidence *of the run*, not about the subject, so they change no claim already traced
here — they replace one drawn recreation on slide 7 with the screen it was recreating, and
add slides 9 and 10, carrying the same run to delivery. Audited on the same terms as everything else: what they show, and what they
may not be made to say.

## Second amendment — GATE 4, 2026-08-19

A fourth source landed: two public Reddit posts, now slide 2. Unlike the run screenshots, this
is third-party material about a *third party's* experience, and it is the only claim in the
deck that rests on evidence the deck does not own. It was audited on its own terms and its
headline was written down to fit the evidence rather than up to fit the intended point — the
posts complain about legibility, so the slide claims legibility. Two further images requested
for that slide were not included: no file, and unknown provenance. Recorded in ASSETS.md.
