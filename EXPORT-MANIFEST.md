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

**The films.** 110 MB of picture and no method in any of it:

| left behind | size |
|---|---|
| `education/how-to-make-an-explainer/picture/*.html` (2 bundles) | 54 MB |
| `education/intro/picture/*.{mp4,html}` | 20 MB |
| `showoff/assembly/gallery/*.png` (4 stills) | 33 MB |
| `video/out/` — frames, takes, mixes, masters | 5.1 GB |

`education-video`'s interview stage is explicit that a skill travels between repositories, that the
films it produces are not part of it, and that the same holds for any directory being packaged for
reuse. This is that directory, so the rule applied to itself.

Also left: `video/MOVE-LOG.md`, which instructs its own retirement once the old layout is gone, and
`video/RELEASES.md`, an index of cuts that stayed behind.

## What was changed on the way in

Nothing in `.claude/skills/`. Outside it, twelve Python files that could not have run here:

- **10 × `REPO = Path(r"c:\temperature-controller")`** → a walk-up to the directory holding
  `video/natural-voice/`. The source repository's own README flagged this as the reason those
  scripts could not run on its second machine.
- **2 × `sys.path.insert(0, r"c:\temperature-controller\PCB\render\tools")`** → the same walk-up to
  `video/engine/`. That path had already died in the source repository's own reorganisation.

`video/README.md` was rewritten for this repository. Three film READMEs lost a link to the dropped
`RELEASES.md` and now point here instead.

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
