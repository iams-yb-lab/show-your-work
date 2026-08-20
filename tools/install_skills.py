#!/usr/bin/env python3
"""Install the skills, and the tree they point into, in another project.

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

It also wires the feedback loop into the target, unless you pass --no-feedback-hook: two hooks that
read `feedback/lessons/<skill>.md` into a run and push what went wrong back here as a pull request.
That writes two entries into the target's `.claude/settings.json` and says so. Without it the skills
still work; they just cannot learn from the run, and nothing comes back to the lab.
"""

from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# What travels. `video/` goes whole — a partial copy is how a link starts dangling. It is 108 MB,
# not the 2.6 MB this comment claimed until 2026-08-19: most of it is two 27 MB Claude Design
# bundles, an 18 MB master and 34 MB of render gallery, i.e. the films' picture, which
# EXPORT-MANIFEST.md records as unreproducible without these exact files. Installing copies all
# of it. `presentation/` and `proposals/` are deliberately not here — evidence about this
# repository, of no use in a target project. `feedback/lessons/` travels because the friction
# hook reads it back into every run; `feedback/inbox/` does not — that is evidence too.
PAYLOAD = [".claude/skills", "video", "tools/check_links.py", "tools/skill-hashes.txt",
           "tools/friction.py", "feedback/lessons"]

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


FRICTION = '${CLAUDE_PROJECT_DIR:-.}/tools/friction.py'

HOOKS = {
    "PostToolUse": [{
        "matcher": "Skill",
        "hooks": [{"type": "command", "command": f'python3 "{FRICTION}" brief', "timeout": 10,
                   "statusMessage": "Reading what this skill got wrong before"}],
    }],
    "Stop": [{
        "hooks": [
            {"type": "command", "command": f'python3 "{FRICTION}" check', "timeout": 10,
             "statusMessage": "Checking the friction log"},
            {"type": "command", "command": f'python3 "{FRICTION}" flush', "timeout": 90,
             "statusMessage": "Sending friction upstream"},
        ],
    }],
}

# So a session in *any* project can find the clone to push from. A pointer on this machine, not a
# path written into a file — this repository must never name another checkout as a live path.
HOME_TXT = Path.home() / ".claude" / "skill-friction" / "home.txt"


def commands_in(settings: dict, event: str) -> set[str]:
    return {h.get("command", "") for group in settings.get("hooks", {}).get(event, [])
            for h in group.get("hooks", [])}


def wire_feedback(target: Path, check: bool) -> list[str]:
    """Merge the two friction hooks into the target's settings. Idempotent, and it reports."""
    did = []
    f = target / ".claude" / "settings.json"
    settings = {}
    if f.is_file():
        try:
            settings = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [f"! {f} is not valid JSON — not touching it. Wire the hooks by hand."]

    allow = settings.setdefault("permissions", {}).setdefault("allow", [])
    for rule in ("Bash(python3 tools/friction.py:*)", "Bash(python tools/friction.py:*)"):
        if rule not in allow:
            allow.append(rule)
            did.append(f"permission: {rule}")

    hooks = settings.setdefault("hooks", {})
    for event, groups in HOOKS.items():
        have = commands_in(settings, event)
        for group in groups:
            fresh = [h for h in group["hooks"] if h["command"] not in have]
            if not fresh:
                continue
            hooks.setdefault(event, []).append({**group, "hooks": fresh})
            did.extend(f"{event}: {h['command']}" for h in fresh)

    if did and not check:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not HOME_TXT.is_file() or HOME_TXT.read_text(encoding="utf-8").strip() != str(ROOT):
        did.append(f"pointer: {HOME_TXT} -> {ROOT}")
        if not check:
            HOME_TXT.parent.mkdir(parents=True, exist_ok=True)
            HOME_TXT.write_text(str(ROOT), encoding="utf-8")
    return did


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="project root to install into")
    ap.add_argument("--check", action="store_true", help="report only; change nothing")
    ap.add_argument("--force", action="store_true", help="overwrite files whose content differs")
    ap.add_argument("--no-feedback-hook", action="store_true",
                    help="do not wire the friction hooks into the target. The skills work; they "
                         "just stop learning, and nothing comes back to the lab")
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
        if not a.no_feedback_hook:
            did = wire_feedback(target, check=True)
            print("\nfeedback loop would be wired into the target:")
            for line in did or ["  (already wired)"]:
                print(f"  {line}")
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

    if not a.no_feedback_hook:
        did = wire_feedback(target, a.check)
        if did:
            print("\nfeedback loop wired into the target:")
            for line in did:
                print(f"  {line}")
            print("  Runs of these skills now read feedback/lessons/ and send what went wrong\n"
                  "  back as a pull request. --no-feedback-hook opts out.")
        else:
            print("\nfeedback loop: already wired.")
    if not a.skills_only:
        print(f"Run this in the target to check everything:\n  python tools/check_links.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
