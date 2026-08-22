# Asset plan (rev 6, 18 slides — the problem stated first at GATE 4, user's call: real community evidence)

Diagrams explain, words stay in the speaker notes. Sources: **drawn** = inline SVG
authored in the master; **repo** = a real file from this repository, typeset or shown;
**found** = Lucide icons (ISC license, embedded as SVG — the only third-party imagery);
**user** = supplied by you in `presentation/assets/`; **generated** = made by Claude where
nothing better exists. Everything embeds; nothing is fetched at render time.

| # | slide (short) | main visual | source |
|---|---|---|---|
| 1 | work must travel | your finished work at centre; reader, room and viewer it must reach | drawn + found icons |
| 2 | THE PROBLEM | two r/ClaudeCode posts, whole and labelled — "unreadable jargon" (140 up) and "word salad" (316 up); what people actually complain about is legibility, not correctness | **user** (screenshots of public posts) |
| 3 | four deliverables | map: four skills → four deliverables; natural-voice drawn as the audio companion under both films | drawn |
| 4 | the shared gate shape | universal pipeline: interview → posted checklist → gates, a you-approve loop on every gate; the source audit highlighted as the first gate everywhere | drawn |
| 5 | technical-report | its pipeline as a gate diagram: evidence map → skeleton → sections → cold read; cold reader shown testing the verdict playback | drawn |
| 6 | EXAMPLE: report | chat mock: you type "write up this project as a report" → Claude posts the real checklist and first interview questions (verbatim from the skill's own plan) | drawn (content per SKILL.md) |
| 7 | slide-deck | its pipeline: source → storyline → scripts → build → cold pass; the flip test drawn as headlines-only column that still reads | drawn |
| 8 | EXAMPLE: this deck, at the start | **the entire editor window**, uncropped: this repository in the tree, the run in the chat panel, one sentence typed and six gates back with nothing ticked | **user** (screenshot, whole) |
| 9 | EXAMPLE: the same run, mid-flight | the same window later: GATE 0 and 1 ticked and naming their files, GATE 2 marked *here*, 3–5 open | **user** (screenshot, whole) |
| 10 | EXAMPLE: the same run, delivered | the same window at the end: six ticks, the deck, export and tools by path, and the two notes recording what went wrong | **user** (screenshot, whole) |
| 11 | PROOF: explainer film | title card + stats (4:30 · 8 scenes · 55 lines · 1080p30) + **[YT-EDU-LINK]** + QR placeholder | user frame (optional) / generated title card |
| 12 | education-video | pipeline document → script → audio → picture with AUDIO FIRST highlighted; locked-waveform-owns-captions-and-cuts timeline underneath; natural-voice badge on the audio stage | drawn |
| 13 | EXAMPLE: explainer | chat mock: "make an explainer video" → the artifact trail you approve (script w/ traces, soundtrack, image manifest) ending in one prompt → Claude Design → HTML page → your render | drawn + found icons |
| 14 | PROOF: assembly film | title card + stats (84 s · 2560×1440 · approved on draft 3, first viewing) + **[YT-SHOWOFF-LINK]** + QR placeholder | user frame (optional) / generated title card |
| 15 | showoff-render | pipeline CAD readiness → stills → motion → drafts → frozen final; the 8 CAD checks as a tick-strip; camera-freeze padlock with "421 frames" caption | drawn (content per SKILL.md) |
| 16 | EXAMPLE: showoff | chat mock: "make the board look amazing" → freeze commit, colour stills side by side, measured-cost bar (guess 10.5 h vs measured 16.1 h), draft you watch | drawn; cost bar generated from the numbers |
| 17 | one sentence to start | terminal mock, two steps: install once (copy this repo's path, ask Claude to install into your project) → then one sentence, the checklist appearing; notes carry the house rules (skills read-only; your files live in your project) | drawn |
| 18 | takeaway | typographic slide, the takeaway verbatim | drawn |

## Where the trimmed content went (nothing was lost silently)

- Deck mode (spoken/read): dropped from the deck entirely, per your direction.
- Source-first: the highlighted first gate in every pipeline diagram (slides 4–5, 7, 12, 15).
- Flip test: slide 7's diagram; cold reader: slide 5's diagram.
- natural-voice and the two discarded soundtracks: slide 12 badge + speaker notes.
- 421 voided frames, measured 16.1 h vs guessed 10.5 h, humans-catch-the-faults: slides
  15–16 diagrams and notes, slide 14 notes.
- Read-only skills, files-never-next-to-the-skill: slide 17 speaker notes.
- Act IV (no-overclaiming, human-bench) removed whole at the user's direction during
  GATE 3; both themes already ride in the notes of slides 5, 12 and 16 and in the pipeline
  diagrams' verify loops — no dedicated slides.

## What only you can supply (all optional except the last)

- `assets/explainer-frame.png`, `assets/assembly-frame.png` — a frame you like from each
  film (slides 11, 14); otherwise I generate title cards.
- ~~The two YouTube URLs~~ — **landed during GATE 4**: education
  `youtube.com/watch?v=mXi9sxOSgwc`, showoff `youtube.com/watch?v=5jy-V41uGpI`; QR codes
  generated from them and embedded on slides 11, 14.

## The screenshots (landed at GATE 4, 2026-08-19)

Slides 8, 9 and 10 are one triptych: the same run at the start, mid-flight, and closed. Six
files in `assets/` — three untouched captures, all 3839×~2087, and three legible crops that
an earlier revision used and this one does not.

| slide | file embedded | shown at | its own text lands at |
|---|---|---|---|
| 8 | `deck-run-original.png` (whole) | 1306px, 0.34× | ~13px |
| 9 | `deck-run-gate2-original.png` (whole) | 1306px, 0.34× | ~13px |
| 10 | `deck-run-gate5-original.png` (whole) | 1306px, 0.34× | ~13px |

**These four slides deliberately break the GATE 0 28px floor**, at the user's explicit
direction: *"include the entire png, I wanna show them the entire work environment."* The
trade was stated before it was made. What the audience gets is the shape of real work in a
real tool — file tree, tabs, chat panel, status bar — not text they can read from a seat. The
content of each screen is carried by the speaker's notes; a viewer who opens the PPTX or the
PDF and zooms gets the text. **No tool here enforces this either way**: `render_check.py`
measures computed DOM font-size and is blind to text baked into a bitmap, so a 1080p canvas
will happily render an unreadable capture and report OK.

The legible crops from rev 4 are kept — `slide7-checklist-gate0.png` (1240px, 28.2px text)
and `slide8-checklist-gate2.png` (1700px, 39px text) — so the call can be reversed in one
edit. Crop boxes are recorded in `SLIDE-SCRIPTS.md`.

**Three things are on screen that a kinder crop would have hidden**, all left in on purpose:
the stale "26 slides, inside the agreed 25–28" on slide 8; a user message on slide 8 opening
"I insist on editing the skills", which is this repository's own override phrase for its
read-only rule and sits nine slides from the house rule on slide 17; and slide 9's capture
describing the deck as "16 slides" when it is now 17. All three were true when captured. A
screenshot that is retouched to agree with the present is not evidence any more, so none of
them were touched — the notes carry the corrections instead.

Images are inlined as data: URIs by `tools/build.py`, which resolves `__ASSET:name.png__`
placeholders out of this directory — same mechanism as the fonts, and it fails the build on a
missing file. The master is now 3.0 MB and still fetches nothing at render time.

## Licence and attribution

Lucide icons: ISC, free for commercial use, licence kept in source
(github.com/lucide-icons/lucide).

**Third-party content, slide 2.** Two screenshots of public posts on r/ClaudeCode, quoted as
published criticism: "Opus 5 - unreadable jargon" (u/Beautiful_Cap8938, 140 up, 90 comments)
and "Going back to 4.8 due to Opus 5 word salad?" (u/player__piano, 316 up, 238 comments).
Reddit's interface and subreddit icon are visible in both. Nothing is retouched, no vote count
or username altered, no watermark removed, and the source is labelled on the slide itself. If
this deck is published rather than presented, check whether that is the attribution you want
to stand behind — quoting named individuals to a room is a different act from putting them on
the open web.

**Requested and absent.** Two further images for slide 2 — a press-compacting-pages
illustration and an "AI Slop Explained" banner — were asked for and could not be included: no
file was saved, and both are third-party artwork of unknown provenance. Source or replace
before use.

Every other visual is authored for this deck or owned by you.
