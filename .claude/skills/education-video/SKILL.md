---
name: education-video
description: Use when the user wants to make a narrated educational or explainer video. Process notes only — order of steps, what to ask, how to do the voice, the images, the picture and the final file. Triggers on "explainer video", "educational video", "video explaining how X works", "teach this in a video", "walkthrough video".
---

# Education video — process notes

The order that works is **document → script → audio → picture → film**. Words are settled before
anything is recorded; the audio is recorded and locked before the picture is timed; captions and
scene boundaries are read off the finished audio. Done backwards it gives narration cut off
mid-sentence, a rushed line, and captions that fight the speech.

This file is a toolbox, not a procedure to recite. **What the film says and how it looks belong to
the user** — follow the project's own style guide if it has one, and ask if it does not. Nothing
here is an opinion on content, tone or structure.

## Working with the user

- Fit their way of working. Report first, plan first, storyboard first — whatever they ask for.
  No checklists to approve, no stage-numbered messages, no refusing to start until questions are
  answered.
- [`interview.md`](interview.md) lists the questions whose late answers cost a rewrite or a
  re-record. Read the project first; most are already answered. Ask the open ones together, in
  plain language, when they matter.
- Two things are worth a look before spending effort on them, because redoing them is the expensive
  half: the script before recording, and the combined audio before the picture is timed to it.
  Say what to read or listen to and why. If told to run through, run through and write down the
  decisions taken.
- Keep this file's process words (stage, cue sheet, master, composition) out of the deliverables and
  out of questions to the user.

## Source document

- Every number the film will speak has one home, with its precision and its status (measured,
  simulated, specified, estimated, typical). Nothing is spoken beyond that precision.
- A scope section listing what the film does not cover.
- Check the numbers and claims before scripting; a finished picture cannot be retimed cheaply.

## Script

- One cue per visual beat. Words, order, performance grouping, and a trace from each claim to the
  source document. **No timecodes** — nothing has been recorded yet.
- Slot length follows word count, not a fixed grid, so dense lines are not rushed.
- Leave 0.7–1.9 s at the top of each scene before the first cue, so a cut or music mark lands clear.
- Define terms at first use, in the document's own words.

## Audio

- **Load the `natural-voice` skill before generating any speech.** Two complete soundtracks were
  thrown away before its method worked.
- Generate whole sections as continuous performances; keep the endings and breaths; lock a
  narration master; derive captions (`.srt`/`.vtt`) from the master.
- Music, if any, goes on after the voice at a constant level with the narration in front, into one
  combined track. The picture is timed against that track, which never changes after lock.
- One language, one master, one timed picture. A second narration language is a second master and a
  second render.

## Images

- [`images.md`](images.md): list which cues need a photograph (usually few), gather and clean
  candidates yourself, licence every one, never remove a watermark, then ask the user what of their
  own to add. Record the set in a manifest. "None needed, everything is drawn" is a valid outcome.

## Picture

- One self-contained HTML composition; nothing fetched at render time. Build it from a template with
  a script; never hand-edit the built output.
- It must be a pure function of time: the exporter seeks to an instant and screenshots. No CSS
  animation or `requestAnimationFrame` clock driving anything that matters — that renders as a smear
  while looking perfect in a browser.
- Duration comes from the locked master and lives in the page; the root box equals the authored size.
- Scene table and cue sheet drive it; the licensed images sit in it unchanged; on-screen labels use
  the document's vocabulary.
- The exporter, its seek protocol and the checks are documented in [`method/README.md`](method/README.md).
- Check before any long render: [`composition_check.py`](method/composition_check.py) — overflow, font floor, determinism, duration. Probe
  sixty frames, then a contact sheet, never a single frame.
- Where a project instead uses a Claude Design bundle, the same checks and the same seek protocol
  apply, and the bundle may reference only the narration: substitute the combined mix.

## Film

- Render silent at delivery size and frame rate; mux the combined mix with the video stream copied,
  never re-encoded. Video-stream MD5 before and after is the proof.
- Captions as a subtitle track, default off, `.srt` beside the file. Never burned into the frames
  unless the user asks for that as an extra file. Extract the track back out and diff it.
- Measure the delivered file: loudness, true peak, duration against the master (at most half a
  frame short). [`deliver_film.py`](method/deliver_film.py) does mux, disposition and checks in one pass.
- **Every film ends on the project's closing credit slate**, held 2–3 s (default 3): lab logo and
  name, video title, release date, website with QR code, and the supporters' logos. Build it from the
  project's slate tooling ([`method/credit_slate/`](method/credit_slate/README.md)); the narration master carries matching tail silence
  before it is locked so the slate falls inside the timed picture. Same slate for every film and every
  language; only the title changes.
- Cross-check mechanically: a tool that parses the scene table from the picture and the cues from
  the script and fails on disagreement above 0.1 s, plus scene durations summing to the file
  duration within 0.05 s.

## Changing this skill

Skills are shared through `show-your-work`. When the repository owner asks for a change, make it
in the open: edit in the checkout, commit on a branch, push, open a pull request, refresh the hash
list, and tell them what changed. Do not let an installed copy drift silently.
