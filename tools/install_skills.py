#!/usr/bin/env python3
"""Install the three skills, and the tree they point into, in another project.

    python tools/install_skills.py /path/to/project           # install
    python tools/install_skills.py /path/to/project --check   # say what it would do, change nothing
    python tools/install_skills.py /path/to/project --force   # overwrite files that differ

Why this is not `cp -r .claude/skills`:

`natural-voice/SKILL.md` is a short document whose content is a relative link to the method —
`../../../video/natural-voice/README.md`. Copy the skill alone and it still loads, still announces
itself as the authority on generated speech, and can no longer reach a word of what it knows. So
the skill and the tree travel together, at the same relative offset:

    <target>/.claude/skills/natural-voice/SKILL.md  ──►  <target>/video/natural-voice/README.md

That is the whole design. `--skills-only` exists for the case where the target already has an
identical `video/` tree; it is otherwise the wrong flag.

Installing into `~/.claude/skills` to make the skills global does not work and is refused: from
there the link resolves to `~/video/natural-voice/README.md`, which is not a thing.
"""

from __future__ import annotations

import argparse
import filecmp
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# What travels. `video/` goes whole: it is 2.6 MB, and a partial copy is how a link starts dangling.
PAYLOAD = [".claude/skills", "video", "tools/check_links.py", "tools/skill-hashes.txt"]

SKIP_DIRS = {".git", "__pycache__", "out", ".venv", "venv", "node_modules"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def payload_files():
    """Every file that travels, as (source path, repo-relative posix path)."""
    for item in PAYLOAD:
        src = ROOT / item
        if src.is_file():
            yield src, item
            continue
        if not src.is_dir():
            print(f"! missing from this repository: {item}", file=sys.stderr)
            continue
        for p in sorted(src.rglob("*")):
            if not p.is_file():
                continue
            r = p.relative_to(ROOT)
            if any(part in SKIP_DIRS for part in r.parts):
                continue
            yield p, r.as_posix()


def refuse_global(target: Path) -> str | None:
    """Global skill directories cannot host these skills. Say so rather than half-installing."""
    parts = [q.lower() for q in target.parts]
    if ".claude" in parts and "skills" in parts:
        return ("that is a skills directory, not a project root. These skills reach their method by\n"
                "  ../../../video/natural-voice/README.md, which only resolves when they sit inside a\n"
                "  project that also has video/. Give me the project root instead.")
    if target == Path.home() or (target / ".claude").resolve() == (Path.home() / ".claude").resolve():
        return ("installing to the home directory would put video/ in your home folder. Give me a\n"
                "  project root instead.")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="project root to install into")
    ap.add_argument("--check", action="store_true", help="report only; change nothing")
    ap.add_argument("--force", action="store_true", help="overwrite files whose content differs")
    ap.add_argument("--skills-only", action="store_true",
                    help="copy .claude/skills only — leaves natural-voice unable to reach its method "
                         "unless the target already has an identical video/ tree")
    a = ap.parse_args(argv)

    target = Path(a.target).expanduser().resolve()
    if target == ROOT:
        print("Already installed — this is the repository the skills live in.")
        return 0
    if (why := refuse_global(target)):
        print(f"Refusing: {why}", file=sys.stderr)
        return 2
    if not target.exists():
        if a.check:
            print(f"note: {target} does not exist; it would be created")
        else:
            target.mkdir(parents=True)

    payload = list(payload_files())
    if a.skills_only:
        payload = [(s, r) for s, r in payload if r.startswith(".claude/skills")]
        print("! --skills-only: video/ is not being copied. natural-voice will only work if the\n"
              "  target already has this repository's video/ tree at its root.\n")

    new, same, differ = [], [], []
    for src, r in payload:
        dst = target / r
        if not dst.exists():
            new.append((src, r))
        elif filecmp.cmp(src, dst, shallow=False):
            same.append(r)
        else:
            differ.append((src, r))

    print(f"target:    {target}")
    print(f"payload:   {len(payload)} files")
    print(f"  new:     {len(new)}")
    print(f"  same:    {len(same)}")
    print(f"  differ:  {len(differ)}")

    if differ:
        print("\nAlready present and different:")
        for _, r in differ[:15]:
            print(f"  {r}")
        if len(differ) > 15:
            print(f"  … and {len(differ) - 15} more")
        if not a.force:
            print("\nNothing written. Look at these, then re-run with --force to overwrite them.")
            return 1

    if a.check:
        print("\n--check: nothing written.")
        return 0

    written = 0
    for src, r in new + (differ if a.force else []):
        dst = target / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written += 1
    print(f"\nwrote {written} file(s)")

    # Verify in the target, using the copy of the checker that just landed there.
    ok = True
    for where, link in [(".claude/skills/natural-voice/SKILL.md", "../../../video/natural-voice/README.md"),
                        (".claude/skills/education-video/SKILL.md", "interview.md")]:
        f = target / where
        if not f.exists() or not (f.parent / link).resolve().exists():
            print(f"! {where} cannot reach {link}", file=sys.stderr)
            ok = False
    for src, r in payload:
        if r.startswith(".claude/skills") and sha(src) != sha(target / r):
            print(f"! {r} did not copy byte-identical", file=sys.stderr)
            ok = False

    if not ok:
        return 1
    print("verified — skills byte-identical, geometry intact.")
    if not a.skills_only:
        print(f"Run this in the target to check everything:\n  python tools/check_links.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
