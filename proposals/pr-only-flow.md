# Proposal: every change to this repository arrives as a pull request, admins included

**Status: PARTLY APPLIED 2026-08-21.** The user decided the rule that same day: everyone,
admins included, opens a pull request, and the merge is decided together. Step 2 below is done —
`git-autosync.sh` now refuses to push the default branch, and `CLAUDE.md` states the rule.

**Step 1 is now unblocked and not yet done.** The repository was made public later the same day, so
rulesets are available; `GET /rulesets` returns `[]` instead of 403. Creating one needs **admin**,
which the session account does not have, so it waits on an admin — see *Going public* below. Step 3
(a fork flow) stopped being hypothetical the moment the repository went public. This document
remains as the rationale.

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

The org is on the **free** plan and the repository was **private**, which is the one combination
where branch protection and rulesets are unavailable. There was no way to require a pull request,
and therefore no way to make the rule bind an admin who forgets it. Convention was the only
mechanism, and a `Stop` hook that pushes without being asked is stronger than a convention.

**Superseded 2026-08-21, later the same day:** the supervisor made the repository public. Free plan,
public repo is a supported combination, so `GET /repos/iams-yb-lab/show-your-work/rulesets` now
returns `[]` rather than 403. The hook stays regardless — it is what stops a session pushing `main`
before a ruleset ever sees the push, and it is the half that travels to installed targets.

## What it would take

1. **Make enforcement possible.** ~~Either make the repository public, or move the org to Team.~~
   **Done 2026-08-21 — the repository is public.** What remains is the ruleset itself, on `main`:
   require a pull request, one approval, and an **empty bypass list** — that last part is what makes
   it apply to admins, which is the actual request here. **An admin must create it**; `admin` is
   false for the session account, and repository rulesets are an admin-only API. The two admins are
   the people to ask. The exact call is in *Going public* below.
2. **Stop the hook from pushing `main`.** `git-autosync.sh` should refuse when the branch is the
   default branch: warn, name the branch to create, push nothing. Today it would simply start
   failing once protection exists — it exits 0 and warns, so it degrades safely, but work then sits
   local with only a status line to say so. Better to make the refusal deliberate than incidental.
3. **Decide what non-collaborators do.** `flush` pushes a branch to `origin` directly; there is no
   fork flow. Someone with read-only access gets a silent no-op and a local buffer that grows
   forever — the entries are never lost and never arrive. If the skills are meant to go wider than
   the write-access list, `flush` needs a fork-and-PR path, and that is a real piece of work.
   **Raised in priority 2026-08-21:** "wider than the write-access list" is no longer a hypothetical.
   Anyone can now clone the repository, install the skills, and accumulate friction that can never
   be delivered. Six of the nine collaborators are already `pull`-only and would hit this today.

## Going public, 2026-08-21 — what it unblocked and what it exposed

The supervisor made the repository public. Two consequences, and they point opposite ways.

**Unblocked.** Rulesets are reachable. The ruleset this proposal asks for, as a single call an
admin can run:

```bash
gh api -X POST repos/iams-yb-lab/show-your-work/rulesets \
  -f name='pull requests only' -f target=branch -f enforcement=active \
  -F 'conditions[ref_name][include][]=~DEFAULT_BRANCH' \
  -F 'rules[][type]=pull_request' \
  -F 'rules[][parameters][required_approving_review_count]=1' \
  -F 'rules[][parameters][dismiss_stale_reviews_on_push]=true' \
  -F 'rules[][parameters][require_last_push_approval]=true' \
  -F 'bypass_actors[]='
```

Two things to weigh before running it. GitHub does not let an author approve their own pull
request, so **one approval means no one can land a change alone** — with nine collaborators that is
the intent, not an obstacle, but it does end same-session merges. And an empty bypass list binds
the admins who create it, which is the whole point and is also the part people undo three weeks
later; if it is going to be undone, better not to claim it.

**Exposed.** The audience for this repository changed from the lab to everyone, and two things were
written for the smaller audience:

- **`proposals/slide-deck-gate4-checks.md` names a real project and lab** — `RedPitaya`,
  IAMS Yb Lab — and quotes the deck's author verbatim, including the line about why one image is
  sitting on top of another. Unattributed and unremarkable inside a lab; outside one it is an
  identifiable person's rough first reactions, in public. The redaction rule in `CLAUDE.md` forbids exactly this
  for friction entries, on the reasoning that "this repository goes to the whole lab" — the same
  reasoning now reaches further than the rule does.
- **`video/` hardcodes `C:\Users\iams1\...` in 37 files.** Not a secret, but a machine account
  name in public, and `CLAUDE.md` already calls hardcoded checkout paths a bug that broke a batch of
  scripts on the second machine. `tools/friction.py` refuses these in friction entries while the
  repository is full of them.

Neither is a leak: no credential, key or address is tracked anywhere. Both are judgement calls for
the user, and history is public either way, so a scrub means rewriting it — which is a decision, not
a cleanup. **There is also no `LICENSE`.** A public repository without one is all-rights-reserved,
so nobody outside may reuse the skills this repository exists to distribute.

## Cost of not doing it

The friction half is fine. The exposure is the other half: an unreviewed edit to a method document,
or to the `feedback/lessons/` files that are read back into every future run, reaches `main` the
moment a session ends. That is the same class of risk the read-only skills rule exists to remove,
one directory over.

## Friction entries behind this

None. This is not a lesson from a run; it is a gap between the stated rule and the wiring, found by
reading the hooks. Recorded here rather than in chat because it is a proposal about the tooling.
