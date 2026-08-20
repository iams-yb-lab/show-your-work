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
session ends                      Stop hook pushes it to friction/<host>
                                    -> inbox/<host>.md, one standing PR per machine
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

## The two directories

| | what it is | who writes it | travels with the skills |
|---|---|---|---|
| `inbox/<host>.md` | raw entries from one machine, newest last, awaiting review | `friction.py flush`, via git plumbing, on a branch — never in your working tree | no |
| `lessons/<skill>.md` | reviewed, compacted, size-capped to 2 KB | you, at merge, with `friction.py compact` | **yes** |

One inbox file per machine, so two people's entries never conflict in the same PR.

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

This repository goes to the whole lab. It must never become a back door onto someone's film.

**Never** put in an entry: verbatim script or narration text, a subject or client name, an absolute
path, a filename from the user's project. `friction.py note` rejects absolute paths outright, but it
cannot recognise a title or a name — that judgement is the writer's.

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
