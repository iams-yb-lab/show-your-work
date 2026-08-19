---
name: technical-report
description: Use when the user wants to write a report or technical write-up that presents a project to readers outside it — a design report, a findings report, documentation a reader with background but no project context must understand on their own. Start here BEFORE writing any outline or section. Triggers on "design report", "write a report", "write up this project", "document this design", "present this project", "make this understandable to outsiders".
---

# Technical report — the document that stands alone

The order is **evidence → skeleton → sections → cold read**, and it is not negotiable. Prose
written before the evidence is mapped asserts things nothing supports; sections written before
the structure is approved get rebuilt after every cross-reference exists. The reference this
method produced is a design report that takes a reader with no project context from "why does
this exist" to a two-sided verdict, defining every term on the way; it lives with the project it
describes, never here.

## Never edit a skill. The exact words, or not at all.

**This file and every other skill are read-only.** Not a wording tweak, not one more bullet, not
"while I was in there". A skill travels between repositories, so a session that quietly improves
one changes how every future session works, everywhere, unreviewed.

**The only exception is the user typing `I insist on editing the skills`** — exactly, not a
paraphrase and not a typo. Anything short of it, *including* a direct "put this in the skill",
means: say you are not going to, write the request down where the current work lives, and keep
following the skill as written.

## Who the report is for — the contract every sentence signs

**The reader has the background and none of the context.** They can follow the math and the
physics; they have never heard of the project, its parts, or its vocabulary. So the report may
assume competence and must assume ignorance: a derivative needs no apology, and every
project-specific term, part and quantity gets taught. GATE 0 turns this into two explicit lists —
what may be assumed, what must be taught — and every sentence is judged against them.

## You deliver three things

**Every technical-report task ends with exactly these, in the order they are made:** the **evidence map** —
every number and load-bearing claim the report will carry, each with one home and an honest
status (GATE 1); the **report** — skeleton approved first, then sections one at a time, each
verified before the user sees it (GATES 2–3); and the **cold-read record** — what a reader with
no context stumbled on and what changed because of it (GATE 4). All of it lives where the user
said at GATE 0, never next to the skill.

## How this runs — the plan first, then one gate at a time

**Before anything else, post the plan as an unticked checklist and ask to begin** — no reading,
no questions, no work; it is the first thing the user sees.

```
- [ ] GATE 0  the interview — audience, subject, evidence, verdict, home
- [ ] GATE 1  the evidence map — every number, one home, an honest status
- [ ] GATE 2  the skeleton — the whole report, a few lines per section
- [ ] GATE 3  the sections — one at a time, verified before shown
- [ ] GATE 4  the cold read — a reader with no context, then the mechanical pass
- [ ] GATE 5  the user's read — end to end, then delivery
```

Then ask **"Ready to begin?"** and wait for the answer.

**Every message opens by naming the gate** — `GATE 3 of 5 — the sections.` The user must never
have to work out where in the process they are.

**A gate ends when the user says it is good, never when you decide it is.** Show the gate's
output, say precisely what needs judging, stop. Do not begin the next gate in the same message,
do not work ahead while waiting, and never read silence as approval. **The one that gets skipped
here is the skeleton: ask whether the structure is right before a single section is written**,
because prose is the expensive half — a structural change after GATE 3 opens renumbers every
cross-reference, reorders the concept chain, and strands sections the user already approved.

**A change that lands on an already-approved gate stops the run.** When new direction arrives — a
different audience, new evidence, a changed verdict — name the earlier gate it invalidates, say
what rebuilding costs (which approved sections it touches, which cross-references break), and
ask whether to go back. Reopening an approved artifact is the user's call, never yours, and never
something you do by quietly editing it.

**Tick the box and repost the checklist** as each gate is approved, so progress is visible
without scrolling back.

**Close a gate with what to read and one question. Nothing else.** Name the artifact **by
absolute path**, name what needs judging, stop. No findings list, no summary of what is in the
file, no account of what you fixed on the way. The exceptions: GATE 0 closes by playing the
answers back as bullets, and a GATE 3 section close also reposts the ticked skeleton.

## GATE 0 — the interview. Ask before reading anything.

Ask in two or three short windows, not one wall. **An unanswered question is a question, not a
default** — never open GATE 1 on an assumption.

- **Where does the report live?** Never next to the skill, never defaulted. The report, the
  evidence map and the cold-read record all land there.
- **Who reads it?** Get the two lists: what this reader may be assumed to know, and what must be
  taught. "Background but no project context" is the register this skill exists for, but the
  boundary is the user's to draw, in their words.
- **What is the subject, and where is the evidence?** Paths — the design files, the data, the
  datasheets, the calculations, the prior documents. Note what exists on disk versus what lives
  only in the user's memory; the second kind gets written down at GATE 1 and labelled as their
  statement.
- **What has actually been done?** Built, measured, simulated, specified, or only intended — per
  subsystem. This becomes the front matter, and it bounds every sentence after it.
- **What question does the report answer, and does it end on a decision?** A report with no
  verdict is a tour. If the decision is still open, the report can end on an honest tie with its
  axis named — but establish now which kind of ending this is.
- **Is there a falsifiable target?** The number and its pass rule, or the honest absence. "Very
  stable" gives the report nothing to judge anything against.
- **What must the report not claim?** The scope limits, in the user's words, collected now — they
  become a section, not a hedge scattered through the prose.
- **Where will it be read, and how long may it be?** Venue and length are constraints, not
  aesthetics.

Write the answers down where the report's files live — the audience lists, the evidence status,
the scope limits. Later gates read them, and a resumed session cannot replay a chat. Close by
playing the answers back as bullets and asking to open GATE 1.

## GATE 1 — the evidence map. Numbers before prose.

**Read every source end to end before writing a word of report.** Then build the map: one entry
per number and per load-bearing claim, each carrying its value, its unit, **its one home** — the
file and place it lives, which the report will link at every point of use — and an honest status:
**measured** (where, on what), **specified** (whose document, typical or maximum), **calculated**
(from which inputs), **assumed** (whose assumption, labelled provisional), or **unknown**.

- **Two sources that disagree get reconciled here**, or recorded as an open contradiction the
  report must carry visibly. Never silently pick one.
- **Namesake quantities get inventoried now** — the three things the project calls "temperature",
  the two things it calls "reference" — with the distinct name the prose will use for each. A
  report that lets namesakes share a label makes every later sentence a coin flip.
- **A number with no home does not go in the map**, and therefore never in the report. If the
  user states one from memory, write it down where the report's files live and point the map
  there, labelled as their statement.

Close with the map by absolute path and one question: are these statuses honest?

## GATE 2 — the skeleton. The whole report before any of it.

**Every section, at one to three sentences each — brief is the point.** Structure is cheap to
move now and ruinous to move after prose and cross-references exist. Nothing longer than three
sentences per section gets written at this gate.

The shape that works:

- **Front matter first: evidence status before any claim.** What is built, measured, specified,
  intended — and the target, stated once with its pass rule. A reader must know what kind of
  document they are holding before the first section.
- **Part 1 is the problem**, written for the reader who has never heard of the project: why this
  exists, in one or two sentences; then the one load-bearing concept (below); then the target and
  the judging criteria, kept separate — what must be achieved versus what is merely preferred.
- **One part per subsystem, and the parts share a shape** — architecture, then the math — each
  opening with a one-line *Scope:* note. A reader learns the structure once and reuses it.
- **A ruler section before any judgment**: the target converted into every unit the chain works
  in, so every later error has something to be compared against at the point it appears.
- **Open items and scope limits**, then **the verdict**: the decision, its reasons, why each
  loser lost — and what remains outside the report's reach, said plainly.

When GATE 0 found no falsifiable target, the ruler section and the pass rule drop out — and the
verdict must then say what the decision was judged on instead.

**Name the one load-bearing concept.** The reference report has exactly one — the error the
control loop cannot see — taught early as a thought experiment a reader can run in their head,
and every later section spends it: it names the hardest analysis section and it decides the
verdict. Find this report's one. If the report is a survey and genuinely has none, say so; but a
design report without one is usually a parts list wearing a title.

**Order sections by concept, not by convention.** No section may use a term or idea a later
section defines. The skeleton records, per section: the question it answers, the map entries it
draws on, and the new terms it introduces. That third list is the vocabulary plan GATE 3 checks
against.

Close with the skeleton by absolute path and one question: right sections, right order?

## GATE 3 — the sections. One at a time, verified before shown.

**Draft one section, verify it, show it, stop.** Approval of one section opens the next. Never
draft ahead while waiting — a later section regularly discovers something an earlier one must say
differently, and that is a stop-the-run event, not a quiet edit to an approved section.

**Write in this register:**

- **Plain English carrying the full meaning.** A term of art gets its plain-language mechanism at
  first use — what it does, not just what the letters stand for. "An NTC: its resistance falls as
  it gets warmer" teaches; the expansion alone does not.
- **One metaphor per concept, forever.** The reference calls the ADC reference "the ruler" at
  first use and never calls it anything else — the metaphor reappears in a section title and a
  table header. Never two metaphors for one thing; never one metaphor for two things.
- **Mechanism is a causal chain** — this pushes, so that moves, so the two cancel — never an
  assertion of quality. "It rejects drift" is a claim; the chain is an explanation.
- **Headings answer the reader's next question.** By the end of a section the reader is holding a
  question; the next heading should be its answer. "Why the warm setpoint is harder" beats
  "Thermal considerations".
- **Anticipate the stumble.** The part of a mechanism a reader will mistake for mattering gets a
  sentence saying it does not — "it does not appear in the final calculation."
- **A small diagram at each mechanism**, at the point of the mechanism. Text diagrams are fine;
  what matters is that the shape appears where it is explained.
- **Comparisons use identical columns at identical operating points**, anchored to the same few
  operating points across the whole report, so context the reader pays for once keeps paying.
  When exactly one variable differs, say so — that is what makes the comparison mean something.
- **Every table gets a narrator.** Prose beside it saying what to see in it, and any deliberate
  repetition declared as deliberate. Even omissions are declared — "the sign has been omitted
  because this section compares sizes."
- **Arithmetic gets a physical reason** — "rounded upward because an ADC cannot provide part of a
  usable bit" — and a formula gets its one trap stated (the unit, the sign) rather than a
  derivation.
- **Numbers appear once and link home.** Every number links to its map home at the point of use.
  Facts repeat only when missing them is dangerous, and then deliberately.
- **Claims wear their status inline.** Proven, specified, assumed, estimated — in the sentence,
  not in a footnote. A quantity nobody has bounded is "must be measured rather than entered as
  zero", never silently zero.
- **Namesakes get their distinct names at every appearance**, per the GATE 1 inventory.

**Verify before the user sees it — every section, every time:**

- every number against the evidence map: value, unit, status, home;
- every claim against the front matter: nothing measured-sounding about the unmeasured;
- every calculation re-derived by a different route or a fresh subagent — re-reading your own
  arithmetic is not a second pass — now, while it is one section's worth;
- every term against the vocabulary plan: defined before used, defined exactly once;
- every cross-reference pointing where it says.

Close each section with its location and one question, and repost the skeleton with finished
sections ticked, so progress is visible inside the gate.

## GATE 4 — the cold read. The audience claim, tested honestly.

The report claims to work on a reader with background and no project context. **The only honest
test is a reader who actually has none** — a fresh subagent, or a colleague if the user prefers.
Its prompt carries exactly three things: the audience description written down at GATE 0, the
report itself, and the reporting instructions below — and it is told to read nothing else, not
the evidence map, not the project, or it is not cold. It reports back, each item with where in
the document it happened: every term it met before the report taught it; every question it was
left holding; every claim it took as measured; and its own playback of the verdict and the
reasons. **The user judges whether that playback matches the verdict the report meant — if it
does not, the report failed**, however clean the prose.

Alongside it, the mechanical pass over the whole document: term-before-definition order; any
number appearing twice with two values; compared tables still carrying identical columns at
identical operating points; every cross-reference and link resolving; the front matter still
true of the finished document; the scope-limits section covering everything the report does not
claim.

Fix what both surface. These fixes land on sections approved at GATE 3 and that is what this
gate is for — it is not a stop-the-run event; stop-the-run stays for new direction (a changed
audience, new evidence, a different verdict). But list every fix for the user and re-run the
GATE 3 verification on every touched section; never patch silently. You write the cold-read
record as you go: one entry per reading — what stumbled, where, and what changed because of it.

**A re-test needs a new cold reader** — one who has read draft one is no longer cold. The gate
ends when a fresh cold read and the mechanical pass surface nothing that changes the document —
a leftover question is the user's call: a gap in the report, or a question the report is right
to leave open — and the user says so. Close with the cold-read record by absolute path and one
question: does the playback match the verdict you meant?

## GATE 5 — the user's read, then delivery.

The user reads the report end to end — reading, not skimming — because **their eyes are the
bench**: a report every check passed can still lose its reader, and only a human notices where.
Fix what the reading surfaces; a wording fix re-runs the GATE 3 verification for the touched
sections, and a fix that changes what any section claims reopens GATE 4 — the document the cold
reader certified no longer exists.

Then deliver: the report, the evidence map and the cold-read record, in the home named at GATE 0,
links resolving. Close with the report by absolute path and one question: done?

## What this report may never do

It carries real numbers and a verdict to people who will believe them. So: no claim the evidence
map does not support, no measured-sounding statement about anything unmeasured, no number without
a home, no verdict stronger than its reasons — and when the honest answer is "not built or tested
yet", the report says so in the front matter and again at the verdict. **A polished report that
overclaims is worse than no report**, because it cannot be recalled from the people who read it.
