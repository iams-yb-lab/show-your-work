# Proposal: `slide-deck` GATE 4 — four mechanical checks, clearance not contact

**Status: PROPOSED, not applied.** `.claude/skills/**` is read-only; applying this needs the
user's exact phrase. Nothing under `.claude/` is touched by this branch, so
`tools/check_links.py` and every hash in `EXPORT-MANIFEST.md` are unchanged.

Raised from outside this repository: a 15-slide final-report talk built with `slide-deck` in the
`RedPitaya` project (IAMS Yb Lab), 2026-08-20/21. The deck itself stays in that project, per
`CLAUDE.md`. What travels here is the part that generalizes.

## Why

The skill's GATE 4 asks for two mechanical checks: nothing below the font floor, nothing
overflowing its slide. Both were built as instructed, both ran green, and the deck went to its
author — who found **six layout defects on his first look at a screen**:

| slide | what he said | what it was |
|---|---|---|
| 02 | "the phrase is on top of the vertical line" | a label crossing the marker it labelled |
| 03 | "why's the image on top of another one??" | a 1560-px diagram in a ~1130-px column, landing on the figure beside it |
| 04 | "add the word mixer to clearly represent this thing" | the concept the slide teaches, unlabelled on its own diagram |
| 04 | "too much DC? What does that even mean?" | a hand-wave on a teaching slide where the source had ±1 V |
| 05 | "3 demodulators? I think that might be an overclaim" | a number with no referent beside it |
| 06 | "lines are over the words, just look at it" | three labels crossed by strokes |

**Neither existing check could see any of them.** Every defect was full-size text, inside the
canvas. The two checks the skill names are the two that find almost nothing, because real defects
do not happen at the edges of the canvas or below the font floor — they happen between elements
that each sit legally where they were put.

Two more rounds followed, and the same reader rejected the deck twice more in the same words:
*"even if the words are not touching the box, they're way too close to the edge, you know what I
mean?"* That is the finding that changes the rule from **contact** to **clearance**.

## What this proposal adds

| today | proposed |
|---|---|
| two checks named in one sentence, "early, cheap, and never eyeballed" | **four** checks, numbered, with what each one is for — and an explicit note that the cheap two find almost nothing |
| — | **element collision**: no two figures/diagrams/cards/tiles overlap. Catches fixed-width artwork dropped into a narrower column |
| — | **clearance inside every diagram**: no stroke or block edge near a word, stated as clearance not contact, **per-axis**, with the straddling-vs-contained distinction that makes it usable, and stroke geometry walked point by point rather than bounding-boxed |
| — | **prove each check can fail** before trusting it — inject a defect, confirm the report, remove it |
| — | **then look at the pictures**: render every slide and read the images, every build, because the two passes catch different things |
| "exports are regenerated, never patched" | plus: **a second-implementation export gets its own mechanical check**, and a rebuild does not carry its fonts |
| — | **the build is one named command chain**, derived artifacts after what they derive from |
| — | **reusable tooling is run against the finished deck** before it is called done |
| GATE 3 verification list | plus: **diagrams are the default**, and the **asset list is a named GATE 3 output** — searched-and-found separated from still-needed |
| GATE 4 close | plus: say which checks ran and what they cover; never let green stand in for "this looks right" |

Reference implementations, with the tuning numbers and the negative test, are in
[`assets/slide-deck-gate4/`](assets/slide-deck-gate4/). They are evidence and a starting point,
not payload — `install_skills.py` does not copy `proposals/`.

## The evidence for the clearance rule, and its tuning

Tuning turned out to matter more than the idea:

| rule | findings on 15 slides | verdict |
|---|---|---|
| symmetric 12 px | **54** | unusable — nearly all were two-line labels in blocks that read perfectly well |
| per-axis: 12 px sideways / 3 px vertical inside a block, 8 px from a stroke | **8** | every one real |

The eight, after tuning — and the author had flagged only two of these slides:

```
s03: "−" crossed by a curve (needs 8px clearance)
s04: "a quarter-turn later" crossed by a rect edge (needs 12px sideways)
s07: "inside the chip" crossed by a rect edge (needs 12px sideways)
s07: "against one shared reference" crossed by a rect edge (needs 12px sideways)
s07: "against one shared reference" crossed by a curve (needs 8px clearance)
s08: "sine out → drives the EOM" crossed by a rect edge (needs 12px sideways)
s14: "demodulates → error out" crossed by a rect edge (needs 12px sideways)
s14: "drives the two actuators" crossed by a rect edge (needs 12px sideways)
```

Where the two passes disagreed, which is the argument for keeping both:

- the **checker** found two defects the eyes had passed over;
- the **eyes** found one the checker had passed over — a caption wrapped four lines deep in a
  200-px box: legal geometry, bad typography.

And one defect no check could have found: after a diagram was redesigned, the PowerPoint rebuild
still carried the **old** picture, because the SVG→PNG step had not been re-run. Nothing failed.
It just shipped a stale figure. Hence the named-command-chain paragraph.

## What is deliberately NOT in the text below

Three further requests came from the same author. They change what the skill *asks of the user*
rather than what it *verifies*, so they want a human decision rather than being folded in behind
one:

1. **Drop the "spoken over, or read alone?" interview question** and default to a talk deck — his
   answer never changes and the question costs a slot every run. Invasive: the skill branches on
   mode in GATES 0, 3 and 5, so this is its own proposal.
2. **Carry evidence status by tense and framing, not by negative clauses on slides** — no "not yet
   built", no "never tested". He was explicit that the honesty requirement is unchanged: the deck
   must never claim what it has not done; it just earns that by what it asserts ("next is", "the
   real prize", "estimated") rather than by apologising in parentheses. The safety exception stays
   (a genuine over-range warning is a negative sentence and should be). This touches a load-bearing
   honesty rule, so it should be weighed on its own.
3. The **diagram-first default and the asset list** — this one *is* in the text below, because it
   only sharpens an existing GATE 3 instruction rather than reversing one.

## Applying it

The block below is the complete proposed `SKILL.md`. It was produced by applying four edits to the
live file programmatically, not retyped, so everything outside the edits is byte-identical by
construction.

- current `.claude/skills/slide-deck/SKILL.md` — sha256[:16] **`1ecd48bc86bef336`** (matches
  `tools/skill-hashes.txt`)
- proposed text below — sha256[:16] **`6b0c277b92fcd76b`**

To apply, with the user's exact phrase: extract the fenced block programmatically, write it to
`.claude/skills/slide-deck/SKILL.md`, verify the new hash matches, re-bless
`tools/skill-hashes.txt`, record the divergence in `EXPORT-MANIFEST.md`, and run
`python tools/check_links.py`.

````markdown
---
name: slide-deck
description: Use when the user wants a slide deck — a presentation, talk slides, a pitch deck, or a reading deck that presents a project, a design, or findings to an audience. Start here BEFORE writing any outline or opening any design tool. Triggers on "slide deck", "presentation", "slides for a talk", "pitch deck", "make slides", "deck about this project", "present this to an audience".
---

# Slide deck — the argument on slides

The order is **source → storyline → slide scripts → build → cold pass**, and it is not
negotiable. Slides drawn before the storyline is approved get redrawn after every change of
story, and a deck built on an unaudited source asserts things nothing supports, at projector
size, to a room that will believe them.

Unlike its siblings, this skill was not distilled from a produced deck. The run protocol —
interview, posted checklist, named gates, user-owned approvals — is the family's, carried from
the skills that have evidence behind them; the slide craft is stated as method, not as
measurement. The first deck this skill produces is its first evidence: the GATE 0 answers and
the cold-pass record are its log, kept with the deck, where the user said the files go, never
next to the skill.

## Never edit a skill. The exact words, or not at all.

**This file and every other skill are read-only.** Not a wording tweak, not one more bullet, not
"while I was in there". A skill travels between repositories, so a session that quietly improves
one changes how every future session works, everywhere, unreviewed.

**The only exception is the user typing `I insist on editing the skills`** — exactly, not a
paraphrase and not a typo. Anything short of it, *including* a direct "put this in the skill",
means: say you are not going to, write the request down where the current work lives, and keep
following the skill as written.

## One deck, two modes — and everything branches on which

A deck is **spoken over** or it is **read alone**. A talk deck's slides are sparse because a
human carries the meaning, and its words live in the speaker notes; a reading deck's slides
carry the full meaning with nobody talking. GATE 0 asks which this is, the answer is written
down with the deck's files, and GATES 3 and 5 branch on it. A deck that tries to be both is a
talk deck that reads badly and a reading deck that presents worse — if the user needs both, that
is two GATE 0 answers and the second is planned as a variant, not smuggled into the first.

## You deliver four things

**Every slide-deck task ends with exactly these, in the order they are made:** the **storyline**
— one asserted headline per slide, reading top to bottom as the whole argument (GATE 2); the
**slide scripts** — per slide, what it shows and what it says, every claim traced to the source
(GATE 3); the **deck** — one self-contained HTML master plus the export the user chose, with the
mechanical cross-check beside them (GATE 4); and the **cold-pass record** — what a viewer with
no context played back and what changed because of it (GATE 5). All of it lives where the user
said at GATE 0, never next to the skill.

## How this runs — the plan first, then one gate at a time

**Before anything else, post the plan as an unticked checklist and ask to begin** — no reading,
no questions, no work; it is the first thing the user sees.

```
- [ ] GATE 0  the interview — mode, audience, takeaway, budget, export, home
- [ ] GATE 1  the source — audited, or written first
- [ ] GATE 2  the storyline — every headline, the whole argument
- [ ] GATE 3  the slide scripts — act by act, verified before shown
- [ ] GATE 4  the build — the HTML master, checked mechanically, then the export
- [ ] GATE 5  the cold pass — a viewer with no context, then the user's own pass
```

Then ask **"Ready to begin?"** and wait for the answer.

**Every message opens by naming the gate** — `GATE 3 of 5 — the slide scripts.` The user must
never have to work out where in the process they are.

**A gate ends when the user says it is good, never when you decide it is.** Show the gate's
output, say precisely what needs judging, stop. Do not begin the next gate in the same message,
do not work ahead while waiting, and never read silence as approval. **The one that gets skipped
here is the storyline: ask whether the argument is right before a single slide is written**,
because everything after it is built on the order of the argument — a storyline change after
GATE 3 opens re-cuts the acts, re-traces the claims, and strands slides the user already
approved.

**A change that lands on an already-approved gate stops the run.** When new direction arrives —
a different audience, a changed takeaway, new evidence, a mode switch — name the earlier gate it
invalidates, say what rebuilding costs (which approved acts it touches, which slides it
strands), and ask whether to go back. Reopening an approved artifact is the user's call, never
yours, and never something you do by quietly editing it.

**Tick the box and repost the checklist** as each gate is approved, so progress is visible
without scrolling back.

**Close a gate with what to look at and one question. Nothing else.** Name the artifact **by
absolute path**, name what needs judging, stop. No findings list, no summary of what is in the
file, no account of what you fixed on the way. The exceptions: GATE 0 closes by playing the
answers back as bullets, a GATE 1 close also names what was checked and its evidence status,
and a GATE 3 act close also reposts the storyline with finished acts ticked.

## GATE 0 — the interview. Ask before writing anything.

Ask in two or three short windows, not one wall. **An unanswered question is a question, not a
default** — never open GATE 1 on an assumption.

- **Where do the deck's files go?** Never next to the skill, never defaulted. The storyline, the
  scripts, the master, the exports and the cold-pass record all land there.
- **Spoken over, or read alone?** And if spoken: who speaks — the notes are written in that
  person's voice, and the timing pass at GATE 5 is measured on them.
- **Who is the audience?** Get the two lists: what this audience may be assumed to know, and
  what must be taught. Every slide is judged against them.
- **What is the one takeaway?** The sentence the audience should be able to repeat the next day.
  A deck with no takeaway is a tour. It becomes the final headline, and GATE 5's cold viewer is
  judged against it.
- **Where is the source material, and what is its evidence status?** Paths. What is measured,
  what is specified, what is only intended — noted now, checked at GATE 1.
- **How long?** Minutes for a talk, reading minutes for a reading deck. The slide budget is
  proposed from the answer and agreed here, never defaulted.
- **Where will it play, and what leaves the room?** The screen decides the aspect ratio and the
  font-size floor — propose the floor as a number from the screen and the room's back row,
  agree it with the user, and write the agreed number down; GATE 4 checks against it. If the
  deck is sent onward afterward, the reading path is decided now: for a talk deck that means
  agreeing the notes' vehicle — the PowerPoint notes text, or a notes page per slide in the
  PDF — as part of the export choice.
- **Which export?** The master is always one self-contained HTML file. PDF prints faithfully
  from it. PowerPoint is one of two honest kinds, chosen here: pixel-faithful slides as images
  with real notes text where notes exist, or a hand-editable rebuild — a second implementation,
  priced as one. Never promise an editable file that is "the same deck as" the HTML; it is not.
- **Any brand or template constraint?** Colours, fonts, logo, a mandated template — and ask for
  the real assets, not descriptions of them.

Write the answers down where the deck's files live — a resumed session cannot replay a chat, and
GATE 5 needs the audience description and the takeaway verbatim. Close by playing the answers
back as bullets and asking to open GATE 1.

## GATE 1 — the source. A deck is only as accurate as the document under it.

A vague, unaudited or half-finished source is a disqualifying problem, not a starting point.
The source is ready when it states its own evidence status before any claim; every number has
exactly one home; typicals, estimates and assumptions are labelled inline; namesake quantities
are disambiguated; mechanism is a causal chain, not an assertion of quality; the scope limits
are explicit; and — when the deck ends on a verdict — the source actually reaches one, with the
losers' reasons.

If any of that is missing, **stop and help the user fix the document first — that is the work.**
When the deck presents a project to readers outside it, the `technical-report` skill exists to
write exactly this document. Never write a storyline against a source you would not defend.

Close by naming the source, saying what was checked and what its evidence status is, and asking
to open GATE 2.

## GATE 2 — the storyline. The whole argument before any slide.

**One line per slide, and the line is the slide's headline, written as a full-sentence
assertion.** "Q3 revenue" is a label; "Q3 revenue doubled, on one customer" is a headline. A
slide is one claim — a headline holding an "and" is usually two slides.

- **The flip test, and it is the gate's own check:** read the headlines alone, top to bottom.
  They must carry the complete argument — someone who reads nothing else gets the takeaway. Run
  it before showing the storyline, and again after any headline changes, at every later gate.
- **A headline whose claim is not measured carries its status word already, here** — estimated,
  specified, assumed — because the headline's bytes are frozen from this gate on, and a status
  patched in later breaks them.
- **The storyline file is written to be parsed**: one headline per line, act names on their own
  lines and marked so the cross-check tool skips them. Ticks live in the reposted checklist,
  never in the file — the file's bytes are what the tool reads.
- **Open where the audience is standing, never on what goes wrong.** Slide one is their
  situation and what they want out of it; the shape of the whole thing comes before any detail.
  Costs, failures and war stories belong inside the act they belong to, and in the closing
  verdict.
- **No headline may rest on a concept a later slide teaches.** The two GATE 0 lists decide what
  needs teaching; a term the audience must be taught gets its slide before the first headline
  that spends it.
- **The takeaway lands as the final headline**, in words the GATE 0 answer would recognize.
- **The budget is honored here**, not discovered broken at GATE 4. Cutting a slide from a
  storyline costs a line; cutting it from a built deck costs the act around it.
- **Group the slides into acts** — GATE 3 proceeds act by act, and the acts are how progress is
  reported.

Close with the storyline by absolute path and one question: right argument, right order?

## GATE 3 — the slide scripts. Act by act, verified before shown.

**Draft one act, verify it, show it, stop.** Approval of one act opens the next. Never draft
ahead while waiting — a later act regularly discovers something an earlier one must say
differently; treat that like a stop-the-run: name the approved act it touches and ask before
editing it, never quietly.

Each slide's script carries four things:

- **The headline** — byte-identical to the storyline. A headline that needs to change is a
  storyline change: flag it, do not slip it.
- **What the slide shows** — precisely: a chart and which comparison it makes; a table and which
  columns at which operating points; an image, its source and its licence; a diagram and what
  shape it draws. **Every image is licensed and no watermark is ever removed.** Evidence that
  proves a different claim belongs on that claim's slide, not this one.
- **What it says** — talk mode: the speaker notes, in the speaker's own voice, in spoken
  register; reading mode: the slide's own prose, carrying the full meaning with nobody talking.
- **The trace** — each claim's line in the source, written with the slide, so the verification
  below has something to point at.

**Write in this register:**

- **The body proves the headline and nothing else.** A chart shows exactly the comparison its
  headline makes; comparisons use identical columns at identical operating points.
- **Numbers trace home.** Every number on a slide traces to its line in the source; rounding is
  the only transform allowed, never beyond the source's stated precision, never a number the
  source does not carry.
- **Claims wear their status inline** — measured, specified, estimated, assumed — on the slide,
  not in the notes; a room cannot hear a footnote. The headline's own status word has been there
  since GATE 2 — never patch it in here.
- **Terms are taught at first use, one metaphor per concept, forever.** The source's own
  vocabulary and images are the deck's; never two metaphors for one thing, never one for two.
- **Talk slides stay sparse.** The audience reads the slide or listens to the speaker, not both;
  what is on the slide is what they can take in at a glance, and the sentences live in the
  notes. Namesakes get their distinct names at every appearance.

**Verify before the user sees it — every act, every time:** every number against the source
(value, unit, status, home); every slide's evidence actually proving its own headline; every
term taught before any headline spends it; every trace pointing where it says; the flip test
still passing.

**Diagrams are the default and images are the exception.** A drawn diagram of structure beats a
photograph for most of what a technical deck must explain and never waits on someone finding a
file. When an image genuinely is needed, search for it — the project's own files first — before
asking the user for anything, and close the act with **the asset list as a named output**: what
was found, with paths, separated from what is still missing and what each missing one must show.
The user should only ever be asked for what could not be found.

Close each act with its location and one question, and repost the storyline with finished acts
ticked, so progress is visible inside the gate.

## GATE 4 — the build. The HTML master, checked mechanically.

**The master is one self-contained HTML file**: every slide on the same fixed canvas at the
GATE 0 aspect ratio, fonts and images embedded, no external requests, and it plays from a
double-click. Headlines land byte-identical to the approved scripts. Every chart is generated
from the numbers it plots, never drawn to look right.

**The mechanical checks are four, not two, and the cheap two find almost nothing.** Build all
four early, run them on every build, and never eyeball what they cover:

1. **Font floor** — nothing renders below the GATE 0 floor. Text inside a scaled diagram is
   measured at its *scaled* size, because that is what the room sees.
2. **Slide overflow** — nothing renders outside the canvas.
3. **Element collision** — no two figures, diagrams, cards or tiles overlap each other. This is
   what catches fixed-width artwork dropped into a narrower column, which lands silently on
   whatever sits beside it.
4. **Clearance inside every diagram** — no line, curve or shape edge comes near a word. State
   this as *clearance, not contact*: "not touching" still reads as cramped, and a reader will
   say so. Margins are per-axis, because the two directions are not the same problem — a
   two-line label in a short block is normal, a label almost against a side edge is the defect
   the eye catches first. A label fully inside its own block is correct; one straddling that
   block's edge is not. For strokes, walk the geometry point by point — a diagonal line's
   bounding box covers half a diagram.

**Prove each check can fail before trusting it.** Inject a deliberate defect into a scratch copy,
confirm the check reports it, remove the injection. A check that has only ever passed is not
evidence, and reporting its green result as "the slides are sound" is a false claim about work
you have not done.

**Then look at the pictures.** Render every slide to an image and read the images, every build.
The checks and a pair of eyes catch different things: a checker finds crossings and collisions a
reader skims past, and a reader finds what is legal but ugly — a caption wrapped four lines deep
in a narrow box, a photograph left in portrait on a landscape slide when it could simply have
been rotated. Neither pass replaces the other, and a green check is not a reviewed slide.

**A talk deck's speaker notes live in the master**, each marked as a note, and the master
renders without them — the notes-free rendering is what the room sees, what every export
derives from, and what GATE 5's cold viewer gets.

**Build the cross-check tool early — it is cheap.** It parses the headlines and the slide count
out of the HTML master and out of the storyline file, and exits non-zero on any difference,
because the two are written independently and editing one while forgetting the other must
surface here, not on the projector. Never eyeball that agreement.

**Exports derive from the master and are regenerated, never patched.** PDF prints from it.
PowerPoint is whichever kind GATE 0 agreed. An edit lands in the master and the exports are
rebuilt — an export edited by hand is a second deck that will drift.

**An export that is a second implementation gets a mechanical check of its own.** A
hand-editable PowerPoint rebuild has its own layout engine, so the master's checks cannot see
its defects: read the geometry back out of the saved file and test bounds, collisions and the
font floor there too, estimating wrapped-text height pessimistically because a rebuilt file
cannot be measured the way a browser measures. Say plainly which renderer the user is getting,
and that **a rebuild does not carry its fonts** — on a machine without the typeface it
substitutes, while the master embeds them.

**The build is one named command chain, written down where the deck's files live.** Every
derived artifact comes after the thing it derives from — diagrams rendered before the rebuild
that inserts them, checks after the build that produces the file they read. Re-running the whole
chain must be cheaper than remembering which parts to re-run, because the one step skipped is
the step that ships a stale figure while every check still passes.

**Tooling written to be reused is run against the finished deck before it is called done.** The
completed artifact is the fixture: on the deck this gate was written from, running the
generalized copies against a deck that had already passed found a units bug in the new code
within one command, which reading it had not revealed.

Close with the master and the chosen export by absolute path, and say which checks ran and what
they cover — never let a green result stand in for "this looks right". Ask the user to open the
master full screen on the machine it will actually play from — a deck that sits right in a browser
window can still clip on the projector — and to open the export the way its recipient will,
because a print can split a slide the master shows whole. One question covers both: does every
slide sit right?

## GATE 5 — the cold pass, then the user's own pass.

The deck claims to work on the GATE 0 audience. **The only honest test is a viewer who actually
has no context** — a fresh subagent, or a colleague if the user prefers. Its prompt carries
exactly three things: the audience description written down at GATE 0, the slides as the
audience gets them — the master's notes-free rendering, because the room never gets the notes;
never the scripts, never the HTML source with its comments and hidden text — and the reporting
instructions; it is told to read nothing else, not the source, not the scripts, or it is not
cold. It reports back, each item with its slide number: the takeaway it took, the argument as it
understood it, every term it met before the deck taught it, every claim it took as measured,
every question it was left holding. **The user judges whether the played-back
takeaway matches the one from GATE 0 — if it does not, the deck failed**, however clean the
slides.

**Talk mode adds the timing pass, measured, not assumed.** The speaker reads one act aloud, the
user or the speaker times it and reports the number, and the measured pace is written down with
the GATE 0 answers — a resumed session must be able to re-price the acts after a fix. That pace
— theirs, never a book value, never substituted silently — prices every act's notes against the
stated duration; if the speaker cannot be reached, say so and let the user decide whether the
pass waits or they stand in. A slide whose notes outrun the time it can hold gets flagged, and
the fix is cutting words or splitting the slide, never asking the speaker to talk faster.

Fixes land on slides approved at GATE 3 and that is what this gate is for — it is not a
stop-the-run event; stop-the-run stays for new direction (a changed audience, new evidence, a
changed takeaway, a mode switch). List every fix, re-run the GATE 3 verification on every
touched slide and the GATE 4 mechanical checks on the rebuilt master, never patch silently.
**A fix that changes a headline is a storyline change even here**: name it, get the user's yes,
update the storyline file, re-run the flip test, and only then the cross-check. **A fix that
changes what any slide claims needs a fresh cold viewer** — one who has seen draft one is no
longer cold. You write the cold-pass record as you go: one entry per pass — what stumbled, at
which slide, and what changed because of it.

**The cold passes end when a fresh viewer's playback changes nothing on any slide.** Questions
a cold viewer is still holding are the user's call — a gap in the deck, or a question the deck
is right to leave open — and the user says so. Only then does their own pass open.

Then the user's own pass, because **their eyes are the bench**: for a talk deck, rehearsing it
aloud once end to end; for a reading deck, reading it as the recipient would. A deck every check
passed can still lose its room, and only a human notices where. Fix what the pass surfaces under
the same rules, then deliver: the storyline, the slide scripts, the master, the exports, the
cross-check tool and the cold-pass record, with the GATE 0 answers beside them, in the home
named at GATE 0. Close with the deck by absolute path and one question: done?

## What this deck may never do

It carries real numbers to a room that will believe them, and a room asks no footnotes. So: no
claim the source does not support, no measured-sounding statement about anything unmeasured, no
number without a home, no takeaway stronger than its evidence — and when the honest answer is
"not built or tested yet", the deck says so on the slide, not in the notes. **A beautiful deck
that overclaims is worse than no deck**, because it cannot be recalled from the room that saw
it.
````
