# Maintenance — open items on this repository's own machinery

One file, one line per item, newest last. This is where anything about **the tooling, the checks,
the hooks and the rules** goes: not a new document per idea, and not into chat.

Rules for writing here, so it stays a ledger and not a pile:

- **One line, or a short block if there is a command to keep.** If it needs a document, it needs the
  user's decision first.
- **Say who it waits on.** An item nobody can act on is noise.
- **Delete the line when it is done.** The commit that closes it is the record.
- **`proposals/` is not for this.** That directory holds skill text waiting for the exact phrase,
  and nothing else — see [`CLAUDE.md`](CLAUDE.md).

## Open

### Branch-protection ruleset on `main` — waits on a GitHub admin

The pull-request rule is enforced by `.claude/hooks/git-autosync.sh`, which refuses to push the
default branch. The repository went public on 2026-08-21, so rulesets became available; creating one
needs **admin**, which the session account does not have. One call:

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

Two things to weigh first. GitHub does not let an author approve their own pull request, so one
approval means **nobody lands a change alone** — with nine collaborators that is the intent, but it
ends same-session merges. And an empty bypass list binds the admins who create it, which is the
point and also the part people undo three weeks later.

### `friction.py flush` has no fork path — read-only collaborators cannot deliver friction

`flush` pushes `friction/<host>` straight to `origin`. Someone with read access gets a silent no-op
and a local buffer that grows forever: entries are never lost and never arrive. Six of the nine
collaborators are `pull`-only and would hit this today. Fixing it means a fork-and-PR path in
`flush`, which is real work, not a patch. Waits on the user deciding whether the skills go wider
than the write-access list.

### `proposals/slide-deck-gate4-checks.md` names a real project and a real person, in public

It names `RedPitaya` and the IAMS Yb Lab, and quotes the deck's author verbatim. Unremarkable inside
a lab; the repository has been public since 2026-08-21. `CLAUDE.md` forbids exactly this for
friction entries. History is public either way, so a scrub means rewriting it — a decision, not a
cleanup. Waits on the user.

### 31 files hardcode `C:\Users\iams1\...`

Not a secret, but a machine account name in a public repository, and `CLAUDE.md` calls a hardcoded
checkout path a bug in its own right. `tools/friction.py` refuses these in friction entries while
the repository is full of them. Most of them are under `.claude/skills/**`, which is read-only, so
the fix needs the exact phrase; the rest are in `references/frozen-scripts/`, which is frozen by
definition. Waits on the user.

### The stale remote branches were not deleted

`add-license`, `proposal/gate4-tuning-constants`, `proposal/public-repo-followups`,
`slide-deck-gate4-geometry-checks` and `education-video/self-delivered-film` are all
patch-equivalent to commits already in pull request #8, and their local copies are gone. Deleting
them on `origin` was blocked by the permission classifier on 2026-08-23:

```bash
git push origin --delete add-license proposal/gate4-tuning-constants \
  proposal/public-repo-followups slide-deck-gate4-geometry-checks \
  education-video/self-delivered-film
```
