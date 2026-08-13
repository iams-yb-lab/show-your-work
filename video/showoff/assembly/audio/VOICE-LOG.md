# Voice log — narration for assembly_purple_v2.mp4

Session of 2026-08-12, evening. Lives in temp until a cut is approved, then merges into
`PCB/render/AUDIO-LOG.md`. The repo is untouched meanwhile (Codex is running its own session in it).
This log is deliberately detailed end-to-end so the whole pipeline can be re-run or extended
without this conversation.

## Ground rules carried over from AUDIO-LOG.md

- Music (`cinematic_score.wav`, 84 s stereo 48 kHz, −14 LUFS, in the temp media dir) is the one
  approved element. Never regenerate it.
- Picture is `PCB/render/out/anim/assembly_purple_v2.mp4` (84.000 s, 2520 frames @ 30 fps). Every
  mux is `-c:v copy`; verify with `ffmpeg -i f.mp4 -map 0:v -c copy -f md5 -` on both files —
  they must match (they have on every cut: `155474b62f81f7315a766d44496a8551`).
- No cloning of real people's voices. No heavy "humanising" DSP on the voice — that chain is what
  got the edge-tts cuts rejected. Static gain only.
- The bench for audio is the student's ears. Every measurement below passed on cuts that were
  still rejected; measurements gate *correctness*, not *quality*.

## Working directories

| path | contents |
|---|---|
| `%TEMP%\temperature-controller-media\` | all deliverables, previews, this log |
| `%TEMP%\temperature-controller-media\{chatterbox,chatterbox_deep,kokoro,editx}\` | per-engine takes + `manifest.json` |
| `%TEMP%\chatterbox-venv\` | Python 3.12 venv: chatterbox-tts + kokoro + CUDA torch 2.6.0+cu124 |
| `%TEMP%\editx-venv\` | copy of the above with transformers==4.53.3 (breaks chatterbox in *this copy only*), + onnxruntime, openai-whisper |
| `%TEMP%\editx-node\` | clone of github.com/Saganaki22/ComfyUI-Step_Audio_EditX_TTS — `step_audio_impl/` inside it is a standalone, ComfyUI-free inference engine |
| `%TEMP%\editx-models\` | HF snapshots of stepfun-ai/Step-Audio-Tokenizer + Step-Audio-EditX, 9.1 GB |
| Claude scratchpad `...\29c5ea58...\scratchpad\` | all scripts: `gen_narration.py`, `gen_deep.py`, `gen_kokoro.py`, `gen_prompt.py`, `editx_gen.py`, `mix_final.py` |

## The script (six lines, timed to the film's own schedule)

Placements 1/3/4/6 were recovered from the first draft's narration master via
`ffmpeg -af silencedetect=n=-45dB:d=1.5`; 2 and 5 were added on request ("slightly more").
Film anchors: first part sets off f880 = 29.3 s, ADC lands f1720 = 57.3 s, Teensy f2140 = 71.3 s,
music-only fade from ~81.4 s.

| # | start | line | anchor |
|---|---|---|---|
| 1 | 2.23 s | "It all begins with a bare board... and an idea precise enough to become real." | bare board |
| 2 | 14.50 s | "A thousandth of a degree... that is the promise written into every trace." | the 1 mK spec |
| 3 | 28.70 s | "Then, piece by piece, purpose takes form." | parts set off |
| 4 | 46.73 s | "Power. Sensing. Control. Every component answers the same demand." | mid-assembly |
| 5 | 57.80 s | "And at its heart — a sentinel, listening for the faintest whisper of heat." | ADC landing |
| 6 | 72.72 s | "Until the instrument stands complete... ready to master the invisible frontier between heat... and control." | Teensy landed → fade |

Constraint: line 6 must end by ~82.5 s (fade is music-only; a narrator faded mid-sentence was
fault #4 of the previous sessions). Cap enforced in every generator: 9.6 s.

## Attempts, verdicts, and why

| cut | engine / voice | how | verdict |
|---|---|---|---|
| v1–v2 (prev. sessions) | edge-tts Christopher/Andrew + humanising DSP chain | network TTS, then de-ess/chest/room/breath synthesis | rejected: "very AI", "so ASS" |
| v3 | Chatterbox (Resemble, 0.5B, local GPU), built-in voice, no post | 6 takes/line grid over exaggeration×cfg | **natural but wrong voice** — not deep (median F0 118 Hz) |
| deep-clone experiment | Chatterbox cloned onto its own voice pitch-shifted −3.5 st (`chatterbox_deep/`) | librosa pitch_shift made the reference; audio_prompt_path cloning | deep (89–104 Hz) but F0 wanders line-to-line — reads as an inconsistent narrator; parked |
| v4 | Kokoro-82M `am_onyx` preset, 0.85–0.95× speed, 6 lines | 4 takes/line; one voice forced after mixed-voice selection bug | deep + consistent (86–90 Hz) but "a little AI" — too clean, metronomic |
| v5 (in progress) | **Step-Audio-EditX (StepFun, 3B)** cloning the onyx timbre + model-generated breaths | see below | — |

## Research that picked v5's approach

Detection literature: what flags TTS is **regularity** — longer runs between pauses, low variance
in segment length, missing micro/macropauses and breaths; prosodic flatness second. (JMIR pause-
pattern study PMC11041410; Hume's perceptual-cue writeup; arXiv 2602.20061.)

Open-weight standings (Artificial Analysis Speech Arena, July 2026): Step-Audio-EditX 1118 ·
Fish S2 Pro 1110 · Voxtral TTS 1077 · Kokoro 1060 · Maya1 1053. v4's engine was mid-pack.
Step-Audio-EditX chosen because: highest Elo; 3B bf16 ≈ 12 GB fits the 4080 SUPER unquantized;
plain transformers/sdpa path works on Windows (proven by the ComfyUI port); and its RL-trained
*editing* adds paralinguistics ([breath], [inhale], [sigh]) — human irregularity generated by the
model, not bolted on by DSP. Fish S2 Pro needs 24 GB or 4-bit + SGLang (Linux-y); Voxtral needs
vLLM Omni (no Windows).

## v5 pipeline and its pitfalls

Moved to [`editx-pipeline-reference.md`](editx-pipeline-reference.md) when this log hit its size
ceiling: the EditX install recipe, the clone/edit API, the mix chain and the eight pitfalls. **v8
does not use EditX**, so none of it is live; it is kept because v7.2 is still the approved cut.

## Measurements so far

- Chatterbox default voice median F0 117.6 Hz; deep-shift reference 96.6 Hz; deep-clone takes
  89–104 Hz; Kokoro am_onyx 86–90 Hz across all lines and speeds (the consistency winner).
- All shipped takes in v3 and v4: Whisper WER 0.000.
- v3 mix −14.67 LUFS; v4 mix −15.31 LUFS (linear loudnorm ran out of true-peak headroom; the
  0.6 dB shortfall was accepted rather than adding another limiter stage).

## v5 result (2026-08-12, delivered for judgment)

- All 24 clone takes rendered; verification rejected two takes on wrong words ("Tower" for
  "Power", "when" for "and") — the first attempt where takes actually failed WER, worth knowing.
- Breath edits **won on all three ellipsis lines** (1, 2, 6): still WER 0.000, F0 80–89 Hz,
  durations inside slots. Lines 3/4/5 ship as plain clones (80–91 Hz).
- Chosen line durations: 4.39 / 4.73 / 3.58 / 5.20 / 4.49 / 6.84 s. Line 6 ends at 79.6 s, clear
  of the fade.
- Mix −15.50 LUFS / −1 dBTP (same TP-limited shortfall as v4, accepted). Video stream
  MD5-identical: `155474b62f81f7315a766d44496a8551`.
- Deliverable: `assembly_purple_v2_epic_v5.mp4` + `preview_v5_opening.m4a` / `preview_v5_ending.m4a`.
- EditX clone loudness varies wildly per take (−30 to −17 LUFS integrated) — the per-line static
  gain stage is load-bearing here, more than it was for Kokoro.

## v6: the "crappy microphone" diagnosis and the pulse collisions (2026-08-12, late)

The student identified v5's remaining tell precisely: not the voice or the pacing, but the *sound*
— "like a noise-cancelling mic". Root cause is bandwidth: **every engine used so far outputs
24 kHz**, i.e. nothing above 12 kHz. Studio narration carries "air" to 16–20 kHz; its absence is
exactly the cheap-mic signature. The prosody work survives; the fix is restoration, not
regeneration.

- **Fix 1 — speech super-resolution** (`sr_lines.py`, `%TEMP%\sr-venv` = another chatterbox-venv
  copy + `pip install clearvoice`): MossFormer2_SR_48K (ClearerVoice-Studio, Alibaba) upsamples
  the six chosen lines 24 → 48 kHz, reconstructing the highs. Chosen over Resemble-Enhance
  (DeepSpeed dependency — bad on Windows) and AudioSR (diffusion, slower, noise-sensitive).
  Gates per line: WER ≤ 0.05, duration within 1 %, median F0 within 3 Hz, and measured energy
  above 12 kHz must actually appear. A failed gate ships the 24 kHz original for that line.
- **Fix 2 — voice vs. score pulses.** Second observation: lines were starting on top of the
  music's pulses. Checkable against the score's own grid — the bar is exactly 70 frames
  (2.3333 s), and lines 1/4 began within 0.1 s of downbeats (2.23 vs 2.333; 46.73 vs 46.667),
  line 6 within 0.4 s. Nudged into the post-pulse gap: **1 → 2.85 s, 4 → 47.25 s, 6 → 72.95 s**
  (applied in `editx_sr/manifest.json`; visual anchors move ≤ 0.6 s, tolerable). And the duck is
  now **pre-emptive**: `mix_final.py` builds a second narration bus advanced 0.35 s that drives
  the sidechain (thr 0.015, ratio 10, atk 80 ms, rel 1000 ms), so the bed is already down when
  the voice enters. Line 6 now ends ≈ 79.8 s — still clear of the fade.

## The dinner-window exploration (2026-08-12, ~19:30–20:10)

Student's brief before leaving: render variants, tweak settings, decide together after; the
bandwidth treatment "might be the most important part"; voice should also be calmer and slower.

**Slower pass** (`editx_slow.py`, EditX `speed: slower` — model retiming, not a stretch): lines
1/2/5 accepted (+2–4 % duration, natural); line 3 came back *shorter* (rejected), line 4 came back
at 64 Hz median (voice broke character — rejected), line 6 said "till" for "until" (WER gate —
rejected). Gates > seeds: rejected lines keep their good takes. SR re-ran clean on the slowed set
(F0 gate relaxed 3 → 5 Hz; line 2's 3.0 Hz delta was a threshold graze, not an artifact).

**The candidate matrix** (all: deep EditX voice, breaths, shifted starts, pre-emptive duck,
48 kHz SR unless noted; all MD5-identical picture):

| file (assembly_purple_v2_epic_…) | pace | bandwidth treatment |
|---|---|---|
| `v6.mp4` | slower (1/2/5) | MossFormer2 SR only |
| `v6e_eq.mp4` | slower | SR + condenser EQ (HP 50 Hz, +2 dB @110, +1.5 dB @4k, +3 dB shelf @10k) |
| `v6f_exciter.mp4` | slower | SR + aexciter (drive 6, amount 1.5, 7.5–16 kHz) |
| `v6d_original_pace.mp4` | v5 pace | MossFormer2 SR only |
| `v6b_story.mp4` (rendering) | original | EditX `style: story` then SR |
| `v6c_gentle.mp4` (queued) | slower | EditX `style: gentle` then SR |
| — B4 AudioSR | — | **skipped**: pins an old numpy that won't build on py 3.12 |

Mixes land at −15.1 LUFS ±0.1. `mix_final.py` now takes an optional third arg: a per-line voice
filter chain (how the EQ/exciter variants are made).

All six candidates rendered and MD5-verified; previews and `COMPARE.md` in the media dir.
Style-pass notes: `story` fell back on lines 2/6 (pitch rose past 105 Hz — no longer our
narrator); `gentle` fell back on line 6 (same reason), and its SR pass kept lines 2/5 at 24 kHz
(gate failures) — v6c is the one uneven candidate. The F0 identity gate (70–105 Hz) is doing the
work of keeping one narrator across every edit; the style edits are where it earns its keep.

## v7 — the consistency correction (2026-08-12, post-dinner)

🔴 **The six-candidate matrix was rejected on sight: the narrator changes character between
lines inside one video.** Root cause is a selection bug of philosophy, not code: every generator
picked each line's take *independently* (duration fit, per-line gates), and mixing edit kinds
per line (slowed 1/2/5 beside unslowed 3/4/6; styled lines beside fallbacks) guaranteed
line-to-line mood swings. Per-line optimization trades away exactly what a narrator is.
**Select for the narrator, not the line.**

- `consistency_select.py`: features per take = median F0 (register), F0 IQR
  (expressiveness — "excited vs calm" is largely this), spectral centroid (brightness). Joint
  selection minimizes distance to the pool median, register weighted 2×, with an
  excess-expressiveness penalty. Cross-line F0 spread went **6.5 Hz → 2.2 Hz (83.1–85.3 Hz)**;
  all six from the same plain-clone generation, no per-line edit mixing.
- **Ducking removed entirely** on the student's direction: the score runs untouched and the
  voice sits on top (per-line target raised −16 → −13.5 LUFS; sidechain bypassed). The
  pulse-gap start shifts stay.
- v7 = consistent takes + 48 kHz SR + condenser EQ + no duck. −15.1 LUFS, picture MD5-identical.
- Deliverable: `assembly_purple_v2_epic_v7.mp4` + `preview_v7_opening/ending.m4a`.

## v7.1 — v7 approved ("VERY VERY NICE"), three refinements (2026-08-12, night)

1. **Voice 7 % slower** — not regenerated: `atempo=0.93` on the very takes the student approved
   (a model "slower" edit would have produced new takes and re-rolled the narrator's character;
   the WSOLA stretch at 7 % keeps the exact performances, just unhurried).
2. **Line 5 moved 57.8 → 58.9 s.** It was entering during the ADC bell's bloom (the bar-12
   structural bell strikes at exactly 57.3 s).
3. **The 1:10 bass pulse now strikes at 1:11.** Measured, not guessed: low-band (<150 Hz)
   envelope showed a 13 dB step at 69.7 s decaying through 72 s — the Teensy hero's landing
   bloom, arriving 1.6 s before the seat. First attempt assumed it was the `cine` variant's sub
   swell and reconstructed it analytically — correlation 0.001, **aborted by its own guard: the
   score is not the cine bed**. Second approach (`move_pulse.py`): complementary band split at
   240 Hz (low = zero-phase FFT lowpass, high = residual, recombination exact), lift the pulse
   segment [69.68, 72.28), patch the hole with adjacent steady-pedal bed, set the pulse down
   +1.30 s with 50 ms raised-cosine seams. Verified: bed flat −23.8 dB through 70.5 s, strike at
   71.0 s, peak 71.25 s — beside the Teensy bell at 71.3, so the bass now underlines the seat.
   Original `cinematic_score.wav` untouched; the edit lives in `cinematic_score_v2.wav`.
- v7.1 = v7's narrator + the three fixes. −14.9 LUFS, no ducking, picture MD5-identical.
- Deliverable: `assembly_purple_v2_epic_v7_1.mp4`; previews `preview_v7_1_opening.m4a`,
  `preview_v7_1_pulse_region.m4a` (54–76 s: line 5 entry + moved pulse).

## v7.2 — line 1 alone still fast (2026-08-12, night)

v7.1 verdict: good except line 1. Its chosen take was a brisk read to begin with (4.41 s, the
pool's shorter side) and it hurries through the ellipsis — the global 7 % stretch can't add a
pause the performance never made. Fix per the standing surgical recipe (`gen_line1_slow.py`):
8 fresh clone takes of line 1 only, gated to the approved narrator (WER 0, F0 82–86.5 Hz,
IQR ≤ 14) **plus an unhurried-delivery gate** (duration 4.8–7.5 s pre-stretch), selected for the
longest internal pause at the ellipsis. Winner replaces `editx_consistent/line1_best.wav`
(previous kept as `line1_best_v71.wav`), then SR → remix as v7.2. Lines 2–6: untouched.

**Result:** all 8 re-takes were word-perfect but none passed the ≥4.8 s duration gate — the
clone inherits the prompt's pace, so this line simply doesn't come out longer. Take 1 missed
the gate by 4 ms of rounding and was otherwise the best line-1 take of the whole project
(IQR 8.9 = calmest, 84.1 Hz, real 363 ms pause at the ellipsis). Shipped it with a **per-line
stretch**: line 1 at `atempo=0.90`, lines 2–6 stay at 0.93 (`mix_final.py` now honors a
`VOICE_FX_<n>` env override). Line 1 spoken duration 4.74 → 5.33 s. `sr_lines.py`'s override
map now carries line 5 → 58.9 s so re-runs don't lose the pulse-gap shift. One curiosity for
the record: Whisper appends "// // //" when transcribing the SR'd line-1 tail — hallucination
on the low-level noise floor, duration confirms no extra audio.

## v7.3 — the last "noise-cancelled" residue: the voice was anechoic (2026-08-12, late night)

v7.2 verdict: "PHENOMENAL", one residue — the voice still faintly reads noise-cancelled. The
remaining cause isn't bandwidth (fixed in v6) but **acoustics: the voice existed in no room.**
Generated speech sits in digital silence — zero noise floor, zero reflections — and daily-life
voices never do. VO-engineering practice confirms three standard fixes, all now in `mix_final.py`:

1. **Room tone**: constant band-limited (150 Hz–8 kHz) pink bed at **−56 dB** under the whole
   mix (`ROOM_TONE_DB` env), so silence is a quiet room, not a void.
2. **Early reflections only**: three taps at 17/29/43 ms, decays 0.16/0.11/0.07 — the
   close-intimate end of reverb, no audible tail.
3. **Soft-knee compression** (thr −18 dB, ratio 2.5, knee 6): the broadcast density that
   removes the raw synthetic dynamic signature.

Balance was re-matched to the approved v7.2 by measurement, which took three mixes: 🔴
**ffmpeg's `acompressor` `makeup` is a linear factor, not dB** — makeup=4 meant +12 dB and blew
the premix to −11.5 LUFS. Two-point interpolation put makeup=2 (+6 dB) at premix −16.84 LUFS vs
v7.2's −16.27 — voice/music ratio preserved within 0.6 dB. Final −14.4 LUFS, picture
MD5-identical. Deliverable: `assembly_purple_v2_epic_v7_3.mp4` + opening/pulse-region previews.

Sources: SilentCut on AI-voice sterility & the −50/−60 dB ambience bed; Pro Audio Files on
ER-vs-tail reverb distance cues; musehub on parallel/soft compression for natural vocals.

🔴 **v7.3 REJECTED: "sounds like a robot with echos" — v7.2 is much better.** The early
reflections were the mistake: on an already-synthetic voice, discrete echo taps read as
*effect*, not *room*. The lesson to carry forward: **v7.2's dryness was never the problem worth
solving.** Room tone alone (untested in isolation) might have been fine; the ER taps killed it.
This rhymes with the project's oldest audio lesson — the edge-tts humanising chain was also
rejected. Post-processing toward "human" has now failed twice; don't propose it a third time.

## FINAL VERDICT — v7.2 is the approved cut (2026-08-12, end of session)

**`assembly_purple_v2_epic_v7_2.mp4` in `%TEMP%\temperature-controller-media\`. No more
rendering, by instruction.**

What v7.2 is, in one place:
- **Picture**: `PCB/render/out/anim/assembly_purple_v2.mp4`, video stream MD5
  `155474b62f81f7315a766d44496a8551`, muxed `-c:v copy` (verified identical).
- **Voice**: Step-Audio-EditX (3B, local GPU) cloning `onyx_prompt.wav` (Kokoro am_onyx reading
  a neutral passage — synthetic speaker, no real person). Six lines, jointly selected for one
  narrator (median F0 83.1–85.3 Hz, 2.2 Hz spread; take pool in `editx/`), line 1 re-taken for
  the ellipsis pause (363 ms). All takes Whisper-verified word-perfect.
- **Bandwidth**: MossFormer2_SR_48K super-resolution 24 → 48 kHz on every line.
- **Pace**: `atempo=0.90` line 1, `0.93` lines 2–6, applied in the mix.
- **Placement**: 2.85 / 14.5 / 28.7 / 47.25 / 58.9 / 72.95 s (starts sit in the pulse gaps;
  line 5 clears the 57.3 s ADC bell).
- **Score**: `cinematic_score_v2.wav` — the original with the Teensy landing bloom moved
  69.7 → 71.0 s (band-split surgical edit; original WAV untouched). **No ducking.**
- **Voice FX (the approved chain, nothing more)**: highpass 50 Hz, +2 dB @ 110 Hz,
  +1.5 dB @ 4 kHz, +3 dB shelf @ 10 kHz. No compression, no echo, no room tone.
- Exact remix command: see `pipeline/` note below; premix −16.27 → −14.84 LUFS final.

## v8 — the natural-voice method applied, and the engine leaves (2026-08-13)

v7.2 stood for a day. v8 rebuilds the narration under
[`natural-voice/README.md`](../../../natural-voice/README.md), and the engine did not survive the
process. **Step-Audio-EditX is no longer in this film.**

**What v7.2 was doing wrong, by the method's standard.** Two things, both upstream. Every take was
cut with `librosa.effects.split(top_db=40)` and a 60 ms pad *before* it was written, so releases
and breaths were destroyed before anything downstream could keep them, and the raw was never saved
— `EXPERIMENTS.md` lists that exact operation as rejected. And pace was set downstream with
`atempo=0.90/0.93`.

**Moving pace upstream failed.** Slowing the conditioning prompt 0.88 → 0.78 left clone pace
unchanged (line 1 mean spoken 4.62 s vs 4.46 s, n=3) and widened take-to-take F0 spread from
2–3 Hz to 8 Hz. VOICE-LOG's "the clone inherits the prompt's pace" was an explanation for line 1's
stubbornness, not a property that holds.

🔴 **Every audition file was delivered clipped, and two rounds of listening were wasted on them.**
Loudness matching by `gain = target − integrated_LUFS` with no headroom check drove peaks to +0.6…
+3.0 dBFS, then AAC smeared them. The verdict — *"the tone is completely fine, but the acoustic
effect is so much worse"* — is the sound of clipping. One of the ruined comparisons was a ladder
whose rungs were clipped by *unequal* amounts, so it was not even a fair test. Fixed in
`natural-v8/compare_lib.py`: the common level is derived from the material, and delivery is
lossless. The clipped files are kept under `out/showoff/natural-v8/_clipped_invalid/`.

🔑 **The raw prompt beat every processed descendant of itself.** Once the comparison was rebuilt
clean, the ranking held: Kokoro `am_onyx` speaking directly beat the EditX clone of it, the clone
plus restoration, and the clone plus restoration and EQ. The 3B model kept the timbre and threw
away the pace — Kokoro reads 43–55 % slower than its own clone. **Auditioning a prompt says nothing
about what an engine conditioned on it will produce.**

**v8, in one place:**
- **Voice**: Kokoro-82M `am_onyx`, speed 0.78, generated directly. Profile:
  [`deep-onyx-slow/`](../../../natural-voice/profiles/deep-onyx-slow/). All 24 takes word-perfect;
  cross-line F0 83.6–88.3 Hz, spread 4.7 Hz, with no consistency selection needed.
- **Endings preserved**: 0.26–0.32 s lead-in and 0.84–1.01 s tail on every line, against v7.2's
  0.06 s. Lines are placed by subtracting the measured lead-in from the anchor, so first words land
  on the same frames while the files keep both ends.
- **No `atempo`** anywhere — the read is unhurried at the source.
- **Bandwidth**: MossFormer2_SR_48K passed its gates on all six lines, WER 0.000, pitch ≤ 3 Hz.
- **EQ**: high-pass 45 Hz and nothing else. The warm curve is profile-specific; v7.2's is a
  different voice's, and its literal filter string was never written down anyway.
- **Placement** unchanged from v7.2: 2.85 / 14.5 / 28.7 / 47.25 / 58.9 / 72.95 s. Line 6 ends at
  81.60 s including its full tail, inside the 82.5 s limit.
- **Score**: `cinematic_score_v2.wav`, no ducking. Master −14.96 LUFS / −1.00 dBTP against v7.2's
  −14.84. Picture MD5 `155474b62f81f7315a766d44496a8551`, verified identical.
- ⚠ The final `alimiter` does ~4.8 dB of peak reduction on the voice bus. Removing it entirely
  costs 6.4 dB of loudness (master would land at −21.23 LUFS), so it stays — the same chain v7.2
  used and was approved with.
- Deliverable: `out/showoff/anim/assembly_purple_v2_epic_v8.mp4`, previews
  `preview_v8_{opening,middle,ending}.wav`. **Unlistened-to by me.**

## Handover — pick up exactly here

1. **v8 is rendered and unjudged; v7.2 remains the approved cut until it is not.** Both are in
   `out/showoff/anim/`. v8's previews are in `out/showoff/natural-v8/`.
2. **v8 rebuilds in four commands**, all in `natural-v8/` and all pointing at repo paths:
   `generate_v8_kokoro.py` → `finish_v8.py` (restore, master, mux). `compare_lib.py` packages
   anything meant for listening; use it rather than hand-rolling gain, which is what clipped two
   rounds of auditions.
3. **If the pace needs to move, it is 0.76 or 0.80** — one step off the selected profile, never a
   fresh sweep. See [`deep-onyx-slow/README.md`](../../../natural-voice/profiles/deep-onyx-slow/README.md).
4. Environments: `sr-venv` (kokoro + clearvoice + whisper) is all v8 needs. `editx-venv` and
   `editx-models` (9.1 GB) are only for reproducing v7.2 and can go once v8 is approved.
5. ⚠ **The 13 scripts in `pipeline/` still point at `%TEMP%\temperature-controller-media\` and
   `PCB\render\`, both dead since session 58.** They made v7.2 and are kept as its record; they
   will not run as-is. `natural-v8/` supersedes them for new work.
