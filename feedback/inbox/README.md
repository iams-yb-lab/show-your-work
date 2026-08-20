# inbox — raw friction, awaiting review

One file per machine, named for its hostname, appended by `tools/friction.py flush` on the branch
`friction/<host>` and never in anyone's working tree. Newest entries last.

Nothing here is read back into a run. Review it in the PR, fold what is worth keeping into
`../lessons/` with `python tools/friction.py compact`, and delete the entries you folded in the same
commit. Entries you did not fold stay — an unfixed complaint is still a finding, and the third time
it shows up it is a proposal.
