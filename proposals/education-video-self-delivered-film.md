# Proposal: `education-video` delivers the film itself, with a switchable subtitle track

**Status: APPLIED 2026-08-22.** The user authorized the edit with the exact phrase and specified the
change: GATE 5 no longer hands a prompt to Claude Design, the run ends with the finished video, and
the captions ship as a subtitle track the viewer can turn on rather than painted into the frames.
Three design questions were put in a question window before anything was written; the answers were
*pick whatever matches Claude Design's quality and reuse what `presentation/tools/` already proved*,
*MP4 with a soft `mov_text` track plus the sidecar `.srt`*, and *six gates — the picture approved
silent, then the film*. This document is the record and the rationale.

## Why

The old GATE 5 was a paste. Its last deliverable was one self-contained prompt, the user copied it
into Claude Design, waited, and got back an HTML bundle that we then rendered. Three costs came
with that seam, and all three are recorded in this repository rather than argued from taste:

- **The picture came back with captions burned into the frames.** The reference film's bundle
  arrived with `"captions":true`, the first full pass was rendered anyway, and ten minutes of render
  went in the bin. Burned-in captions cannot be turned off after the encode, cannot be restyled,
  cannot be translated, and are not read by anything that indexes video.
- **The bundle was not ours and was barely inspectable.** 26.43 MiB, seventeen assets
  base64-gzipped inside a `<script type="__bundler/manifest">`, no static media tags, nothing
  greppable until the JSX had run. Turning the captions off was a one-byte edit found by reading
  the file for an afternoon. A composition we author is a diff.
- **The audio in the bundle was narration only** — digital zero where the mix has music — so the
  file that came back was never the file to ship, and knowing that depended on measuring it.

Against that, the seam bought one thing: a picture department. That is the part the user has now
decided differently, and the tooling to replace it already exists here — the exporter renders any
page that honours its seek protocol, and `presentation/` proved out the build-and-check pattern for
a self-contained HTML master on this repository's own deck.

## What changes

**Six gates, not five.** GATE 5 becomes the picture — one self-contained HTML composition we build,
checked mechanically, approved *silent*. GATE 6 is new: the full render, the mux against the
approved mix, the subtitle track, the verification, the handover. The picture gets its own approval
for the same reason the script does — the expensive half of the old process was the re-record, the
expensive half of this one is the full render, and a wrong picture must be caught before it.

**The picture is ours.** The skill's `You never design, draw or animate the picture` section is
replaced. What stays settled is that it is *not a GATE 0 question*: the user is asked for the visual
register, never for who draws it or where it comes from. The composition is HTML, deterministic in
time, and rendered by the exporter that is already in `video/picture/`. 3D and mechanism animation
are still not this skill's business — that is `showoff-render`, and the line between them is
unchanged.

**Captions become a track.** The delivered MP4 carries a `mov_text` subtitle stream with the
default disposition cleared, so it is off until the viewer switches it on, and the `.srt` sits
beside the film for upload and re-styling. Burning captions into the frames is now forbidden
outright; a burned-in copy is an *additional* file the user has to ask for, never the delivery.

**Two shared tools, in `video/picture/` where they travel with the skill.**
`composition_check.py` is the GATE 5 gate — export-contract, exact canvas size, overflow, font
floor, determinism, and a contact sheet — adapted from `presentation/tools/render_check.py`, which
is where the overflow and font-floor checks were first proved. `deliver_film.py` is the GATE 6
mux — approved mix in, subtitle track in with the default flag off, video stream copied, and the
verification the render log says was the only proof the mux was lossless: the video stream's MD5
before and after, plus extracting the subtitle track back out and diffing it against the sidecar.

## What is deliberately NOT changed

- **The order.** `document → script → audio → picture` is untouched, and the audio is still the
  timing authority. The composition's duration is set *from* the locked master; the master is never
  cut to the picture.
- **GATE 0 through GATE 4.** The interview's eleven topics, the twelve document-readiness
  conditions, the script rules and the image gate carry word for word. Only three lines move:
  `interview.md`'s picture-direction and delivery questions, its settled-questions list, and
  `images.md`'s one reference to briefing Claude Design.
- **Who owns a stage ending.** Still the user, still never read from silence, and a change landing
  on an approved stage still stops the run and costs a decision.
- **The lossless rule.** It used to be justified by *nothing is uploaded to an encoder*. The
  justification is now simply that nothing leaves the machine at all; the conclusion is the same and
  the WAV stays lossless until the final mux.

## What this obsoletes elsewhere

`proposals/showoff-render-wrapper.md` argues, correctly for 2026-08-17, that `showoff-render` should
not copy education-video's Claude Design handoff because *there Claude is the picture department and
the final deliverable is the rendered master itself*. That contrast is now gone: both skills render
their own master. The distinction that mattered survives and is the real one — education-video is
audio-first, showoff-render is picture-first. That proposal is a dated record and is left as written.

`video/education/how-to-make-an-explainer/` is the reference film, made the old way. It is evidence
of what happened, not a template, and it is left alone: its `DESIGN-PROMPT.md` is kept verbatim as
the prompt that was actually pasted, and its `RENDER-LOG.md` is where three of the rules above are
priced. `presentation/` still describes the old GATE 5 on two slides; correcting a delivered deck is
a separate job the user has not asked for, and it is flagged rather than quietly rewritten.

## Verification

- `python tools/check_links.py` clean, including the new load-bearing link from the skill to
  `video/picture/README.md` — the gate now depends on a tool by name, so the link is registered in
  `GEOMETRY` and a move breaks the check instead of the film.
- Skill hashes re-blessed; the divergence and the new hashes are recorded in `EXPORT-MANIFEST.md`.
- **Neither new tool has been run.** This machine has no `ffmpeg` and no Playwright, so both were
  verified only by their argument parsing and a dry run that prints the exact `ffmpeg` invocation.
  They are unproven until the first film goes through them on a machine that has both, and the
  skill says so at the gate rather than implying a tested path.
