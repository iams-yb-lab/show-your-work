---
name: education-video
description: Use when the user wants to make an educational or explainer video — teaching how something works, walking through a design, presenting technical findings. Start here BEFORE Claude Design or any picture work. Triggers on "explainer video", "educational video", "video explaining how X works", "teach this in a video", "walkthrough video".
---

# Education video

The order is **document → script → audio → picture**, and it is not negotiable. Getting it backwards
produces narration cut off mid-sentence, a narrator rushing a dense line, and captions that fight the
speech. The reference this project produced is a nine-scene, 49-line explainer; its numbers live with
the film that measured them, never here.

## Never edit a skill. The exact words, or not at all.

**This file, [`interview.md`](interview.md), [`images.md`](images.md) and every other skill are
read-only.** Not a wording tweak, not one more bullet, not "while I was in there". A skill travels
between repositories, so a session that quietly improves one changes how every future session works,
everywhere, unreviewed.

**The only exception is the user typing `I insist on editing the skills`** — exactly, not a paraphrase
and not a typo. Anything short of it, *including* a direct "put this in the skill", means: say you are
not going to, write the request down where the current work lives, and keep following the skill as
written.

## You deliver five things, and the picture is not one of them

**Every education-video task ends with exactly these, in this order:**

the audited **source document** (GATE 1); the **script** — words, order, performance grouping, one trace
per claim (GATE 2); the **audio** — a lossless locked master and captions derived from it (GATE 3); the
**image set**, gathered, cleaned and licensed, with its manifest (GATE 4); and **one prompt the user
pastes into Claude Design** (GATE 5), which returns an HTML bundle you then render.

**You never design, draw or animate the picture** — not as HTML, not in Blender, not as slides, not as
screen capture. That belongs to Claude Design, so **never ask where the picture comes from or who makes
it**: it is decided, and asking spends a GATE 0 question. **Rendering the returned bundle to a video
file is yours**, because nothing else can do it.

## How this runs — the plan first, then one stage at a time

**Before anything else, post the plan as an unticked checklist and ask to begin** — no reading, no questions, no work; it is the first thing the user sees.

```
- [ ] GATE 0  the interview — ten-odd questions, in windows
- [ ] GATE 1  the source document
- [ ] GATE 2  the script — cue sheet, traces, slot lengths
- [ ] GATE 3  the audio — takes, QA, locked master, captions
- [ ] GATE 4  the images — gathered, cleaned, licensed, manifest
- [ ] GATE 5  the handoff prompt for Claude Design
```

Then ask **"Ready to begin?"** and wait for the answer.

**Every message opens by naming the stage** — `GATE 3 of 5 — the audio.` The user must never have to
work out where in the process they are.

**A stage ends when the user says it is good, never when you decide it is.** Show the stage's output,
say precisely what needs judging, stop. Do not begin the next stage in the same message, do not work
ahead while waiting, and never read silence as approval. **The script is the one that gets skipped:
ask whether the script is right before a single line is recorded**, because re-recording is the
expensive half of this process.

**A change that lands on an already-approved stage stops the run.** When new direction arrives — a
different premise, audience, verdict or scope — name the earlier stage it invalidates, say what
rebuilding costs, and **ask whether to go back.** Reopening an approved document is the user's call,
never yours, and never something you do by quietly editing it.

**Tick the box and repost the checklist** as each stage is approved, so progress is visible without
scrolling back.

**Close a stage with what to read and one question. Nothing else.** Name the artifact **by absolute
path**, name what needs judging, stop. **No findings list, no summary of what is in the file, no
account of what you fixed on the way** — that is what the file is for, and repeating it in chat asks to
be read twice. The single exception is GATE 0, which closes by playing the answers back as bullets.
A long closing message does not get read, and an unread message gets approved by accident.

## GATE 0 — the interview. Ask before writing anything.

**Read [`interview.md`](interview.md) in full and follow it exactly.** It holds the question list, what
may never be asked, and how the stage closes; a summary of a list is a second copy of it. **An
unanswered question is a question, not a default** — never open GATE 1 on an assumption.

## GATE 1 — the source document. Everything rests on this.

**An educational video is only as accurate as the document under it**, so a vague, unaudited or
half-finished source is a disqualifying problem rather than a starting point. If the user does not
have one, **help them write it first** — that is the work, and it is worth more than any animation.

### It is ready when

- **It states its own evidence status before any claim** — built, measured, simulated, or merely
  specified. Without it every number reads as measured, and the film asserts things nothing has done.
- **One falsifiable target with an explicit pass rule**, stated once. "Very stable" gives the film nothing to zoom to.
- **Every number has exactly one home**, linked at the point of use. Two copies eventually disagree.
- **Components named by part number, never by designator alone** — designators get renumbered.
- **Typicals, maxima, estimates and assumptions labelled inline**, or the narrator states a soft number in a hard voice.
- **Apparent contradictions reconciled in the text**, or the wrong figure is the one that reaches the screen.
- **Namesake quantities disambiguated** — unrelated temperatures sharing a label makes every caption a coin flip.
- **Mechanism is a causal chain, not an assertion.** "The design rejects drift" cannot be animated;
  "this pushes, so that moves, so the two cancel" can — every step is a state change something on
  screen can perform.
- **Comparisons use identical columns at identical operating points**, or the card-by-card scene collapses.
- **It ends with a decision, its reasons, and why the alternatives lost.** No verdict, no third act.
- **An explicit scope-limits section** — a ready-made do-not-narrate list.
- **Its numbers re-derived by a second pass.** Unaudited, the film inherits its errors at broadcast volume.

### Stop and fix the document if

Any of the above is missing, **or** the document is mid-rewrite, has open TODOs, or is queued for
someone else's editing pass on a section the film covers — a finished picture cannot be retimed
cheaply. Say what is missing. Never write a script against a document you would not defend.

## GATE 2 — the script

One cue per visual beat. **No timecodes in this file** — nothing has been recorded, so a start time
written now is a guess, and the picture would be cut to the guess. Words, order, performance grouping
and traces; times are measured off the master at GATE 3.

- **Every claim traces to a line in the source document.** Note the line. On the reference film six of
  its 49 lines do not, and they are its softest claims — one invents a decision axis the report never
  uses. That drift happened *with* a good process, so check it deliberately.
- **Rounding is the only transform allowed.** Never beyond the source's stated precision, and never a
  number it does not carry.
- **Slot length tracks word count, not a fixed grid.** On the reference film the longest slots are its
  densest technical lines, so the narrator never has to rush. A uniform grid guarantees a rushed
  sentence somewhere.
- **Open where the viewer is standing, never on what goes wrong.** Scene one is their situation and
  what they want out of it; scene two is the whole architecture, so they see the shape before any
  detail. A film that opens on failures is describing a mistake its viewer has not made yet, in a
  process they have not started. Costs, failures and war stories belong inside the stage they belong
  to, and in the closing verdict.
- **Leave a hole at the top of every scene** — 0.7–1.9 s before the first cue, so a music mark can
  land on the cut without speaking over it.
- **The document's own vocabulary and metaphors are the film's.** Define terms at first use. If the
  source already has a good image for something, use that one.

## GATE 3 — the audio, before any picture exists

**Load the `natural-voice` skill. It is not optional** — two complete soundtracks were thrown away here
before a method worked. **The audio is the timing authority.** Generate whole sections as continuous
performances, keep the endings and breaths, lock a narration master, then take caption and picture
timing off the finished file. The other way round gives you imperfect sentence joins — artifacts of
fitting narration into a finished video rather than a property of the voice.

**The stage is not over when the voice is.** Music goes on next — narration clearly in front, constant
music level, no ducking — mixed down to **one combined audio track**, and **the user approves that
track before GATE 4 opens.** A voice approved dry is not a voice approved under music, and the picture
must never be timed against an audio track that is still going to change.

## GATE 4 — the images. You raise it, and you arrive with candidates.

**Read [`images.md`](images.md) in full and follow it exactly.** Open this gate unprompted once the
master is locked; gather and clean candidates *before* showing anything; ask what the user wants to add
only after that; licence every image; never remove a watermark.

## GATE 5 — one prompt the user pastes into Claude Design

**Your last deliverable is a prompt, not a video — and it has to work on the first paste.** The user
copies it into Claude Design and waits; they should not have to answer a question, find a file, or run
a command afterwards. So it is **one message, self-contained**, and it carries:

- **where everything is** — absolute paths, and what each file is: the audio, the captions, the image
  manifest, the cue sheet;
- **the locked scene table** — number, title, in and out timecode, duration, to 0.1 s;
- **the cue sheet inside each scene** — every line, its start, its slot, and its words;
- **what each scene must show**, in the source document's own vocabulary, one instruction per cue;
- **what the finished video should look like** — the visual register in plain description, plus
  resolution, aspect ratio and frame rate;
- **the do-not-draw list**, lifted from the document's scope section;
- **the deliverable: the HTML bundle, not a video file.**

**Claude Design cannot encode video.** Its encoder lives in the browser and only fires from a human
clicking Export, so asking it for an MP4 gets you a dead end at the very last step. What it returns is
a self-contained HTML page that plays the film. **Rendering that page to a file is yours**, and so is
the audio: the bundle it hands back may carry only the narration, so check what it actually references
and substitute the real mix before rendering.

**Which means the audio stays lossless.** Nothing is uploaded to an encoder, so there is no size limit
and no reason to compress anything — hand over the WAV and keep it lossless end to end.

Scene boundaries come from the audio, never the reverse. **Read the prompt back as if you were the one
receiving it** — anything it assumes, it does not have, because there is nobody there to ask.

## Cross-check it mechanically

Never eyeball the agreement between script, scenes and film. Build a tool — early, it is cheap — that
parses the scene table out of the picture and the cues out of the script and exits if they disagree by
more than 0.1 s, plus a check that scene durations sum to the real file duration within 0.05 s. The two
are written independently, so editing one and forgetting the other surfaces here, not in the film.

**Point each gate at one artifact, and say which.** A limit that belongs to a delivered file will
manufacture failures if aimed at a raw take; a wpm ceiling that sizes slots while writing means
nothing measured against a recording. Before believing a red result, check what it was written about.

## What this film may never be

It carries real numbers to people who will believe them. So: no claim the source document does not
support, no measured-sounding statement about something unmeasured, no number without a home, and when
the honest answer is "not built or tested yet", the film says so. **A beautiful film that overclaims is
worse than no film.**
