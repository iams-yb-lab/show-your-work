# Export manifest

Extracted 2026-08-14 from the `temperature-controller` repository, at commit `2fea890`.

141 files, 2.6 MB. The method, the shared tooling and the evidence came; the films did not.

## The skills, byte-identical

Copied without a character changed, because they are read-only and because an adapted skill is a
different skill. Verified by `tools/check_links.py`, which reads `tools/skill-hashes.txt`.

| file | sha256 (first 16) |
|---|---|
| `.claude/skills/education-video/SKILL.md` | `99a16be0ad1e7866` |
| `.claude/skills/education-video/interview.md` | `fa7a570e313f1d84` |
| `.claude/skills/education-video/images.md` | `81b65b43ae00363c` |
| `.claude/skills/natural-voice/SKILL.md` | `1b11e1ec4bbf2538` |
| `.claude/skills/showoff-render/SKILL.md` | `8805cef3fc262996` |

## What came with them, and why it had to

| what | why it is not optional |
|---|---|
| `video/natural-voice/` | `natural-voice/SKILL.md` links to `README.md` here for the method itself, to `EXPERIMENTS.md` for what is ruled out, and to `profiles/warm-natural/` for the approved voice identity. Without this directory the skill is a broken link |
| `video/engine/` | the shared audio: BS.1770-4 loudness, true-peak limiting, the voice chain. `voice_chain.py` is linked by name from the method as a failed approach not to repeat |
| `video/picture/` | the HTML-bundle-to-video exporter. `education-video` GATE 5 ends in a bundle and says rendering it is the assistant's job — this is what does it |
| `video/showoff/assembly/RENDER-LOG.md` | showoff-render says "the full arc, with numbers and citations, is in" this file |
| `video/showoff/assembly/audio/VOICE-LOG.md` | the method links to it for the rejected room-tone experiment and its verdict |
| `video/showoff/assembly/{picture,script,audio}/` | the Blender + KiCad pipeline and the audio R&D: showoff-render's reference implementation and the record behind natural-voice's fourteen rejected attempts |
| `video/education/` | both explainers' documents, scripts, logs and tools — including `how-to-make-an-explainer/tools/`, the cross-check tooling `education-video` tells you to build |
| `.claude/hooks/git-autosync.sh` | pushes commits already made; exits silently with no remote |

## What did not come

`video/out/` — 5.1 GB of frames, takes, mixes and masters, gitignored at both ends and
regenerable. Plus two documents about the source repository rather than about the method:
`video/MOVE-LOG.md`, which instructs its own retirement once the old layout is gone, and
`video/RELEASES.md`, an index of cuts that live under `out/`.

**Everything else tracked under `video/` came, including 107 MB of film media** — the two 26 MB
Claude Design bundles, the intro film's MP4 and HTML, and the four committed stills.

That reverses the first pass, which left them on the grounds that films must not accumulate in a
directory packaged for reuse. That rule assumes the film still has a home. Once the source `video/`
is deleted this repository is the only home, and the explainer's own render log says **the picture
cannot be re-rendered without those bundles** — they are an input, not an output. Losing something
irreplaceable to keep a repository tidy is the wrong trade.

The rule still holds going forward: **new** films belong to the project using the skill, not here.

## What was changed on the way in

Nothing in `.claude/skills/`. Outside it, every path that named another checkout as a **live** path
was removed, because the source `video/` tree is being deleted and this repository has to stand on
its own. `tools/check_links.py` now fails on any that come back.

| what | was | now |
|---|---|---|
| 10 Python files | a repository root hardcoded to one checkout | walk up to the directory holding `video/natural-voice/` |
| 2 Python files | `sys.path` into a pre-move `PCB/render/tools` | the same walk-up, to `video/engine/` |
| `render.ps1`, `animate.ps1`, `animate_v2.ps1` | `-Board` defaulted to one project's `.kicad_pcb` | no default; `throw "pass -Board <path to your .kicad_pcb>"` |
| `pipeline/mix_final.py` | the picture to mux hardcoded to one render | `SHOWOFF_PICTURE` from the environment |
| `warm-natural-v2/README.md` | run commands naming one machine's venv in one checkout | `$env:EDITX_PYTHON` and a repo-relative script path |
| 2 narration scripts | traces linked to the board's review and spec | the same traces, named as text, like the rows beside them |

**Records were left verbatim** and are declared in `check_links.py`'s `RECORDS` — six files: the
generation settings, the prompt-selection audition record, the delivered Design prompt, and the
three v2 pipeline reports. They describe what happened on a particular machine on a particular day,
and nothing reads them. Rewriting a record to look tidy in a new repository falsifies it. The
allowlist is exactly those six; nothing is listed that does not need to be, because an unnecessary
entry is a hole.

Sixteen further files mention the source project's name **without depending on it**: fifteen frozen
scripts write to `%TEMP%\temperature-controller-media\`, a machine-local scratch directory that
merely borrowed the name, and the assembly film's brief describes its subject in prose. Neither is
a path into another checkout.

`video/README.md` was rewritten for this repository. Three film READMEs lost a link to the dropped
`RELEASES.md`.

**Records were left verbatim.** `DESIGN-PROMPT.md`'s absolute paths, `education-v2-generation-settings.json`'s
provenance, and `VOICE-LOG.md`'s pre-move `PCB/render/` references all describe what actually
happened on a particular machine on a particular day. Rewriting a record to look tidy in a new
repository falsifies it.

## What will not run here

Honest limits, so nobody discovers them mid-task:

- `video/showoff/assembly/audio/{pipeline,natural-v8}/` — their repository anchors were repaired,
  but their inputs were takes under `out/` and scratch directories in `%TEMP%` that did not travel.
  Read them as the experiment record they are.
- `video/natural-voice/profiles/deep-onyx-slow/make_prompt.py` — same: the profile document and its
  measurements are here, the prompt-generation inputs are not. `warm-natural/` is complete,
  including its prompt WAV.
- `video/showoff/assembly/picture/*.ps1` — the Blender pipeline renders a specific board from a
  KiCad file in the other repository. It is here as showoff-render's worked example.
- The two `narration-assembly*.md` scripts trace their claims to that board's review and spec.
  Those links dangle on purpose and are registered in `check_links.py`'s `EXTERNAL` list.
- Several scripts extend `PATH` with this machine's ffmpeg install. Left alone: changing a path
  that works on the machine the export was made on trades a real capability for a tidier file.
