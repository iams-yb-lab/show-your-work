# show-your-work — how we work

This repository is five skills and the evidence behind them. [`MAP.md`](MAP.md) says which files
belong to which skill; [`README.md`](README.md) is the front door. Nothing here is a film; films are
made elsewhere, using this.

## The shape of every reply

Three sections, these names, this order, whenever you report work. Written for a tired reader.

**Done**: what is now true, one bullet per result, including whether it was saved and pushed.
**Caveats**: unfinished work, limits, side effects; "None." when there are none. **Need from you**:
one action or decision; "Nothing." when there is none, or "Nothing now. Later: <the decision>". Then
stop.

- About 20 words per bullet, one idea each. Any number of bullets.
- Completeness beats brevity. When the two conflict, the point stays.
- Ordinary English. No invented words, no metaphors, no internals unless they change what I do.
- Do not narrate your reasoning or what you tried first. The commit message is for that.
- Anything I must decide goes under *Need from you* and nowhere else.
- Keep a problem I have now apart from maintenance I might want later.
- Name sources in plain English ("the render log from the showoff film"), not as bare paths.
- Proposals about this system go to [`MAINTENANCE.md`](MAINTENANCE.md) as one line, not into chat.

This governs reporting work, not answering a question. Asked what a skill does or where something
stands, give the whole picture, unfinished and awkward parts included.

## What the skills are

Toolboxes of process notes: the order of steps that has worked, the questions worth asking early,
and how to do the technical parts (voice, images, picture, delivery, checks). They are not procedures
to recite. No plan checklists posted for approval, no "ready to begin?", no mandatory interview
before work starts, no stage-numbered message headers, no waiting at each step for permission to
continue. Read the project first; ask the questions that matter, in plain prose, when they matter;
otherwise keep going.

The skills carry no opinions on the content, tone or structure of what gets made. That belongs to
the project's own style guide. The technical rules stay: an audited source document before
scripting; one home per number, precision limited by the inputs; audio recorded and locked before the
picture is timed; captions derived from the master; `natural-voice` loaded before any speech is
generated; licensed images only; mechanical cross-checks; lossless delivery; the closing credit slate.

Plain English throughout the skills. No film or workshop vocabulary, no quoted insults, no
"record of failures" framing. Rejected treatments are kept as flat tables (what was tried, why it was
rejected) because they prevent repeats. Established technical terms are never renamed.

## The skills are shared, so change them in the open

`.claude/skills/**` travels between repositories: a session that quietly changes a skill changes how
every future session works, everywhere, unreviewed. So a skill is never edited casually.

When the repository owner asks for a change: edit here, commit on a branch, push, open a pull request
that says what changed and why, refresh `tools/skill-hashes.txt` and `EXPORT-MANIFEST.md`, and
reinstall where the skills are installed. A request from anyone else, or an urge of your own, becomes a
lesson in `feedback/inbox/` and the skill is followed as written. Hashes are recorded so an unrecorded
edit shows up as a mismatch.

## Do not let films accumulate here

A film's document, script, takes, masters and picture belong to the user's project, not to the
tooling. When someone uses a skill from here, ask where the film's files go and never default to
putting them next to the skill.

What may be added here: a new voice profile under `natural-voice/profiles/`, a fix to shared tooling
in `_shared/`, a fix to a skill's own `method/`, or a correction to a method document.
`slide-deck/examples/presentation/` is the one output kept here: its subject is this repository and
it is the only evidence `slide-deck` has. Leave it; it is not a precedent. `examples/` holds the
worked examples the skills were written from; a new film does not go there.

## Log the friction, silently

When a skill from here was used and anything went wrong (a correction, rework, a re-run stage, a
wrong assumption), record one entry before the session ends:

```bash
python3 tools/friction.py note --session <id> --skill <name> \
  --complaint "what they pushed back on" --mistake "what I did" \
  --fix "what worked" --rule "the one line that would have prevented it"
python3 tools/friction.py note --session <id> --skill <name> --none   # clean run
```

- It does not involve the user: no permission, no offer, no report. The `Stop` hook pushes it to a
  branch and keeps one standing pull request per machine.
- It carries a rule, not a story. Fields are capped at 220 characters.
- No film content, ever: no script text, no subject or client name, no absolute path, no filename
  from the user's project. `note` rejects absolute paths; the rest is your judgement.

The `PostToolUse` hook on `Skill` injects `feedback/lessons/<skill>.md` at the start of a run; only
reviewed lessons on `main` are injected. Format and redaction rule: [`feedback/README.md`](feedback/README.md).
Repeated entries are the evidence a skill change is argued from.

## `proposals/` holds one thing, and empties itself

A proposal is skill text waiting for the owner's go-ahead: the argument, the evidence, and the block
that will become `.claude/skills/**`. Do not open one unless asked; tooling and rule notes are one
line in [`MAINTENANCE.md`](MAINTENANCE.md). The pull request that applies a proposal deletes it; the
rationale lives in the commit message and the pull request. A proposal a skill names by path stays,
so the reference does not dangle.

## Every change arrives as a pull request

Nothing is pushed to `main`. Work happens on a branch, the branch becomes a pull request, and the
merge is decided by the people reviewing it. There is no bypass, because the rule exists to bind the
people who could grant themselves one. Enforcement until a ruleset exists is
`.claude/hooks/git-autosync.sh`: on the default branch it pushes nothing and tells you the commands
that turn your commits into a branch.

Branch before the first commit of a session. **One open pull request at a time**; if work is open,
add to that branch or wait. `.claude/hooks/one-pr.py` refuses `gh pr create` while another is open,
exempting `friction/*`; `tools/test_one_pr.py` holds that case. Say what a branch is for before
committing to it; a branch collecting unrelated changes becomes a pull request nobody can review as
one decision.

## The geometry is load-bearing

Everything a skill owns is inside its folder, so a skill and its method never travel separately.
`natural-voice/SKILL.md` reaches its method by `method/README.md`, and the method reaches the shared
engine by `../../_shared/audio/voice_chain.py`. The load-bearing links are listed in
[`MAP.md`](MAP.md) and enforced by `GEOMETRY` in `tools/check_links.py`. A link out of
`.claude/skills/` breaks the moment someone installs the skills; the `travel` check catches it, which
is why `references/` and `proposals/` can only be named in prose from inside a skill, never linked.

```bash
python tools/check_links.py
```

Run it after moving, renaming or adding anything.

## Paths in new code

Do not anchor on the checkout and never count directories. Walk up to the directory holding
`.claude/skills/natural-voice/` (or, from inside the skills, the one holding `_shared/` and
`natural-voice/`) and take every path from there; the expression is in
[`.claude/skills/_shared/README.md`](.claude/skills/_shared/README.md).

## Honest results only

A failed check gets reported with its output. A skipped step gets said. For anything anyone listens to
or watches, the user's ears and eyes outrank every measurement here; this repository has rejected
word-perfect, loudness-correct audio for sounding synthetic.
