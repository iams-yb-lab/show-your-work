# Proposal: every change to this repository arrives as a pull request, admins included

**Status: PARTLY APPLIED 2026-08-21.** The user decided the rule that same day: everyone,
admins included, opens a pull request, and the merge is decided together. Step 2 below is done —
`git-autosync.sh` now refuses to push the default branch, and `CLAUDE.md` states the rule. Step 1
(a GitHub ruleset) is blocked on the org plan and step 3 (a fork flow for non-collaborators) is not
needed while everyone working here has write access. This document remains as the rationale.

## What happens today

Three ways a change reaches `origin`, and only one of them is a pull request.

| path | who | how it lands | PR? |
|---|---|---|---|
| friction from a run | any machine with the skills installed | `friction.py flush` pushes `friction/<host>`, `gh pr create` opens one standing PR per machine | yes |
| ordinary work in the checkout | whoever is in a session here | the `Stop` hook `git-autosync.sh` pushes the current branch — on `main`, straight to `main` | **no** |
| a hand edit and push | anyone with write access | nothing is in the way | **no** |

So the friction loop already behaves as intended. The path that carries every method document,
every proposal and every authorized skill edit does not: `git-autosync.sh` pushes whatever branch
HEAD is on, and sessions in this repository run on `main`. The last five commits went that way.

## Why GitHub is not enforcing it either

- `GET /repos/iams-yb-lab/show-your-work/branches/main/protection` → 404. No protection on `main`.
- `GET /repos/.../rulesets` → 403, *"Upgrade to GitHub Pro or make this repository public."*

The org is on the **free** plan and the repository is **private**, which is the one combination
where branch protection and rulesets are unavailable. There is currently no way to require a pull
request, and therefore no way to make the rule bind an admin who forgets it. Convention is the only
mechanism, and a `Stop` hook that pushes without being asked is stronger than a convention.

## What it would take

1. **Make enforcement possible.** Either make the repository public, or move the org to Team. Then
   one ruleset on `main`: require a pull request, one approval, and an **empty bypass list** — that
   last part is what makes it apply to admins, which is the actual request here.
2. **Stop the hook from pushing `main`.** `git-autosync.sh` should refuse when the branch is the
   default branch: warn, name the branch to create, push nothing. Today it would simply start
   failing once protection exists — it exits 0 and warns, so it degrades safely, but work then sits
   local with only a status line to say so. Better to make the refusal deliberate than incidental.
3. **Decide what non-collaborators do.** `flush` pushes a branch to `origin` directly; there is no
   fork flow. Someone with read-only access gets a silent no-op and a local buffer that grows
   forever — the entries are never lost and never arrive. If the skills are meant to go wider than
   the write-access list, `flush` needs a fork-and-PR path, and that is a real piece of work.

## Cost of not doing it

The friction half is fine. The exposure is the other half: an unreviewed edit to a method document,
or to the `feedback/lessons/` files that are read back into every future run, reaches `main` the
moment a session ends. That is the same class of risk the read-only skills rule exists to remove,
one directory over.

## Friction entries behind this

None. This is not a lesson from a run; it is a gap between the stated rule and the wiring, found by
reading the hooks. Recorded here rather than in chat because it is a proposal about the tooling.
