# inbox — raw friction, awaiting review

One file per machine, named for its hostname, appended by `tools/friction.py flush` on the branch
`friction/<host>` and never in anyone's working tree. Newest entries last.

Nothing here is read back into a run. Review it in the PR, then fold what is worth keeping into
`../lessons/` with `python tools/friction.py compact`.

**Do not delete entries you have folded in.** `compact` counts `seen N×` from this directory, so it
is a pure function of the ledger — run it twice, get the same answer. Deleting a folded entry
quietly demotes a lesson that keeps being learned. Entries you chose *not* to fold stay too: an
unfixed complaint is still a finding, and the third time it appears it is a proposal.
