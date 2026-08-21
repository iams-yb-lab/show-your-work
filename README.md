# show-your-work

Five skills — three for making video with Claude, two for the documents a film rests on and the
room a project gets presented in — and the evidence behind them.

| skill | what it covers |
|---|---|
| [`natural-voice`](.claude/skills/natural-voice/SKILL.md) | any generated or synthetic speech — TTS, narration, cloning, dubbing, mixing |
| [`education-video`](.claude/skills/education-video/SKILL.md) | explainers: document → script → audio → picture, in that order |
| [`showoff-render`](.claude/skills/showoff-render/SKILL.md) | cinematic 3D renders and assembly animations of hardware |
| [`technical-report`](.claude/skills/technical-report/SKILL.md) | reports that stand alone: evidence → skeleton → sections → cold read |
| [`slide-deck`](.claude/skills/slide-deck/SKILL.md) | decks, spoken over or read alone: source → storyline → slides → build → cold pass |

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

`technical-report` and `slide-deck` are the exceptions: they link to nothing, so those two alone
would survive traveling without the tree — `install_skills.py` copies the payload whole either
way.

## Layout

```
.claude/skills/     the five skills — three byte-identical to the repository they came from,
                    technical-report and slide-deck born here (see EXPORT-MANIFEST.md)
video/              the method, the shared tooling and the films' logs — see video/README.md
presentation/       the how-to-use-the-skills deck: slide-deck's own first evidence, and a
                    worked example of what a run of these skills produces. Does not install
proposals/          why the skills were changed, one record per authorized edit
feedback/           what the skills got wrong in real runs. lessons/ is reviewed and travels
                    with the skills; inbox/ is raw, per-machine, and stays here
tools/              install_skills.py, check_links.py, friction.py, update.py
EXPORT-MANIFEST.md  what was carried out of the source repository, and what was not
LICENSE             PolyForm Noncommercial 1.0.0. Travels with an install; see Licence below
ACCEPTABLE-USE.md   what the lab asks of you beyond the licence. Does not install
```

`presentation/` is the one thing here that is an *output* rather than a method, and it earns the
exception twice over: its subject is this repository, so it has no other project to live in, and
it is the only evidence `slide-deck` has — that skill was written without a reference deck, and
this is the deck that tested it. It is not in the install payload, so it costs a target project
nothing. It is not a precedent for films: those still live in the project they are about.

## How the skills improve

They are read-only, so they do not improve by being edited mid-run. They improve because runs are
recorded. A `PostToolUse` hook on `Skill` reads `feedback/lessons/<skill>.md` into the start of a
run; when something goes wrong, Claude records one capped entry, silently; the `Stop` hook pushes it
to `friction/<hostname>` and keeps one standing pull request per machine. You review the PR, fold
what is worth keeping into `feedback/lessons/`, and the next run everywhere starts knowing it.

```bash
python tools/friction.py compact          # inbox entries -> reviewed lessons, at merge
python tools/friction.py flush --check    # what this machine would send, changing nothing
```

Nothing unreviewed is ever read back, no user is ever prompted, and no hook can fail a turn — the
buffer just waits for the next session. `feedback/README.md` has the format and the redaction rule:
entries carry a rule, never film content. Repeated entries are what a `proposals/` document argues
from when a skill genuinely needs to change.

## Installing elsewhere

```bash
python tools/install_skills.py /path/to/other/project
```

It copies the skills **and** the tree they depend on, preserving the relative geometry above, so
every link resolves in the target. It also wires two things into the target's
`.claude/settings.json`, and says which: the two friction hooks — `--no-feedback-hook` opts out, at
the cost of that project's runs teaching nobody anything — and the session-start update check,
which `--no-update-hook` opts out of, at the cost of that project never seeing a newer version.
`--check` shows what it would do; `--update` brings an install that is already there up to date;
`--skills-only` is available and is the wrong choice unless you know why.

**A target project gains two directories, not four.** `.claude/skills/` and `video/` are forced —
a project's skills must sit at its root to be found at all, and `natural-voice/SKILL.md` reaches its
method by `../../../video/natural-voice/README.md`, which is read-only and so cannot be redirected.
Everything else is installed *inside* `video/`:

```
<target>/.claude/skills/        the five skills
<target>/video/                 the method and the tooling they read
        video/tools/            check_links.py, friction.py, update.py, skill-hashes.txt
        video/feedback/lessons/ what earlier runs got wrong
        video/WHAT-IS-THIS.md   what this tree is, and that deleting it breaks the skills silently
```

Nothing is ever written to a target's own `tools/`, so an install cannot collide with a directory
the project already has. Installing everything into one subfolder instead does not work: skills
nested below the project root are not discovered, and the skills would load as nothing at all.

To take it back out:

```bash
python tools/install_skills.py /path/to/project --uninstall
```

It removes only the files it installed, leaves anything edited since and names it, unwires the hooks
it added, and prunes the directories it created. `--uninstall --check` shows you first.

Installing to `~/.claude/skills/` — the usual way to make a skill global — **does not work for
these** and the installer will refuse it. From there, `../../../video/natural-voice/README.md`
resolves to `~/video/natural-voice/README.md`, which does not exist, and `natural-voice` becomes a
skill whose entire content is a broken link.

## Staying up to date

A session that starts here, or in any project the skills were installed into, asks GitHub whether
there is a newer version and installs it before you type anything.

```bash
python tools/update.py check    # what it would do, changing nothing
python tools/update.py apply    # do it now
```

It is deliberately narrow:

- **Fast-forward only.** A checkout that has diverged, or where the merge would overwrite
  something, is reported and left exactly as it is — never merged, never rebased, never stashed.
- **In a project it re-installs from the checkout on this machine**, the one `install_skills.py`
  left a pointer to. The files that are read-only by contract — the skills, `video/tools/`,
  `video/feedback/lessons/` — are replaced when they differ, because a difference there is
  staleness or damage. Anything else in `video/` that the project has edited is left alone and
  named. With no checkout on the machine it says that, rather than looking successful.
- **After an update it runs `check_links.py` on what landed**, so a version that arrives broken
  says so at the start of the session instead of three gates later.
- **It says nothing when there is nothing to say.** A session that was already current starts
  silently; it speaks up when it changed something, and when it could not.
- **It never asks, and it cannot fail a session.** No prompt, every path exits 0. Offline long
  enough and it tells you once that this copy may be behind.

`SHOW_YOUR_WORK_UPDATE=off` in the environment stops it on one machine.
`install_skills.py --no-update-hook` never wires it into a target — which means that project keeps
the version it was installed with for as long as it exists, so pass it on purpose.

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

## Licence

[PolyForm Noncommercial 1.0.0](LICENSE). Copyright 2026 Institute of Atomic and Molecular
Sciences, Academia Sinica.

Use it, change it, build on it, pass it on — for any **noncommercial** purpose. The licence names
educational institutions, public research organizations and government institutions explicitly, and
covers them *regardless of how their work is funded*, so another lab can pick these skills up
without checking with anyone. Commercial use is the one thing it does not grant; ask the lab.

This is a **source-available** licence, not an open-source one. That is deliberate, and it is the
reason GitHub will not show an SPDX badge for it.

`LICENSE` is part of the install payload and lands at `video/LICENSE` in a target project, because
the licence requires that anyone who receives any part of this also receives the terms.

Separately, [`ACCEPTABLE-USE.md`](ACCEPTABLE-USE.md) is what the lab **asks** of you — about cloned
voices, generated footage presented as record, and the honesty rules the skills are built around.
It is a stated position and not a condition of the licence; nothing in it binds you and all of it
is meant.

## The one rule about the skills themselves

**They are read-only.** Not a wording tweak, not one more bullet. A skill travels between
repositories, so a session that quietly improves one changes how every future session works,
everywhere, unreviewed. The skills say this about themselves, and it is why the copies here are
byte-identical rather than adapted — the hashes are in [`EXPORT-MANIFEST.md`](EXPORT-MANIFEST.md).

The only exception is the user typing `I insist on editing the skills`, exactly.
