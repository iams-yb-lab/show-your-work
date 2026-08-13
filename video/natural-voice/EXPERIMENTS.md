# Natural-voice experiments

This log is for voice-agnostic acoustic work. Film-specific take selection stays with the film; reusable
findings belong here.

## Accepted baseline

The warm education narrator proves that convincing acoustic speech can be produced without an effects-based
“room”:

- mono synthetic Chatterbox prompt and mono generation;
- continuous two-to-four-sentence performances;
- native low-level endings retained;
- conditional MossFormer2_SR_48K restoration;
- restrained corrective EQ;
- no denoise, gate, compressor, exciter, reverb, echo taps, room tone or stereo widening.

The current film still has imperfect sentence joins because it was edited into fixed caption slots. That is
not an accepted feature and must not be used to judge the upstream acoustic method. Audio-first productions
will keep selected sections continuous.

## Rejected baselines

| experiment | result | conclusion |
|---|---|---|
| `engine/voice_chain.py`: de-ess, compression, saturation, pitch drift, synthetic breaths and stereo room IR | Rejected as more artificial | Do not stack generic “humanizing” DSP |
| Showoff v7.3: room tone, 17/29/43 ms reflection taps and soft-knee compression | Rejected as “a robot with echoes” | Discrete early reflections are not the missing ingredient |
| Aggressive `top_db=40` trimming and last-word + 100 ms cuts | Audible clipped breaths/releases | Lexical timing is not acoustic timing |
| Unconditional speech restoration | Some cues changed pitch or transcription | Restoration requires a clean-resample fallback |
| Cloning an approved prompt with a larger model to inherit its delivery | Clone kept the timbre, lost the pace; raw prompt preferred over every clone of itself | Prompt quality does not transfer through a clone. Audition the engine on the real script |
| Loudness-matching comparison files by static gain without a peak check | All delivered files clipped; verdict was "tone fine, acoustics much worse" | Match downward to a level the whole set can hold, and measure the delivered file |

## Experiment protocol

Change one variable at a time and record:

1. Hypothesis and audible problem.
2. Immutable source WAV hash.
3. Exact model, code, parameters and seed.
4. Loudness-matched bypass and treatment samples.
5. Transcript, duration, F0 and bandwidth measurements.
5a. True peak and integrated loudness **of the delivered comparison files themselves**, not only of
   the sources. Nothing goes to a listener above −1 dBTP, and nothing goes lossy.
6. Headphone and laptop-speaker verdicts.
7. Accepted, rejected or inconclusive outcome.

No effect becomes a default from theory alone. A human listening verdict is required, and rejected variants
remain named so another session does not rediscover them.

## Next useful experiments

- Test the same audio-first, no-slicing pipeline on a distinctly different synthetic voice.
- Compare raw 24 kHz, clean 48 kHz resample and gated restoration as continuous paragraph files.
- Measure whether prompt capture quality predicts output high-frequency texture across voices.
- Establish profile-specific EQ from loudness-matched blind comparisons instead of copying the warm curve.
- Test section-boundary silence durations while leaving all sentence-internal timing untouched.
