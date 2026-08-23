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

### The applied GATE 4 proposal named a real project and a real person, and history keeps it

The file was deleted on 2026-08-23 when the proposal was applied, so **the tip is clean** — the
record that replaced it in `EXPORT-MANIFEST.md` says "a 15-slide talk built with this skill
elsewhere" and names nobody, and `references/slide-deck-gate4-toolkit/` carries no lab name either.
But the repository has been public since 2026-08-21 and **the commits still contain the original**,
which named `RedPitaya` and the IAMS Yb Lab and quoted the deck's author verbatim. Removing that
means rewriting public history, which is a decision and not a cleanup, and `CLAUDE.md` forbids
rewriting history to tidy. Waits on the user.

### 31 files hardcode `C:\Users\iams1\...`

Not a secret, but a machine account name in a public repository, and `CLAUDE.md` calls a hardcoded
checkout path a bug in its own right. `tools/friction.py` refuses these in friction entries while
the repository is full of them. Most of them are under `.claude/skills/**`, which is read-only, so
the fix needs the exact phrase; the rest are in `references/frozen-scripts/`, which is frozen by
definition. Waits on the user.

### `education-video/examples/intro/` header text is 14px against a 28px floor

Found by running the composition check against it: "PRECISION TEMPERATURE CONTROLLER" and the
"01 · 09" counter render at 14px, half the floor `slide-deck` GATE 0 sets and `education-video`
inherits. They are visible in the frame, so the finding is real. Either the film's furniture is
exempt from the floor and the check should say so, or that example needs a rebuild. Waits on the
user, because it is a question about what the floor is for.

### Nothing. `origin` carries `main` and the branch in review, and no more.

Cleared 2026-08-23. Four of the branches thought to be stale had already been deleted; the local
remote-tracking refs were out of date, which is worth knowing next time — `git fetch --prune`, not
`git fetch`, before believing `git branch -r`.
