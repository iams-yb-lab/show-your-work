# show-your-work — how we work

This repository is five skills and the evidence behind them. [`README.md`](README.md) is the map.
Nothing here is a film; films are made *elsewhere, using* this.

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
every path from there; the expression is in [`video/README.md`](video/README.md). A hardcoded
checkout path is why a batch of scripts in the source repository could not run on the second
machine.

## Honest results only

A failed check gets reported with its output. A skipped step gets said. The bench — the user's ears
and eyes — outranks every measurement in here, and this repository has rejected word-perfect,
loudness-correct audio for sounding synthetic. **For anything anyone listens to or watches, your
ears are not the bench.**
