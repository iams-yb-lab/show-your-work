# Education — the intro film

The 5:38 explainer: what the instrument is for, why a millikelvin, and how the loop closes.
The picture is an HTML bundle captured to video; the audio is generated from the film's own
schedule.

```
picture/   the HTML bundle and the silent 1080p master
script/    voiceover-script.md and captions.srt
audio/     the tools below
```

## The chain

```bash
python video/education/intro/audio/intro_cues.py       # the film's schedule -> cues.json
python video/education/intro/audio/intro_narrate.py    # one WAV per narration line
python video/education/intro/audio/intro_score.py --out video/out/education/audio/score.wav
python video/education/intro/audio/check_intro.py      # measure the result back out
python video/education/intro/audio/intro_mux.py --audio video/out/education/audio/score.wav \
    --out "video/out/releases/Temperature Controller Intro 1080p scored.mp4"
```

| tool | what it does |
|---|---|
| `intro_cues.py` | reads the nine scenes out of the HTML bundle and the lines out of `voiceover-script.md`, and checks the two against each other and against the MP4 |
| `intro_narrate.py` | 🔴 **superseded** — speaks each line via edge-tts. Made `scored.mp4`; the current narration comes from `warm-natural-v2/` |
| `intro_score.py` | synthesises the bed from the scene table, ducks it, levels and masters |
| `check_intro.py` | finds the section marks with an onset detector, measures loudness and the speech band |
| `intro_mux.py` | muxes with `-c:v copy` and proves the video stream is unchanged; `--clip` cuts samples |
| `intro_env.py` | where the repo, the shared engine and ffmpeg are |

Nothing above needs the board, and nothing writes outside `video/out/education/` except the mux.

**Only the narration step was superseded.** `intro_cues.py` reads the film's schedule,
`intro_score.py` synthesises the music bed, `check_intro.py` measures the result and
`intro_mux.py` proves the picture is untouched — none of them is a voice tool, and all four
still stand. Swap `intro_narrate.py` for `warm-natural-v2/` and the rest of the chain is intact.

## Warm-natural narrator v2

[`audio/warm-natural-v2/`](audio/warm-natural-v2/) is the film-specific production record for
the approved Chatterbox narrator: selected contextual takes, fixed-picture alignment, 48 kHz
restoration, music, mix and integrity reports. Heavy artifacts lived under
`../../out/education/warm-natural-v2/`; the finished cut stayed with the project that made them.

The reusable identity and voice-agnostic acoustic method live in
[`../../../natural-voice/`](../../../natural-voice/). New films should generate continuous audio first and
time their captions and picture from that master; the v2 line alignment exists only because
this picture was already finished.

## What it rests on

- **The engine is shared, not copied.** [`../../../_shared/audio/`](../../../_shared/audio/) holds the loudness meter, the
  limiter, the sliding maximum, the voice chain and the pitch set, all written for the assembly
  film. A second copy of a BS.1770 meter is a second answer to the same question.
- **Every cue is the film's own.** Scene boundaries come out of `window.OM_SCENES` in the HTML
  bundle; line timecodes come out of the script. Retiming the film moves the audio with it.
- **`--no-voice` is a first-class output.** Music alone is a finished mix, and on the assembly
  film it was the only part that was ever praised.
- **The TTS cache means a re-mix costs nothing.** Takes are keyed by voice, rate and text, so
  changing the score does not re-fetch a single line, and a re-render needs no network at all.

## What is not checked

How it sounds. Sync, loudness, balance and pronunciation-by-duration are all measured; taste is
not, and this repo has no instrument for it. The narration on the assembly film passed every
measurement and was rejected twice — see
[`../../showoff/assembly/audio/AUDIO-LOG.md`](../../../showoff-render/examples/assembly/audio/AUDIO-LOG.md). Agree the voice before
rendering the whole thing: `--only 1,11,21,49 --audition <file>` cuts a four-line sample in any
voice in about twenty seconds.
