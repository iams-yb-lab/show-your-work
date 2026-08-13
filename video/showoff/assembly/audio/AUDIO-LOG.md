# Audio log

The soundtrack work for `../../../out/showoff/anim/assembly_purple_v2.mp4`. Self-contained: this plus the tool
docstrings is everything. The film's picture is in [`RENDER-LOG.md`](../RENDER-LOG.md).

## Where it stands

**v7.2 is approved** (2026-08-12) — `../../../out/showoff/anim/assembly_purple_v2_epic_v7_2.mp4`. The
music was praised in the first round and never criticised since. **Ten attempts at the narration
were rejected before it.** The recipe that worked, and the full session-by-session record, is in
[`VOICE-LOG.md`](VOICE-LOG.md); the generalised method is
[`../../../natural-voice/README.md`](../../../natural-voice/README.md).

## The ten rejections, and what they had in common

| what was tried | verdict |
|---|---|
| synthesised per-landing sound effects | "the sound effects sound weird" |
| cloud TTS narrator, clean | "the narration sounds very AI" |
| the same voice + de-ess, chest, presence, compress, saturate, drift, room IR, breaths | "so ASS" |
| the script rewritten, voice unchanged | the objection was never the words |
| local model, built-in voice, no processing | "natural but wrong voice" — median F0 118 Hz |
| that voice cloned onto a pitch-shifted copy of itself | register wandered 15 Hz line to line |
| a different local model with a natively deep voice | "a little AI" — too clean, metronomic |
| a 3B model picked on leaderboard Elo, with model-made breaths | "like a noise-cancelling mic" |
| six candidate renders offered for the student to pick from | "the narrator changes character between lines" |
| room tone + 17/29/43 ms reflections + soft-knee compression on the approved cut | "sounds like a robot with echos" |

🔴 **Seven of the ten shared one premise: take a synthetic performance and add the missing human
qualities downstream.** That failed as attempt 3 and was proposed again as attempt 10 with the
first failure already on record. Acoustic realism has to be in the performance; nothing downstream
puts it there.

🔴 **The decisive fault went unmeasured for three engines.** Every one output 24 kHz — nothing above
12 kHz, which is the cheap-microphone signature — and the pipeline never checked bandwidth. The
student heard it and named it. So did the narration landing on the score's own downbeats, which was
checkable against a grid this repo authored.

🔴 **Per-line optimisation destroyed the narrator.** Selecting each line's best take by duration and
gate pass mixed slowed with unslowed, styled with fallback, and once put two different voices in one
film. Select for the narrator, not the line.

**A human reading [`narration-assembly-v2.md`](../script/narration-assembly-v2.md) was always
available** — the pipeline takes a WAV per line and does not care where it came from. It was written
down only after two rounds had been thrown away and ~25 GB of models installed. Offer it first.

## The tools

`audio_cues.py` is here; the rest are the shared engine in `../../../engine/`. All numpy and the standard library, none of them needing the board.

| tool | what it does |
|---|---|
| `audio_cues.py` | imports `animate_assembly_v2`, re-runs its schedule, writes every cue as a frame number |
| `mix_audio.py` | synthesises music and effects; `--no-sfx` for music only, `--voice` to place narration |
| `narrate.py` | speaks the narration table, applies the voice chain, one WAV per line |
| `voice_chain.py` | de-ess, chest, presence, compress, saturate, drift, room, breath |
| `dsp.py` | the primitives all of them share |
| `check_score.py` | measures the finished audio back out, with tools that never saw the cue sheet |

```bash
blender --background --factory-startup --python audio_cues.py -- --out ../../../out/showoff/audio/cues.json
python ../../../engine/mix_audio.py --variant cold --no-sfx --out ../../../out/showoff/audio/music.wav
python ../../../engine/check_score.py --wav ../../../out/showoff/audio/music.wav
```

## What the design actually rests on

- **The tempo is a schedule number, not a taste.** The first part sets off on f880, the ADC lands
  on f1720 and the Teensy on f2140 — exactly 28.0 s and then 14.0 s — so a bar of **exactly 70
  frames** (102.857 BPM) puts both hero landings on downbeats with no tempo map and no drift.
  `BAR_FRAMES` is the only place the tempo exists.
- **One pitch set, sixth degree absent.** D E F G A C, so the mode commits to neither major nor
  minor. Every pitch in the film is drawn from it, including the effects, and a D pedal runs
  unbroken from first frame to last — the film is about holding something still.
- **Nothing is placed by ear.** A cue's time is `(frame − 1) / 30` where the frame came from the
  animation's own tables, so retiming the film moves the audio with it.
- **`-c:v copy` for the mux.** The video stream comes out MD5-identical to the original, so audio
  can be re-cut any number of times without ever re-encoding a frame.

## Faults found by measuring, and one class of fault that measurement missed

1. A boxcar limiter diluted the 2 ms component clicks sixfold; 5015 samples clipped and the
   true-peak pull-down cost 2.25 dB. Fixed with an exact sliding maximum (van Herk).
2. D1 at 36.7 Hz held **81 %** of the mix's energy — inaudible on any speaker, but it owned the
   peaks, so the limiter spent its range on sub. A-weight before believing a band split; raw power
   spectra always over-report bass.
3. The onset checker's first run reported 6.7 ms of systematic lateness that was **its own STFT
   window offset**. The tool was wrong, not the mix.
4. The master fade began at 81.4 s while the last narration line ran to 83.25 — the narrator was
   faded out inside the one sentence carrying the 1 mK spec. Fades belong to the music alone.
5. `narrate.py` did not own its output directory and the mixer globs it, so five superseded lines
   survived a retiming: a mix with **sixteen** lines in it instead of eleven, the narrator talking
   over himself. It now clears the directory and reports how many it cleared.

🔴 **And the one that matters most.** Every measurement passed on the cuts that were rejected:
sync held at **1.3 ms median over all 110 landings**, loudness at **−14.0 LUFS / −1.0 dBTP**,
narration **+17.1 dB in front** of the music in the speech band. None of that is evidence that
something sounds good. There is no instrument in this repo for that, and the sessions that
produced these files could not hear them — which is exactly why the approach should have been
agreed before the second and third renders, not after.

## Provenance

Everything was generated on the desktop except one thing.

- **Music, effects, room, breaths, loudness metering, limiting** — synthesised in numpy here. No
  samples, no library music, no impulse responses, nothing downloaded. The BS.1770-4 gated meter
  and the 4× oversampled true-peak limiter are in `dsp.py` and `mix_audio.py`.
- 🔴 **The narrator's voice was not local.** `narrate.py` sends the line *text* to Microsoft's
  neural TTS over the network via the `edge-tts` package (`en-US-AndrewMultilingualNeural`, and
  `en-GB-RyanNeural` in the first pass). No audio was uploaded and no account or key is involved,
  but eleven lines of this project's text did leave the machine.
- **ffmpeg is installed but not on PATH** on the desktop, so it looks absent to `which`. See
  `narrate.py`'s `find_ffmpeg`. It is used only to decode the returned MP3 and to mux.
