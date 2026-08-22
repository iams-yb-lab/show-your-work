---
name: education-video
description: Use when the user wants to make an educational or explainer video — teaching how something works, walking through a design, presenting technical findings. Start here BEFORE any picture, animation or design work. Triggers on "explainer video", "educational video", "video explaining how X works", "teach this in a video", "walkthrough video".
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

## You deliver six things, and the last one is the film itself

**Every education-video task ends with exactly these, in this order:**

the audited **source document** (GATE 1); the **script** — words, order, performance grouping, one trace
per claim (GATE 2); the **audio** — a lossless locked master and captions derived from it (GATE 3); the
**image set**, gathered, cleaned and licensed, with its manifest (GATE 4); the **picture** — one
self-contained HTML composition you build and the user approves silent (GATE 5); and the **film** — one
MP4 carrying that picture, the approved mix, and a subtitle track the viewer switches on (GATE 6).

**The picture is yours, end to end.** Nothing is pasted into another tool and nothing comes back from
one, so **never ask where the picture comes from or who makes it**: it is decided, and asking spends a
GATE 0 question. Ask what the picture should *look like*; never who draws it.

**It is HTML, and the tool that turns it into frames is already here** —
[`video/picture/README.md`](../../../video/picture/README.md) documents it: a page that answers a seek
with the frame at that instant, stepped frame by frame into ffmpeg. Not Blender, not a 3D scene, not
screen capture — mechanism animation and hardware beauty shots are `showoff-render`'s job, and that
boundary has not moved.

**Captions are never painted into the frames.** They ship as a track the viewer turns on, off by
default, with the `.srt` beside the film. The reference film's picture arrived with its captions burned
in, the full pass was rendered anyway, and ten minutes of render went in the bin — and burned-in
captions cannot be turned off, restyled or translated once they are encoded.

## How this runs — the plan first, then one stage at a time

**Before anything else, post the plan as an unticked checklist and ask to begin** — no reading, no questions, no work; it is the first thing the user sees.

```
- [ ] GATE 0  the interview — ten-odd questions, in windows
- [ ] GATE 1  the source document
- [ ] GATE 2  the script — cue sheet, traces, slot lengths
- [ ] GATE 3  the audio — takes, QA, locked master, captions
- [ ] GATE 4  the images — gathered, cleaned, licensed, manifest
- [ ] GATE 5  the picture — the composition, checked, approved silent
- [ ] GATE 6  the film — rendered, mixed, subtitle track, handed over
```

Then ask **"Ready to begin?"** and wait for the answer.

**Every message opens by naming the stage** — `GATE 3 of 6 — the audio.` The user must never have to
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

## GATE 5 — the picture. You build it; it is approved silent.

**One self-contained HTML file, and nothing is fetched at render time.** Fonts and images are inlined;
the renderer serves the file's own directory on a local port and has no network. Generate the file from
a template with a build script and never hand-edit what the script produced — an edit that lands in the
output instead of the template is lost at the next build.

**The composition is a pure function of time.** The exporter dispatches a seek event carrying an
instant, screenshots, and steps on, so the element carrying the export attribute must render that
instant on demand, having never played the frames before it. No CSS transitions or keyframes driving
anything that matters, no `requestAnimationFrame` clock, no media element as the timebase. **A
composition that animates itself renders as a smear, and it looks perfect in a browser.**

**The duration lives in the page, not in a flag** — the exporter reads it off the export attribute and
renders `round(duration × fps)` frames. **Set it from the locked master**, so the audio is still the
timing authority at the last gate exactly as it was at the third. The root's box must equal the authored
size or the render aborts before the first frame.

**The scene table and the cue sheet drive it, and the composition re-derives nothing.** Every cue's
start and slot comes from the file the master was measured into. **The GATE 4 images sit in it as they
were licensed** — the picture draws type, diagrams, charts and motion, and never redraws a photograph.
**The do-not-draw list is the document's scope section**, lifted whole.

**Check it mechanically before rendering anything long.** Nothing may extend past the canvas, no visible
text may fall below the film's font floor, the same seek twice must give the same pixels, and the scene
table must sum to the page's own duration.
[`composition_check.py`](../../../video/picture/composition_check.py) is that check, and it writes the
contact sheet the next rule asks for.

**Probe, then a contact sheet, never a single frame.** Sixty frames cost seconds where the full pass
costs minutes. A lone frame can land between one beat clearing and the next building — on the reference
film that looked like a broken scene and nearly bought a false defect report, and a twelve-frame sweep
of the same scene showed it built and following the brief beat for beat.

**Close the gate with a silent probe render, and say that it is silent.** Its path, what needs judging,
one question. What is approved here is the picture; the film is the next gate and it is the expensive
one, because a picture change after GATE 6 costs the whole render pass again.

## GATE 6 — the film. One file, and the captions are a track, not paint.

**Render at the delivery size and frame rate, then mux — never re-encode the picture.** The render is
silent by design and the sound goes on afterwards with the video stream copied. **The video stream's
MD5, before and after, is the only proof the mux was lossless.** Check it and say so.

**The audio is the combined mix the user approved at GATE 3**, never the narration master. A film
delivered with the dry voice is the failure this whole order exists to prevent, and it is silent about
itself: the file plays, and the music is simply not there.

**Nothing leaves this machine, so nothing is compressed to travel.** Narration and mix stay lossless
WAV until the mux, which is the only encode the audio ever gets.

**The captions go in as a subtitle track with the default flag cleared** — `mov_text` inside the MP4,
off until the viewer switches it on — and the `.srt` ships beside the film for upload and re-styling.
**Verify by extracting the track back out of the finished file and diffing it against the sidecar**: a
track that is present but empty is indistinguishable from a good one until somebody turns it on.

**Never burn captions into the frames.** If a platform genuinely needs them burned in — silent autoplay
in a feed — that is an *additional* file the user asks for by name, and the switchable film is still
what gets delivered.

**Measure the file you are handing over, not the one you fed in.** Loudness and true peak on the
delivered MP4, and its duration against the master. The picture is `round(duration × fps)` frames, so it
is legitimately up to half a frame shorter than the audio; anything past one frame means the
composition's duration and the master disagree, which is a GATE 5 defect and not a rounding one.

[`deliver_film.py`](../../../video/picture/deliver_film.py) does the mux, the disposition and the
verification in one pass. **It has never been run on a finished film** — the first run is the one that
proves it, so read what it prints instead of trusting that it worked.

**Hand over in the film's own directory, the one agreed at GATE 0.** The file, its duration, and one
line on how to switch the subtitles on. Nothing else: the film is the message.


## Cross-check it mechanically

Never eyeball the agreement between script, scenes and film. Build a tool — early, it is cheap — that
parses the scene table out of the composition and the cues out of the script and exits if they disagree
by more than 0.1 s, plus a check that scene durations sum to the real file duration within 0.05 s. The
two are written at different gates, hours apart, so editing one and forgetting the other surfaces here
rather than in the film.

**Point each gate at one artifact, and say which.** A limit that belongs to a delivered file will
manufacture failures if aimed at a raw take; a wpm ceiling that sizes slots while writing means
nothing measured against a recording. Before believing a red result, check what it was written about.

## What this film may never be

It carries real numbers to people who will believe them. So: no claim the source document does not
support, no measured-sounding statement about something unmeasured, no number without a home, and when
the honest answer is "not built or tested yet", the film says so. **A beautiful film that overclaims is
worse than no film.**
