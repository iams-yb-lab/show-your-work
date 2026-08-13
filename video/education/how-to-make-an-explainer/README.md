# How to make an explainer video

The third film here, and the only one whose subject is the method itself: how to point Claude at your
own finished work and get a short, accurate video out of it. Made with the `education-video` skill,
which is also what it is about.

**4:30.3 · 8 scenes · 55 lines · 893 words · 1920×1080, 30 fps.** Finished and unposted: the film,
captions and upload copy are in `video/out/education/how-to-make-an-explainer/deliver/`. **One blank
before it goes up — the repository link in [`DESCRIPTION.md`](DESCRIPTION.md)**, because cue 53 says
"the link is below this video".

## What is here, and the order it was made in

| stage | file | what it is |
|---|---|---|
| 0 | [`BRIEF.md`](BRIEF.md) | the fifteen interview answers that decided the film |
| 1 | [`SOURCE.md`](SOURCE.md) | the audited document every spoken line traces to |
| 1 | [`NUMBERS.md`](NUMBERS.md) | the one home for every figure the narrator speaks |
| 1 | [`INTERNAL.md`](INTERNAL.md) | how the target is proved, and never narrated |
| 2 | [`script/voiceover-script.md`](script/voiceover-script.md) | words, order, performance grouping, one trace per line |
| 3 | [`script/captions.srt`](script/captions.srt) | derived from word timestamps on the finished master |
| 4 | [`images/MANIFEST.md`](images/MANIFEST.md) | empty on purpose — nothing here is photographed |
| 5 | [`DESIGN-PROMPT.md`](DESIGN-PROMPT.md) | the prompt that was pasted into Claude Design |
| 5 | [`picture/`](picture/) | the HTML bundles it returned — as delivered, and the captions-off copy that was rendered |
| 5 | [`RENDER-LOG.md`](RENDER-LOG.md) | how the page became a file, and what is inside the bundle |
| 5 | [`DESCRIPTION.md`](DESCRIPTION.md) | title, description, chapters — and the one blank |

Heavy audio — takes, restored sections, master, music, mix — lives under
`video/out/education/how-to-make-an-explainer/` and is gitignored.

## The tools, and what each one refuses to do

`tools/` and `audio/` were written for this film rather than inherited, and each carries a check that
already caught something:

| tool | job |
|---|---|
| [`tools/verify_numbers.py`](tools/verify_numbers.py) | re-derives every measured number from the media and the scripts |
| [`tools/script_stats.py`](tools/script_stats.py) | refuses an untraced line, banned vocabulary, or a number with no home |
| [`audio/sections.py`](audio/sections.py) | the 18 performance sections, and the pronunciation aliases |
| [`audio/generate.py`](audio/generate.py) | seeded takes; one voice, one parameter set, seed the only variable |
| [`audio/take_qa.py`](audio/take_qa.py) | transcript and pitch per take, cached so re-scoring is free |
| [`audio/restore.py`](audio/restore.py) | 24 → 48 kHz with four accept-or-fall-back gates |
| [`audio/master.py`](audio/master.py) | EQ, layout, one frozen master, and the per-section review slices |
| [`audio/align.py`](audio/align.py) | cue times and captions from word timestamps, never arithmetic |
| [`audio/music.py`](audio/music.py) | the bed, structured from the film's own scene table |
| [`audio/mix.py`](audio/mix.py) | one combined track, measured after it is built |
| [`tools/finish.py`](tools/finish.py) | muxes the sound onto the silent render, then refuses to believe it worked |
| [`tools/handoff.py`](tools/handoff.py) | generates the design prompt, and self-checks before writing |

Three of them need the virtualenvs listed in
[`../intro/audio/warm-natural-v2/environment.txt`](../intro/audio/warm-natural-v2/environment.txt):
generation, transcription and restoration each live in their own. The picture is rendered by
[`../../picture/export_html_video.py`](../../picture/export_html_video.py), which needs the **default**
`python` (the only one with Playwright) and ffmpeg prepended to `PATH`.

## Remaking it from here

```bash
python tools/verify_numbers.py                      # every measured number, re-derived
python tools/script_stats.py                        # traces, banned vocabulary, numbers with no home
python audio/take_qa.py --rescore                   # re-score cached transcripts, seconds not hours
python audio/master.py && python audio/align.py     # master, cue times, captions
python audio/music.py && python audio/mix.py        # bed and combined track
python ../../picture/export_html_video.py "picture/Explainer Video captions-off.html" \
       "<out>/picture/picture-silent.mp4" --width 1920 --height 1080 --overwrite
python tools/finish.py                              # mux and verify
python tools/handoff.py                             # regenerate the design prompt
```

Generation itself (`audio/generate.py`) needs the chatterbox venv and a GPU; everything above it is
reproducible without one.

## What is not checked

How it sounds. The narration and the mix were approved by ear, section by section, because there is no
instrument here for that — and one line is still flagged in `takes-qa.json` where the words cannot be
settled from text at all.
