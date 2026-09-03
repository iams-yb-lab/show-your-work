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

### `education-video/examples/intro/` header text is 14px against a 28px floor

Found by running the composition check against it: "PRECISION TEMPERATURE CONTROLLER" and the
"01 · 09" counter render at 14px, half the floor `slide-deck` GATE 0 sets and `education-video`
inherits. They are visible in the frame, so the finding is real. Either the film's furniture is
exempt from the floor and the check should say so, or that example needs a rebuild. Waits on the
user, because it is a question about what the floor is for.

### `segno` is a new dependency, needed only for a card with a QR code — waits on the user

`_shared/endcard/build_card.py` imports it lazily and refuses with the pip line when a credits
file has a `link` and segno is absent. Every other card builds without it. Nothing in this
repository declares dependencies, so this is recorded rather than pinned:

```bash
python -m pip install segno
```

### `_shared/endcard/example/example-card.png` does not reproduce on this machine — waits on the user

Rebuilding `credits.example.json` and rendering it here gives a PNG that differs from the committed
one across the whole card, at up to 230 levels per channel. Not caused by the showcase work: the
pre-change and post-change code produce byte-identical renders here, so the shipped file was made
somewhere with different font rasterisation. It is documentation, not a fixture nothing compares
against, so the choice is to rebuild it here or to stop treating it as reproducible.

### The end card has never closed a real film — waits on the next film

`_shared/endcard/` is proven end to end on a throwaway clip: the card renders through the film's
own exporter, the stream-copy join is frame-exact (60 + 180 = 240) and the picture's video stream
MD5 is unchanged by it. No finished film has used it. It joins `deliver_film.py` and
`composition_check.py` in that category, and the first real pass is the one that proves it — read
what it prints rather than trusting the exit code.

### Should `slide-deck` get an authorship slide too? — waits on the user

The end card was scoped to video, because a deck is not a film. But a deck presented outside the
lab has the same problem the films had: nothing on it says who made it, what was generated, or who
is answerable. The deck already renders 1920x1080 HTML through the same composition check, so the
card would drop in with almost no work. Not done, because scope creep into a second medium is the
user's call.

### The skills name `_shared/endcard/` in prose, so nothing checks it is there — waits on the user

`education-video` and `showoff-render` now tell a run to use `_shared/endcard/`, but they name it
rather than linking it, so `check_links.py` cannot see the reference and `GEOMETRY` — which is a
list of relative *links* — has no shape to hold it. Delete that directory and both skills would
still load, still sound authoritative, and send someone to a folder that is not there. The same is
true of `showoff-render`'s prose reference to its render log, which is why this is a question about
the check rather than a defect in the edit.
