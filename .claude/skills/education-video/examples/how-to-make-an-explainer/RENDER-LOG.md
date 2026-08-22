# Render log — how the picture became a file

What was learned turning Claude Design's HTML bundle into the delivered MP4, on 2026-08-13/14. Written
because almost none of it is guessable from the artifacts, and the next session will otherwise re-derive
it. The tool itself is documented in [`../../picture/README.md`](../../method/README.md).

## The short version

`Explainer Video as-delivered.html` came back from Claude Design with **burned-in captions on** and
**narration-only audio embedded**. One byte was changed to turn the captions off; the audio was ignored
entirely, because the exporter discards sound by design and the real mix is muxed on afterwards.
8110 frames at ~13.5 fps is a **ten-minute render**.

## Claude Design cannot make a video

Its encoder runs in the browser and only fires from a human clicking Share → Export → Video. Asking it
for an MP4 produces a dead end at the last step, after everything else is right. **It returns a page;
rendering is ours.** That is now in the skill and in `DESIGN-PROMPT.md`, which no longer asks for a file.

## What is inside the bundle

26.43 MiB, 391 lines, and it is not greppable in the way you would expect:

- **No static media tags at all**, and no `data:` URIs. Seventeen assets live base64-gzipped inside a
  `<script type="__bundler/manifest">`, and the runtime turns each into a `blob:` URL. Searching the
  plaintext for `<audio`, for an asset path, or for the export protocol's own attribute names **finds
  nothing** — they exist only after the JSX runs.
- **The only media element is a 2×2 px, opacity-0.01 `<video>`** created at runtime, fed a blob whose
  44-byte WAV header is synthesised in JavaScript. It carries
  `data-om-exportable-video-play-start/end` so a host exporter plays it during export.
- **The embedded audio was narration only** — two headerless raw PCM payloads, s16le/48 kHz/mono,
  13,920,000 B (145.000 s) + 12,033,504 B (125.349 s) = 270.349 s. Bit-for-bit our narration master
  truncated 24 → 16 bit, correlation 1.000000. No music bed: it is digital zero where the mix has music.
- **Three plaintext globals drive it**, in the inner template near the end of the file:
  `window.OM_SCENES` (8 scenes, durations summing to 270.349), `window.OM_PLAYBACK`, and
  `window.TWEAK_DEFAULTS`.
- **A second, finer cue table is inside `explainer.jsx`** — `C = {c1: 0.9, … c55: 266.92}`, commented
  *"from cues.json — locked"*. So the bundle's timing agrees with our cue sheet to the millisecond,
  independently derived. That is the cross-check passing from the far side.

## Turning off burned-in captions

**`window.TWEAK_DEFAULTS` is plaintext and deliberately host-rewritable**, wrapped in
`/*EDITMODE-BEGIN*/ … /*EDITMODE-END*/`:

```
{\"motionEditor\":true,\"captions\":true,\"accent\":\"#FF6B4A\"}
```

Note the escaping: it sits inside a JSON-escaped document, so the bytes to match are
`\"captions\":true`, **not** `"captions":true`. Replacing `true` with `false` on a copy is a **one-byte
file**: 27,713,348 → 27,713,349 bytes. `Explainer Video captions-off.html` is that copy, and it is what
was rendered.

The Tweaks panel cannot be used instead: it initialises closed and only opens on an
`__activate_edit_mode` postMessage from a host frame, so opening the file in a browser gives you no way
to reach the toggle.

**Verify a flag change by re-rendering one frame and looking at it** — `--frames 60`, extract frame 55,
compare. Sixty frames is seconds; the full pass is ten minutes.

## Substituting the audio, if it is ever needed

It was not needed here, because the exporter passes `-an`. Recorded because it is not discoverable:

- **Zero-edit path, which the page prefers:** `explainer.jsx` HEAD-probes `audio/combined-audio.m4a`
  then `audio/combined-audio.mp4` relative to the page and uses that as the `<video src>` over the
  embedded PCM. Drop an encode there and serve over HTTP — the exporter already serves the bundle's own
  directory, and a `file://` fetch of a relative path fails silently.
- **In-file path:** replace the base64 values in the manifest. The WAV header is computed from the two
  payload lengths, so one may be emptied; but the header is hardcoded PCM/1 ch/48 kHz/16-bit, so an MP3
  or AAC dropped in gets a RIFF header glued in front of it and will not play.

## The render, measured

| | |
|---|---|
| frames | 8110 = `round(270.349 × 30)`, read off the page, not passed in |
| rate | 13.2–14.9 fps, ~10 min wall clock |
| picture | 1920×1080, 30 fps, H.264 High, yuv420p, BT.709, silent, 2.8 MB |
| finished film | 270.333 s, 12.66 MB, AAC 274 kbps, −14.13 LUFS, −1.14 dBTP |
| duration gap | 16 ms — the picture is half a frame short of the audio, which is what the rounding costs |
| mux | `-c:v copy`, and the video stream's MD5 is unchanged, which is the only proof it was lossless |

## Two mistakes worth not repeating

**The first render had captions burned in**, and ten minutes went in the bin. The signal was there
before the render — Claude Design said so in its own handover note — and it was checked only after
watching a frame. **Extract a frame from a 60-frame probe before starting a full pass.**

**A single frame nearly cost a false defect report.** Two of nine sampled frames looked near-empty and a
scene looked broken; a twelve-frame sweep of the same scene showed it fully built and following the
brief beat for beat. The empty frames were sampling landing between one beat clearing and the next
building. **A contact sheet, never a frame.**
