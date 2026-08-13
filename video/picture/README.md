# Picture — the shared HTML-to-video exporter

`engine/` is the shared sound; this is the shared picture. One tool so far, and it is the only thing in
this tree that can turn a Claude Design bundle into a video file.

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
PATH="/c/Users/iams1/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0-full_build/bin:$PATH" \
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
