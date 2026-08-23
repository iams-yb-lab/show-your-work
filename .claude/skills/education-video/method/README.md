# Picture — the shared HTML-to-video exporter

`engine/` is the shared sound; this is the shared picture. Three tools, in the order a film meets them:
`composition_check.py` passes or fails the composition, `export_html_video.py` turns it into frames, and
`deliver_film.py` muxes the frames, the approved mix and a switchable subtitle track into the film.

The composition used to come back from Claude Design as a bundle. Since 2026-08-22 `education-video`
authors it here instead — the reason, the evidence and what it deliberately left alone are in the
commit that applied it, and in the pull request that carried it.
The exporter does not care which: it renders any page that honours its seek protocol, and the two
Claude Design bundles in `../education/` still render exactly as they did.

## Provenance

**`export_html_video.py` was written by Codex**, on 2026-08-12, for the intro film. It is copied here
**byte-identical** — SHA-256 `f4c79a7a…` matches the original at
`%USERPROFILE%\.codex\visualizations\2026\08\12\019ff55c-…\temperature-controller-intro-video\` — so
its provenance stays checkable. It is not ours to rewrite; fixes belong in a wrapper or upstream.

It lived outside the repository for two days, which meant the intro film's picture was not regenerable
here at all and could not be made on the Mac. That is why it is in now.

## What it does

Serves the bundle's own directory on an ephemeral `127.0.0.1` port, drives headless **system Chrome**
through Playwright, and steps the composition frame by frame with the bundle's own
`data-om-seek-to-time-frame` protocol — deterministic seek-and-shoot, not real-time capture. Each frame
is a JPEG piped straight into ffmpeg as `image2pipe`, encoded H.264 High, yuv420p, BT.709, faststart.

**It reads the duration off the page**, from `data-om-exportable-video-with-duration-secs`, and renders
`round(duration × fps)` frames. So the film's length is decided by the bundle, not by an argument, and a
render is legitimately up to half a frame shorter than the audio it will be paired with.

**It is silent by design.** `-an` is hardcoded and there is no audio argument: the sound is muxed on
afterwards with the video stream copied. That is the correct order — see `../natural-voice/`.

## Running it here

```bash
# ffmpeg must be on PATH: the script looks for it with shutil.which and has no override flag.
# winget installs it outside the shell's PATH; this is where, under whoever is logged in. The glob
# covers the version directory, which changes at every upgrade.
PATH="$(echo "$HOME"/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin):$PATH" \
python export_html_video.py "<bundle>.html" "<out>.mp4" --width 1920 --height 1080 --overwrite
```

- **Playwright** is installed only in the default `python` on this box, not in any of the audio venvs.
  A system Chrome is required; `playwright install` is not.
- **`--width`/`--height` must equal the composition's authored size** or it aborts on a bounding-box
  check. Default is 4K, which is wrong for a 1920×1080 composition.
- **`--frames 60`** renders a probe in seconds. Use it before committing to a full pass — this repo's
  8110-frame film takes ten minutes at ~13.5 fps.
- **Captions:** a bundle may burn its captions into the frames. `window.TWEAK_DEFAULTS` is plaintext and
  host-rewritable, so flipping `"captions":true` to `false` on a copy of the bundle turns them off; the
  same trick reaches the accent colour. Verify by re-rendering one frame and looking at it.

## `composition_check.py` — what a composition has to get right

Run it before any long render. It fails on: no export root, a root whose box is not the authored size,
a missing or disagreeing duration attribute, anything fetched at render time, a non-deterministic seek,
an element overflowing the canvas, text under the film's font floor, or a page error — each checked at
every sampled instant, because a composition's contents are a function of time and t=0 proves nothing.

**The determinism check is the one that earns its keep.** It seeks to an instant, screenshots, comes
back to it out of order and demands the same pixels. A composition driven by a CSS animation or a
`requestAnimationFrame` clock looks perfect in a browser and renders as a smear, and this is the only
thing that catches it before the frames are on disk.

Its overflow and font-floor checks are adapted from `../../presentation/tools/render_check.py`, where
they were first proved on this repository's own deck. That deck is per-slide; this is per-instant.

```bash
python composition_check.py film.html --width 1920 --height 1080 \
    --expect-duration 270.349 --font-floor 28 --contact-sheet out/sheet
```

`--contact-sheet` writes the sampled frames and, if ffmpeg is on PATH, tiles them into one
`contact-sheet.png`. **Look at the sheet, never a single frame** — a lone frame can land between one
beat clearing and the next building, which on the intro film read as a broken scene and nearly bought a
false defect report.

## `deliver_film.py` — the mux, and the subtitle track that stays off

Takes the silent render, the mix approved at GATE 3 and the `.srt`, and writes the delivered MP4:
video stream copied, audio to AAC, captions as a `mov_text` track. Then it checks its own work — the
video stream's MD5 before and after, the track extracted back out and diffed against the sidecar, the
picture/audio duration gap against one frame — and exits non-zero rather than handing over a file that
merely looks finished.

**ffmpeg cannot switch an MP4 subtitle track off, and it does not say so.** `-disposition:s:0 0`,
`-disposition:s:0 -default` and `-default_mode passthrough` all produce a `tkhd` with flags `0x000003`
on ffmpeg 7.0 — ENABLED plus IN_MOVIE — so the track comes up burned-on-looking in QuickTime and the
command that was supposed to prevent it reports success. What works is clearing bit 0 of the subtitle
track's `tkhd` flags in the finished file: **one byte, inside a fixed-size box**, no offset moves, the
media data untouched, and `ffprobe` then reports `disposition:default=0`. `switch_subtitles_off()` does
exactly that and nothing else.

```bash
python deliver_film.py --picture silent.mp4 --audio mix.wav \
    --subtitles captions.srt --output film.mp4 --fps 30
```

## What has been run, and on what

Both tools were written on 2026-08-22 against a synthetic three-second composition — a moving dot, a
clock caption, a deliberately broken twin — on macOS with a pip-installed static ffmpeg 7.0 and system
Chrome. Every check was made to fire on purpose and then to pass: the failing twin returned a wrong
duration, 11px text, an element 160px past the canvas, a CSS animation and a missing image, and all
five were reported. The subtitle byte patch was verified by reading the track back out of the finished
file and by the video stream's MD5 being unchanged.

**Neither has been run on a real film.** The intro film predates both. Read what they print on the
first real pass rather than trusting the exit code.
