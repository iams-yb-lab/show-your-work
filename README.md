# ai_video_generation

Three skills for making video with Claude, and the evidence behind them.

| skill | what it covers |
|---|---|
| [`natural-voice`](.claude/skills/natural-voice/SKILL.md) | any generated or synthetic speech — TTS, narration, cloning, dubbing, mixing |
| [`education-video`](.claude/skills/education-video/SKILL.md) | explainers: document → script → audio → picture, in that order |
| [`showoff-render`](.claude/skills/showoff-render/SKILL.md) | cinematic 3D renders and assembly animations of hardware |

They are already installed. Open a Claude Code session in this directory and they load — project
skills live at `.claude/skills/<name>/SKILL.md`, which is where these are.

To use them somewhere else, see [Installing elsewhere](#installing-elsewhere) — do not copy
`.claude/skills/` on its own.

## Why the `video/` tree comes with them

`natural-voice/SKILL.md` is a short document that says *the method is somewhere else, go and read
it*. That somewhere is [`video/natural-voice/README.md`](video/natural-voice/README.md), reached by
a relative link. Two more skills cite evidence the same way.

So the skills are not the three folders under `.claude/`. They are those folders **plus the tree
they point into**, and the paths between them are fixed:

```
<repo>/.claude/skills/natural-voice/SKILL.md   ──►   ../../../video/natural-voice/README.md
<repo>/video/natural-voice/README.md           ──►   ../engine/voice_chain.py
                                               ──►   ../showoff/assembly/audio/VOICE-LOG.md
```

Move either half without the other and the skills still load, still sound authoritative, and
quietly stop being able to tell you the thing they exist to tell you. `tools/check_links.py`
exists to catch precisely that.

## Layout

```
.claude/skills/     the three skills, byte-identical to the repository they came from
video/              the method, the shared tooling and the films' logs — see video/README.md
tools/              install_skills.py, check_links.py
EXPORT-MANIFEST.md  what was carried out of the source repository, and what was not
```

## Installing elsewhere

```bash
python tools/install_skills.py /path/to/other/project
```

It copies the skills **and** the tree they depend on, preserving the relative geometry above, so
every link resolves in the target. `--check` shows what it would do; `--skills-only` is available
and is the wrong choice unless you know why.

Installing to `~/.claude/skills/` — the usual way to make a skill global — **does not work for
these** and the installer will refuse it. From there, `../../../video/natural-voice/README.md`
resolves to `~/video/natural-voice/README.md`, which does not exist, and `natural-voice` becomes a
skill whose entire content is a broken link.

## Verifying

```bash
python tools/check_links.py
```

Five checks, exit non-zero with the file and line on any failure:

| check | catches |
|---|---|
| geometry | a skill that can no longer reach its method |
| skills | a skill file that was edited — they are read-only, and verified by hash |
| independence | any absolute path naming another checkout, so this repository never quietly needs one |
| travel | a link from inside the installable payload to a file that would not travel with it |
| links | any relative link that does not resolve |

Run it after moving, renaming or adding anything. It is also wired to a PostToolUse hook, so it
runs on every markdown write.

## Does this need any other repository?

**No.** It was extracted from the project the three films were made for, and everything that named
that project as a *live* path has been removed — pipeline board defaults, run commands, mux
targets. `install_skills.py` copies only from here. The independence check keeps it that way.

What remains are **records**: generation settings, an audition log, the delivered Design prompt,
the raw pipeline log. They name paths on the machine that made them because that is what a record
is, nothing reads them, and each is declared with its reason in `check_links.py`'s `RECORDS`.

The one thing not in here is the **board** the showoff film was rendered from. That is by design:
`showoff-render` works on whatever CAD you point it at, and the pipeline scripts now require
`-Board` instead of defaulting to somebody else's file.

## The one rule about the skills themselves

**They are read-only.** Not a wording tweak, not one more bullet. A skill travels between
repositories, so a session that quietly improves one changes how every future session works,
everywhere, unreviewed. The skills say this about themselves, and it is why the copies here are
byte-identical rather than adapted — the hashes are in [`EXPORT-MANIFEST.md`](EXPORT-MANIFEST.md).

The only exception is the user typing `I insist on editing the skills`, exactly.
