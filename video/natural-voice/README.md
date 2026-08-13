# Natural voice production

This is the default voice workflow for both films and future films. It captures the part that made the
warm education narrator convincing: natural performance and bandwidth preserved upstream, with almost
no downstream effects.

Reusable identities are in [`profiles/`](profiles/), and accepted/rejected acoustic experiments are in
[`EXPERIMENTS.md`](EXPERIMENTS.md). `audio_audit.py` produces non-destructive measurements for raw and
processed A/B files; it deliberately does not claim to score naturalness.

## The central finding

The approved education voice does **not** contain artificial echo, reverb, room tone, stereo reflections,
denoising, gating, compression or excitation. The prompt, generated takes and restored clips are mono;
the narration bus is dual-mono. Its acoustic realism comes from five things:

1. A voice prompt whose raw model output already sounds plausible.
2. Paragraph-level generation, so phrasing, coarticulation, pauses and sentence releases happen inside one
   performance.
3. Retaining quiet consonant releases, breaths and decays instead of silence-trimming them away.
4. Gated 24 → 48 kHz speech restoration, which returns plausible high-frequency air without being allowed
   to change the performance.
5. Very restrained EQ. Nothing tries to manufacture humanity after synthesis.

This distinction matters. The remaining imperfect joins in the education v2 cut are editing artifacts from
fitting narration into an already finished video. They are not part of the voice's acoustic quality.

## Audio first, video second

Use this order for new work:

1. Settle the words, pronunciations and intended emotional register.
2. Create or select the voice prompt.
3. Generate complete paragraphs or sections, with several seeded takes per section.
4. Transcribe every take and reject wrong words before judging style.
5. Select a coherent set by ear. Keep each selected section continuous.
6. Preserve the raw beginning, ending and internal silences. Do not split at sentence punctuation.
7. Run optional 48 kHz restoration and retain it only when it passes the performance gates.
8. Apply minimal corrective EQ and make one continuous narration master.
9. Lock that master. Derive caption timestamps and picture timing from the finished audio.
10. Add music and effects last, then master and mux with the picture stream copied unchanged.

The audio is the timing authority. A caption marks speech that already exists; it is not a box that speech
must be cut to fit.

## Voice-profile contract

Each reusable voice lives under `video/natural-voice/profiles/<voice-id>/` and contains:

| artifact | purpose |
|---|---|
| `prompt.wav` or an explicitly named prompt WAV | Immutable conditioning identity, lossless and unprocessed |
| `profile.json` | Model, prompt hash, acoustic measurements, baseline generation range and intended register |
| `prompt-selection.json` | Every prompt audition, transcript and selection measurement |
| `make_prompt.py` | Reproduction procedure and deterministic seeds |
| `README.md` | Voice-specific use, limits and listening notes |

Never overwrite a profile. A changed prompt, model or material conditioning change is a new profile version.
Do not normalize, denoise, gate, resample or lossy-encode a stored prompt.

For a new voice, audition the raw prompt before generating a film. It should already sound like a plausible
close spoken recording. A post-processing chain cannot rescue a prompt that sounds synthetic, distant,
phasey or noise-cancelled.

## Prompt selection

Use a neutral passage of roughly one or two natural breaths. It should contain statements, a mild question
or invitation, common consonant clusters and several vowel shapes. The text should express the target
relationship with the listener; the approved warm prompt speaks as a collaborator, not an announcer.

Generate at least four prompt candidates while varying expressiveness and guidance modestly. Record for
each candidate:

- random seed and every model argument;
- exact transcript and word-error rate;
- duration;
- median fundamental frequency and F0 interquartile range;
- prompt hash;
- a short human listening verdict.

Reject incorrect words first. Then reject theatrical, unstable or metronomic candidates. Pitch is a
consistency measurement, not a quality score: the correct voice may be high or low.

For a consented recorded speaker, use a lossless close-mic sample with no clipping, automatic gain control,
noise suppression, gate, music or overlapping voices. A quiet real room is fine; audible reverb is not a
substitute for good capture and may be exaggerated by cloning.

The approved synthetic warm profile is in [`profiles/warm-natural/`](profiles/warm-natural/). Its prompt
selection script and JSON are the exact worked example.

## Contextual generation

Generate paragraphs, not isolated caption lines. The proven Chatterbox range for the warm narrator was:

| setting | working range |
|---|---:|
| `exaggeration` | 0.32–0.40 |
| `cfg_weight` | 0.38–0.46 |
| `temperature` | 0.72–0.80 |

These are starting ranges, not universal targets. A new voice gets its own measured profile. Keep one model,
one prompt and one register across the project; vary seeds and nearby parameters, not narrator identity.

Use punctuation for delivery, but never change the settled displayed script to hide a generation problem.
Pronunciation aliases may be sent to the model if the original text and the mapping are both retained.

The preferred section length is whatever the model can deliver accurately in one coherent performance.
For this project, two to four sentences worked well. If a section is too long, split only at a genuine
paragraph or scene break and keep generous silence at that boundary.

## Ending and breath preservation

Do not use a fixed silence threshold such as `librosa.effects.split(..., top_db=40)` on deliverable speech.
It treats quiet releases and breaths as disposable. Do not cut at `last_recognized_word_end + 100 ms`; ASR
timestamps describe lexical content, not the end of the acoustic event.

The best policy is not to split continuous generated sections at all. If a section boundary must be trimmed:

- inspect the waveform and listen at headphones volume;
- keep the model's full post-speech output unless it contains an actual artifact;
- keep at least several hundred milliseconds after the last lexical word;
- place a short click-prevention fade only after the retained decay;
- add digital silence after the fade, never in place of a natural tail;
- never time-compress the retained breath just to fit a caption box.

The education v2 rescue retained 0.44–1.235 s after lexical endings, with a 0.68 s median, then used a 12 ms
landing fade and 160 ms quiet post-roll. Those values document the repair, not the preferred future method;
continuous audio avoids the cut entirely.

## Bandwidth restoration

Chatterbox 0.1.7 produces 24 kHz audio, so the native Nyquist limit is 12 kHz. The missing upper octave can
read like a noise-cancelling headset even when the performance is excellent.

The proven restoration model is `MossFormer2_SR_48K` through ClearVoice. Run it per continuous section and
compare it with a clean 48 kHz resample of the original. Restoration is accepted only when all gates pass:

- transcript word-error rate ≤ 0.12;
- duration change ≤ 1.2% + 50 ms;
- median F0 change ≤ 5 Hz;
- measurable energy appears above 12 kHz.

If any gate fails—or the result sounds phasey, papery or less human—ship the clean resample. Education v2
accepted restoration on 36 of 49 edited cues and fell back on 13; preserving the performance took priority
over uniform processing.

The checkpoint path and SHA-256 belong in each production report. Do not put downloaded checkpoints under
Git LFS; keep them in the ignored `checkpoints/` tree.

## Corrective EQ

Start flat and make only evidence-based changes. The approved warm-narrator chain was:

| stage | setting | purpose |
|---|---|---|
| high-pass | 45 Hz | Remove non-speech sub-bass |
| low body | +1.7 dB at 115 Hz, Q 0.9 | Restore gentle close-mic weight |
| boxiness | −0.5 dB at 900 Hz, Q 1.1 | Tiny nasal/boxy correction |
| presence | +1.2 dB at 4 kHz, Q 1.0 | Speech clarity |
| air | +1.8 dB shelf at 10 kHz | Modest openness after restoration |

This curve is profile-specific. Use it as a restrained scale reference, not a preset to paste onto every
speaker. Match perceived level before comparing EQ variants; louder almost always sounds superficially
better.

Avoid by default:

- denoisers and noise-cancelling speech enhancement;
- hard gates;
- exciters;
- synthetic breaths;
- pitch drift or chorus;
- audible saturation;
- per-line peak normalization;
- short room impulse responses or discrete echo taps;
- compressors added merely to sound “broadcast.”

Compression is permitted only to solve a measured dynamic-range problem, with a bypassed loudness-matched
A/B. It was not used on the approved education voice.

## Mixing

Keep the narration stable and let the arrangement make space. Fast voice-triggered ducking exposes every
phrase boundary and can sound like another voice artifact. The approved education mix used constant music
level with no sidechain or ducking: voice at −16 LUFS per cue, music at −29.5 LUFS, and a −14 LUFS / −1 dBTP
master target. Its measured result was −14.59 LUFS and −0.99 dBTP.

Those levels are project values, not universal law. Preserve the relationship: speech clearly leads, music
does not pump, and final limiting does not flatten consonants or tails.

## QA and listening gates

Automation catches correctness; ears accept realism. For each new voice and production:

1. Transcribe the raw take and the processed take.
2. Measure duration and F0 before and after restoration.
3. Inspect the final word, breath and decay of every section.
4. Loudness-match raw, restored and EQ variants before listening.
5. Listen on headphones for phase, echo, pumping and chopped air.
6. Listen on laptop speakers for intelligibility and excessive low body.
7. Audition the opening, densest technical passage, longest sentence and ending before full rendering.
8. Keep every rejected treatment and its verdict in the film's audio log.

Do not let a metric overrule an audible failure. This repository has rejected word-perfect, loudness-correct
voices because they still sounded synthetic.

## Failed approaches that must not return silently

The legacy [`voice_chain.py`](../engine/voice_chain.py) added de-essing, chest/presence EQ, compression, saturation,
micro-pitch drift, synthetic breaths and a stereo room impulse. Its outputs were rejected as more artificial.

The showoff v7.3 experiment added room tone, 17/29/43 ms early-reflection taps and soft-knee compression.
It was rejected as “a robot with echoes.” The exact experiment and verdict are preserved in
[`../showoff/assembly/audio/VOICE-LOG.md`](../showoff/assembly/audio/VOICE-LOG.md).

The lesson is not that all rooms or compressors are forbidden. It is that acoustic realism must already be
present in the performance. Effects are allowed only as answers to a specific audible problem, and every
effect needs a loudness-matched bypass test.

## Provenance checklist

Every finished narration must preserve:

- settled script and pronunciation-map hashes;
- model and package versions;
- prompt WAV, prompt hash and prompt-selection record;
- generation seeds and parameters;
- selected raw continuous takes;
- ASR and pitch QA;
- restoration checkpoint hash and per-section accept/fallback decisions;
- exact EQ, level and mastering settings;
- final narration WAV before music;
- full mix and final decode report;
- rejected variants and human verdicts.

If those artifacts exist, the voice is reusable. If only the final mixed video exists, it is not.
