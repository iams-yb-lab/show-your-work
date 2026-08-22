# Shared

Only things **more than one skill calls**. Anything one skill owns lives in that skill's own folder;
this directory exists so a measurement has one answer instead of several.

```
audio/    dsp, mix_audio, voice_chain, narrate, check_score
checks/   the composition check: canvas overflow and the font-size floor
```

`_shared/` has no `SKILL.md`, so Claude Code does not discover it as a skill. It travels with the
skills because they call it.

## audio/

The BS.1770-4 loudness meter, the true-peak limiter, the van Herk sliding maximum, the voice chain
and the pitch set. Written for the assembly film; every film since imports it and none of them owns
it. **A second copy of a loudness meter is a second answer to the same question**, and this
repository's bench is a person's ears, which will not catch a wrong number.

`natural-voice/method/README.md` links `audio/voice_chain.py` directly, so that path is load-bearing
and `tools/check_links.py` fails if it moves.

Called by: `natural-voice` (method), `education-video` and `showoff-render` (their films' audio).

## checks/

`composition.py` — canvas overflow and the minimum on-screen font size, measured in headless Chrome.
One implementation, one 28-pixel floor. Two callers wrap it and add their own medium's checks:
`education-video/method/composition_check.py` adds determinism, offline behaviour, the duration
attribute and a contact sheet; `slide-deck/examples/presentation/tools/render_check.py` adds
per-slide screenshots.

Called by: `education-video`, `slide-deck`.

## Frozen copies that were deliberately left alone

Seven files still carry their own loudness or true-peak maths. Four of them
(`showoff-render/examples/assembly/audio/natural-v8/` and `.../pipeline/`) are records of what ran on
a particular machine on a particular day, and their inputs were takes that never travelled. **Read
them; do not expect them to run.** Rewriting a record to import from here would make it a tidier
document and a false one. `MAP.md` lists which those are.

## Paths, for anything written here in future

**Do not anchor on the checkout.** Walk up until you find the directory holding the skills:

```python
ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / ".claude" / "skills" / "natural-voice").is_dir())
```

Code written that way does not care which repository it was lifted into or which machine it is on.
A hardcoded checkout path is why a batch of scripts could not run on the project's second machine,
and `tools/check_links.py` fails on any absolute path naming another checkout.
