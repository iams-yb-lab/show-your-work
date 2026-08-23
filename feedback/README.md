# feedback — what the skills got wrong, and the line that would have prevented it

The skills here are **read-only**. That rule protects every future session from an unreviewed
tweak, and on its own it throws away the one thing a run actually teaches: the moment the user had
to correct Claude. This directory is the other half of the rule.

Nothing in here is a diary. One entry per thing that went wrong, six fields, and the field that
matters is `rule` — the single line that would have made the run one-pass. Everything else is
provenance for the day someone asks *why* that line is in a skill.

## The loop

```
a skill runs somewhere            PostToolUse(Skill) injects lessons/<skill>.md
  something goes wrong            Claude records one entry, silently, at session end
                                    -> ~/.claude/skill-friction/pending.jsonl   (machine-local)
session ends                      Stop hook pushes it to friction/<name>
                                    -> inbox/<name>.md, one standing PR per sender
you review the PR                 with Claude, at your pace
  worth keeping                   python tools/friction.py compact
                                    -> lessons/<skill>.md on main
                                    -> read back at the start of the next run of that skill
  a pattern, seen 3x, 5x          proposals/<something>.md, citing the entries
                                    -> you type the exact phrase -> the skill changes
```

**Only `lessons/` is ever read back.** An unreviewed entry cannot change how a skill behaves — the
same guarantee the read-only rule gives, applied to the feedback loop. `inbox/` is evidence; it is
never injected into a run.

## How it gets here, with or without push rights

Reporting friction does not need write access to this repository. `flush` builds its commit in a
bare scratch repo of its own — `~/.claude/skill-friction/upstream.git`, a hundred KB or so, trees
and no file contents — and never inside one of your own checkouts. It then takes one of three
routes, resolved once from two API answers and cached in `route.json` next to it:

| route | when | where it lands | `<name>` |
|---|---|---|---|
| direct | you have push rights here | `friction/<host>`, one standing request per machine | `mac` |
| fork | you do not | your fork, then a cross-fork request onto `main` here | `you-mac` |
| stuck | no `gh`, not signed in, no network | nowhere; the buffer holds it for next session | — |

The name carries the handle on the fork route because `mac` and `macbook-pro` collide the moment two
people outside the lab report. `compact` globs `inbox/*.md` and does not care which shape it is.

Two things follow. A cross-fork pull request is **attributable**: it carries your GitHub handle,
creates a public fork under your account, and shows in your activity. There is no anonymous version
of this transport, and "silent" only ever meant that the tooling does not announce itself. And the
route is anchored on this repository's name rather than on your `origin` — on a fork `origin` is the
fork, and in a project the skills were installed into it is that project's own remote, which is
where a friction branch once could have landed.

`gh` not being signed in is the single state the loop says out loud, once per machine, because until
it is fixed nothing can leave at all. Every other reason to be stuck is silent and retried next
session.

## The two directories

| | what it is | who writes it | travels with the skills |
|---|---|---|---|
| `inbox/<name>.md` | raw entries from one sender, newest last, awaiting review | `friction.py flush`, via git plumbing, in a scratch repo of its own — never in your working tree | no |
| `lessons/<skill>.md` | reviewed, compacted, size-capped to 2 KB | you, at merge, with `friction.py compact` | **yes** |

One inbox file per sender, so two people's entries never conflict in the same request.

`inbox/` is the ledger, not a queue: `compact` counts `seen N×` by reading it, which makes it a pure
function of what is recorded there. Fold entries in, leave them where they are, and running compact
twice changes nothing.

## The entry

```
### 2026-08-20 · education-video · GATE 3
- **complaint:** what the user actually pushed back on
- **mistake:** what Claude did instead
- **fix:** what worked in the end
- **rule:** the one line that would have prevented all of it
- **cost:** 3 turns            (optional)
```

Every field is capped at 220 characters. Longer than that and it is a transcript, not a lesson, and
`friction.py note` refuses it.

## Redaction is part of the format

This repository goes to the whole lab, in public, and an entry arrives under a real GitHub
handle. It must never become a back door onto someone's film.

**Never** put in an entry: verbatim script or narration text, a subject or client name, an absolute
path, a filename from the user's project. `friction.py note` refuses what a pattern can catch —
absolute paths, `~/` paths, UNC shares, `file://` URLs, email addresses — but it cannot recognise a
title or a name, so treat the check as a floor and not as the rule. That judgement is the writer's.

Skill, gate, mistake, fix, rule. Nothing about *what* the film was.

## What a good entry looks like

Bad — a description of one afternoon, useful to nobody:

> **mistake:** got confused about the audio and had to redo it after the user complained

Good — a rule a future run can act on before making the mistake:

> **rule:** Agree the voice on one line before generating the whole script — a re-cut costs the
> whole render.

If you cannot write the `rule` field, there is no lesson yet. Record it anyway; three vague entries
about the same stage are themselves the finding.

## Turning entries into a skill edit

Entries are the **only** sanctioned route to changing a skill. A `proposals/` document argues from
them — how often, at which gate, what it cost — and the user types the exact phrase, or the skill
does not change. A proposal with no entries behind it is someone's taste, which is precisely what
the read-only rule exists to keep out.

A proposal is opened only when the user asks for one, and the pull request that applies it deletes
it: the rationale then lives in the commit message, where a reviewer looks for it. `proposals/` is
skill text awaiting the phrase and nothing else — see `../CLAUDE.md`. Everything about the tooling
and these rules is one line in `../MAINTENANCE.md` instead.
