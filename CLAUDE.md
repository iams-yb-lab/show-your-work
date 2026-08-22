# show-your-work — how we work

This repository is five skills and the evidence behind them. [`README.md`](README.md) is the map.
Nothing here is a film; films are made *elsewhere, using* this.

## IMPORTANT: the shape of every reply

Three sections, these names, this order, whenever you report work. Written for a tired reader.

**Done** — what I can now see is true, one bullet per result, including whether it was saved and
pushed. **Caveats** — unfinished work, limits, side effects; "None." when there are none. **Need
from you** — one action or decision; "Nothing." when there is none, or "Nothing now. Later: <the
decision>" when it is not needed yet. Then stop.

- **20 words per bullet, one idea each.** No limit on how many bullets: the cap is on how much you
  say about a thing, never on how many things you say. Offer detail, never supply it unasked.
- **Completeness beats brevity.** Leaving a point out to keep a reply short is the one mistake I
  cannot spot from the outside. When the two conflict, the length rule loses and the point stays.
- **Ordinary English.** No invented words, no metaphors, no internals unless they change what I do.
- **Never narrate** your reasoning, your testing, or what you tried first. The commit message is for
  that, and `feedback/inbox/` is for what went wrong on the way.
- **Never say "nothing" and then add an exception.** Anything I must decide goes under *Need from
  you* and nowhere else.
- **Keep a problem I have now apart from maintenance I might want later.**
- **Sources survive in plain English** — "the render log from the showoff film", never a bare path.
- **Never put a proposal about this system in chat.** A skill change, the tooling, the checks and
  these rules go to `proposals/`, with the friction entries that would settle them.

**This governs reporting work; it does not govern answering a question.** Asked what a skill does or
where something stands, I want the whole picture — unfinished, unverified and awkward included. A
missing fact costs me far more than a long answer does.

## IMPORTANT: the skills are read-only

`.claude/skills/**` is not yours to edit. Not a wording tweak, not one more bullet, not "while I
was in there". A skill travels between repositories, so a session that quietly improves one changes
how every future session works, everywhere, unreviewed.

**The only exception is the user typing `I insist on editing the skills`** — exactly, not a
paraphrase and not a typo. Anything short of it, *including* a direct "put this in the skill",
means: say you are not going to, write the request down where the current work lives, and keep
following the skill as written.

The skills say this about themselves. The copies here are byte-identical to their source and their
hashes are recorded in [`EXPORT-MANIFEST.md`](EXPORT-MANIFEST.md); an edit shows up as a hash
mismatch, which is the point.

## IMPORTANT: do not let films accumulate here

A film's document, script, takes, masters and picture belong to the user's project, not to the
tooling. When someone uses a skill from this repository, **ask where the film's files go and never
default to putting them next to the skill.** `education-video`'s interview stage says this
explicitly and it applies to this whole directory.

What may be added here: a new voice profile under `video/natural-voice/profiles/`, a fix to shared
tooling in `video/engine/` or `video/picture/`, or a correction to a method document.

`presentation/` is the standing exception, not a loophole. It is the how-to-use-the-skills deck:
its subject *is* this repository, so there is no project elsewhere for it to live in, and it is
the only evidence `slide-deck` has. Its home was fixed at that deck's GATE 0 interview, not
defaulted to. It is outside the install payload, so it never reaches a target project. **Leave it
where it is** — and do not read it as permission for a second one. Anything about another project
goes to that project.

## IMPORTANT: log the friction, silently

Every run of these skills that goes wrong teaches something, and the read-only rule throws it away
unless it is written down. So: **when a skill from here was used and anything went wrong — a
correction, rework, a re-run gate, a wrong assumption — record one entry before the session ends.**

```bash
python3 tools/friction.py note --session <id> --skill <name> \
  --complaint "what they pushed back on" --mistake "what I did" \
  --fix "what worked" --rule "the one line that would have prevented it"
python3 tools/friction.py note --session <id> --skill <name> --none   # clean run
```

Three things about how this is done, all of them non-negotiable:

- **It does not involve the user.** Do not ask permission, do not offer to log it, do not report
  that you logged it, do not turn it into a conversation. It is bookkeeping. The `Stop` hook pushes
  it to a branch and keeps one standing pull request per machine; that PR is the only thing a human
  is meant to see.
- **It carries a rule, not a story.** The `rule` field is the whole point — the line a future
  authorized skill edit would quote. Fields are capped at 220 characters and `note` refuses a
  transcript.
- **No film content, ever.** No script or narration text, no subject or client name, no absolute
  path, no filename from the user's project. This repository goes to the whole lab. `note` rejects
  absolute paths; the rest is your judgement.

The hooks do the rest: `PostToolUse` on `Skill` injects `feedback/lessons/<skill>.md` so you start a
run already knowing what it got wrong last time, and `Stop` reminds you once if a skill ran and
nothing was recorded. Only *reviewed* lessons on `main` are ever injected — an unreviewed entry
cannot change how a skill behaves, which is the read-only guarantee applied to the feedback loop.
The format, the loop and the redaction rule are in [`feedback/README.md`](feedback/README.md).

This is also the only sanctioned route to changing a skill: a `proposals/` document argues from
entries — how often, at which gate, what it cost — and then the user types the exact phrase. A
proposal with no entries behind it is taste, which is what the read-only rule exists to keep out.

## IMPORTANT: every change arrives as a pull request

Nothing is pushed to `main`. Not by me, not by an admin, not by a session that only fixed a typo.
Work happens on a branch, the branch becomes a pull request, and the merge is decided by the people
reviewing it together. **There is no bypass, because the rule exists to bind the people who could
grant themselves one.**

GitHub is not what enforces this. The repository is private on a free org plan, where rulesets and
branch protection are unavailable, so the enforcement is `.claude/hooks/git-autosync.sh`: on the
default branch it pushes nothing and tells you the three commands that turn your commits into a
branch. On any other branch it behaves as it always did.

So: **branch before the first commit of a session.** Landing commits on `main` is not a disaster —
they simply sit there until someone moves them — but it is a step you then have to undo by hand.

The friction loop already worked this way and is unchanged: `friction/<host>` and one standing pull
request per machine, never a direct push.

## The geometry is load-bearing

`natural-voice/SKILL.md` reaches its method by `../../../video/natural-voice/README.md`. That is
why `video/` sits beside `.claude/`, and why the two halves never travel separately.

```bash
python tools/check_links.py
```

Run it after moving, renaming or adding anything. It exits non-zero on a broken relative link. If
it reports a link into a file that was deliberately left behind, that belongs in the known-external
list at the top of the script, with a reason — not silently.

## Paths in new code

**Do not anchor on the checkout.** Walk up to the directory holding `video/natural-voice/` and take
every path from there; the expression is in
[`.claude/skills/_shared/README.md`](.claude/skills/_shared/README.md). A hardcoded
checkout path is why a batch of scripts in the source repository could not run on the second
machine.

## Honest results only

A failed check gets reported with its output. A skipped step gets said. The bench — the user's ears
and eyes — outranks every measurement in here, and this repository has rejected word-perfect,
loudness-correct audio for sounding synthetic. **For anything anyone listens to or watches, your
ears are not the bench.**
