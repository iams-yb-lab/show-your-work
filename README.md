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

To use them somewhere else, see [Installing elsewhere](#installing-elsewhere) — do not copy a
`SKILL.md` on its own.

**[`MAP.md`](MAP.md) says which files belong to which skill.** Start there if you are looking for
something.

## One folder per skill

Everything a skill owns is inside that skill's folder: its instructions, its method, its profiles
and its worked examples. `natural-voice/SKILL.md` is a short document that says *the method is next
door, go and read it*, and next door is
[`natural-voice/method/README.md`](.claude/skills/natural-voice/method/README.md).

So a skill is not one file. It is the folder, and the paths inside it are fixed:

```
natural-voice/SKILL.md          ──►   method/README.md
natural-voice/method/README.md  ──►   ../../_shared/audio/voice_chain.py
                                ──►   ../../showoff-render/examples/assembly/audio/VOICE-LOG.md
```

Copy a `SKILL.md` without its folder and the skill still loads, still sounds authoritative, and
quietly stops being able to tell you the thing it exists to tell you. `tools/check_links.py` exists
to catch precisely that.

Only what more than one skill calls is shared, in
[`_shared/`](.claude/skills/_shared/) — the audio engine, the composition check and the
authorship end card every film closes on.
`technical-report` and `slide-deck` contain no paths at all, and `technical-report` owns nothing
beyond its instructions, which [`MAP.md`](MAP.md) says out loud so nobody goes looking.

This layout replaced a top-level `video/` tree on 2026-08-22; the case is in the pull request that
did it, `#8`.

## Layout

```
.claude/skills/     the five skills, each with its own method and examples inside it, plus
                    _shared/ for what more than one of them calls. This is the whole payload
MAP.md              which files belong to which skill. Read this first
references/         set aside, not deleted, and never installed — see references/README.md
proposals/          absent unless something is waiting. It holds skill text and nothing
                    else, and the pull request that applies one deletes it
MAINTENANCE.md      open items on this repository's own machinery, one line each
feedback/           what the skills got wrong in real runs. lessons/ is reviewed and travels
                    with the skills; inbox/ is raw, per-machine, and stays here
tools/              install_skills.py, check_links.py, friction.py, update.py — this
                    repository's machinery. No skill calls any of it
EXPORT-MANIFEST.md  what was carried out of the source repository, and what was not
LICENSE             PolyForm Noncommercial 1.0.0. Travels with an install; see Licence below
ACCEPTABLE-USE.md   what the lab asks of you beyond the licence. Does not install
```

`slide-deck/examples/presentation/` is the one thing here that is an *output* rather than a method,
and it earns its place twice over: its subject is this repository, so it has no other project to
live in, and it is the only evidence `slide-deck` has — that skill was written without a reference
deck, and this is the deck that tested it. Until 2026-08-22 it sat in a top-level `presentation/`
that no document connected to the skill it belonged to. It is not a precedent for films: those
still live in the project they are about.

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

It copies each skill's folder whole, so every link inside it resolves in the target. It also wires two things into the target's
`.claude/settings.json`, and says which: the two friction hooks — `--no-feedback-hook` opts out, at
the cost of that project's runs teaching nobody anything — and the session-start update check,
which `--no-update-hook` opts out of, at the cost of that project never seeing a newer version.
`--check` shows what it would do; `--update` brings an install that is already there up to date;
`--skills-only` is available and is the wrong choice unless you know why.

**A target project gains one directory.** `.claude/skills/` is forced — a project's skills must sit
at its root to be found at all — and everything else is installed inside it:

```
<target>/.claude/skills/            the five skills, each whole
        _shared/                    the audio engine, the composition check, the end card
        _shared/tools/              check_links.py, friction.py, update.py, skill-hashes.txt
        _shared/feedback/lessons/   what earlier runs got wrong
        _shared/WHAT-IS-THIS.md     what this is, and that deleting it breaks the skills silently
```

192 files, 16.5 MB. Before 2026-08-22 it was 108 MB, because a `video/` tree carried three past
jobs' media that no skill ever opened; that media is in `references/` now and does not install.

Nothing is ever written to a target's own `tools/`, so an install cannot collide with a directory
the project already has. Installing into a subfolder below the project root does not work: skills
nested there are not discovered, and would load as nothing at all.

To take it back out:

```bash
python tools/install_skills.py /path/to/project --uninstall
```

It removes only the files it installed, leaves anything edited since and names it, unwires the hooks
it added, and prunes the directories it created. `--uninstall --check` shows you first.

Installing to `~/.claude/skills/` — the usual way to make a skill global — is **refused**, for a
narrower reason than it used to be. The installer creates `.claude/skills/` itself, so pointing it
at one would nest a second copy inside the first; give it the project root. Pointing it at `$HOME`
is refused too, though since every path a skill needs is now inside its own folder that case would
probably resolve and work. Nobody has tried it, and a half-working global install is worse than
none, so it stays refused until someone does it on purpose.

## Staying up to date

A session that starts here, or in any project the skills were installed into, asks GitHub whether
there is a newer version and installs it before you type anything.

```bash
python tools/update.py check    # what it would do, changing nothing
python tools/update.py apply    # do it now
```

It is deliberately narrow:

- **It updates from the lab, not from `origin`.** `iams-yb-lab/show-your-work` is named in the tool
  as an identity. `origin` is trusted only where it *is* that repository: on a fork it is the fork,
  and a fork a few months behind would otherwise hand you its stale skills and report success. Off
  the lab, the lab's `main` is fetched by URL into a ref of the tool's own — no remote is added to
  your checkout and no branch appears in your list.
- **Fast-forward only.** A checkout that has diverged, or where the merge would overwrite
  something, is reported and left exactly as it is — never merged, never rebased, never stashed.
- **In a project it re-installs from the checkout on this machine**, the one `install_skills.py`
  left a pointer to. The files that are read-only by contract — the skill instruction files and
  everything in `_shared/`, tools and lessons included — are replaced when they differ, because a
  difference there is staleness or damage. A skill's `method/`, `examples/` or `profiles/` that the
  project has edited is left alone and named. With no checkout on the machine it says that, rather than looking successful.
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
| independence | any absolute path naming another checkout, so this repository never quietly needs one — and, inside the payload, any literal home directory, which resolves on one machine and names its owner |
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

`LICENSE` is part of the install payload and lands at `.claude/skills/_shared/LICENSE` in a target
project, because the licence requires that anyone who receives any part of this also receives the
terms.

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
