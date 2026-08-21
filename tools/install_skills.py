#!/usr/bin/env python3
"""Install the skills, and the tree they point into, in another project.

    python tools/install_skills.py /path/to/project           # install
    python tools/install_skills.py /path/to/project --check   # say what it would do, change nothing
    python tools/install_skills.py /path/to/project --force   # overwrite files that differ
    python tools/install_skills.py /path/to/project --update  # bring an existing install up to date

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

It also wires two things into the target's `.claude/settings.json`, and says which:

  the feedback loop (--no-feedback-hook opts out)   reads `feedback/lessons/<skill>.md` into a run
      and pushes what went wrong back here as a pull request. Without it the skills still work;
      they just cannot learn from the run, and nothing comes back to the lab.

  the update check (--no-update-hook opts out)      at the start of a session, `video/tools/update.py`
      asks GitHub whether there is a newer version and installs it. Without it the project keeps the
      version it was installed with, for as long as it exists, and nobody finds out.

`--update` is the mode that check runs: replace the files that are read-only by contract when they
differ, add anything missing, leave the project's own edits to `video/` alone and name them.
"""

from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import os
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
# `LICENSE` travels because it has to: PolyForm's Notices section requires that anyone who gets
# any part of the software also gets the terms, and an install is exactly that. `ACCEPTABLE-USE.md`
# does not travel — it is the lab's stated position, not a licence term, and it links into
# `feedback/`, which would break the payload-self-contained check.
PAYLOAD = [".claude/skills", "video", "tools/check_links.py", "tools/skill-hashes.txt",
           "tools/friction.py", "tools/update.py", "feedback/lessons", "LICENSE"]

# Where each of those lands in the target. `.claude/skills/` and `video/` are forced: a project's
# skills must sit at its root to be discovered at all, and `natural-voice/SKILL.md` reaches its
# method by ../../../video/natural-voice/README.md, which is read-only. Everything else goes inside
# video/, so an install adds ONE directory to the project instead of three, and never merges into a
# `tools/` the project already has. Both tools find their root by walking up, so either layout works.
REMAP = {"tools/": "video/tools/", "feedback/lessons": "video/feedback/lessons",
         "LICENSE": "video/LICENSE"}


def dest_of(rel: str) -> str:
    for src, dst in REMAP.items():
        if rel.startswith(src):
            return dst + rel[len(src):]
    return rel

# Target-relative paths whose content is not the project's to own: the skills are read-only by
# rule, the tools and the reviewed lessons are shared machinery, and all three are byte-identical
# to the checkout by design. So `--update` replaces them when they differ, because a difference
# there is damage or staleness rather than work. Everything else in video/ is method and record:
# added when missing, never overwritten without --force.
CONTRACT = (".claude/skills/", "video/tools/", "video/feedback/lessons/", "video/LICENSE")


def is_contract(dest: str) -> bool:
    return dest.startswith(CONTRACT)


SKIP_DIRS = {".git", "__pycache__", "out", ".venv", "venv", "node_modules"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def payload_files():
    """Every file that travels, as (source path, repo-relative posix, target-relative posix)."""
    for item in PAYLOAD:
        src = ROOT / item
        if src.is_file():
            yield src, item, dest_of(item)
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
            yield p, r.as_posix(), dest_of(r.as_posix())


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


FRICTION = '${CLAUDE_PROJECT_DIR:-.}/' + dest_of("tools/friction.py")
UPDATER = '${CLAUDE_PROJECT_DIR:-.}/' + dest_of("tools/update.py")

# Two independent bits of wiring, each with its own opt-out, each keyed by the script it calls so
# that --uninstall can find them again. `feedback` carries what a run got wrong back to the lab;
# `update` pulls the latest skills from GitHub at the start of a session, so a project installed
# months ago does not quietly go on using the version it was installed with.
FEATURES = {
    "feedback": {
        "script": dest_of("tools/friction.py"),
        "hooks": {
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
        },
    },
    "update": {
        "script": dest_of("tools/update.py"),
        # Not on `compact`: that is a session continuing, and changing the skills under a run in
        # progress is worse than being a day behind.
        "hooks": {
            "SessionStart": [{
                "matcher": "startup|resume|clear",
                "hooks": [{"type": "command", "command": f'python3 "{UPDATER}" hook', "timeout": 180,
                           "statusMessage": "Checking GitHub for a newer version of the skills"}],
            }],
        },
    },
}

# Both scripts are ours, so --uninstall can recognise its own wiring by filename.
OURS = ("friction.py", "update.py")

# So a session in *any* project can find the clone to push from, and to update from. A pointer on
# this machine, not a path written into a file — this repository must never name another checkout as
# a live path. FRICTION_STATE moves it, as it does for friction.py and update.py, so an install can
# be exercised end to end without touching the real pointer.
HOME_TXT = (Path(os.environ.get("FRICTION_STATE")
                 or Path.home() / ".claude" / "skill-friction").expanduser() / "home.txt")


def commands_in(settings: dict, event: str) -> set[str]:
    return {h.get("command", "") for group in settings.get("hooks", {}).get(event, [])
            for h in group.get("hooks", [])}


def wire(target: Path, features: tuple[str, ...], check: bool) -> list[str]:
    """Merge the hooks for each named feature into the target's settings. Idempotent, and reported."""
    did = []
    if not features:
        return did
    f = target / ".claude" / "settings.json"
    settings = {}
    if f.is_file():
        try:
            settings = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [f"! {f} is not valid JSON — not touching it. Wire the hooks by hand."]

    allow = settings.setdefault("permissions", {}).setdefault("allow", [])
    for key in features:
        where = FEATURES[key]["script"]    # the path a session in the target will type
        for rule in (f"Bash(python3 {where}:*)", f"Bash(python {where}:*)"):
            if rule not in allow:
                allow.append(rule)
                did.append(f"permission: {rule}")

    hooks = settings.setdefault("hooks", {})
    for key in features:
        for event, groups in FEATURES[key]["hooks"].items():
            for group in groups:
                have = commands_in(settings, event)
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


MARKER = "video/WHAT-IS-THIS.md"

MARKER_TEXT = """\
# What this directory is, and what happens if you delete it

`video/` was not written by this project. It was installed by `show-your-work`, which is a set of
skills for making explainer videos, cinematic renders, technical reports and slide decks with
Claude. It holds the method those skills read, the shared audio and picture tooling they run, and
`tools/` and `feedback/` inside it.

**Deleting it breaks the skills, silently.** `natural-voice/SKILL.md` is a short document whose whole
content is a relative link to `natural-voice/README.md` in here. Remove this tree and that skill
still loads, still announces itself as the authority on generated speech, and can no longer reach a
word of what it knows. Nothing will tell you.

It sits at the project root, and cannot be moved, because that link is fixed and the skills are
read-only.

## Removing it properly

From the show-your-work checkout:

    python tools/install_skills.py /path/to/this/project --uninstall

That deletes only the files it installed, leaves anything you edited, unwires the hooks it added,
and tells you what it left behind. `--uninstall --check` shows you first.

## Staying current

A session started in this project checks GitHub for a newer version of the skills and installs it,
through `video/tools/update.py`. It fast-forwards only, never touches your own files in here, and
says nothing when there is nothing to do. `SHOW_YOUR_WORK_UPDATE=off` in the environment stops it on
this machine; removing its SessionStart hook from `.claude/settings.json` stops it for the project.

## The two directories inside

    tools/       check_links.py verifies the skills can still reach their method; friction.py
                 records what a run got wrong and sends it back as a pull request; update.py
                 keeps this copy of the skills level with GitHub
    feedback/    lessons from earlier runs, read at the start of each run of a skill
"""


def ours(command: str) -> bool:
    return any(name in command for name in OURS)


def unwire(target: Path, check: bool) -> list[str]:
    """Take our hooks and permissions back out. The inverse of wire."""
    did = []
    f = target / ".claude" / "settings.json"
    if not f.is_file():
        return did
    try:
        settings = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"! {f} is not valid JSON — remove our hooks by hand"]

    allow = settings.get("permissions", {}).get("allow", [])
    for rule in [r for r in allow if ours(r)]:
        allow.remove(rule)
        did.append(f"permission removed: {rule}")

    for event, groups in list(settings.get("hooks", {}).items()):
        keep_groups = []
        for group in groups:
            kept = [h for h in group.get("hooks", []) if not ours(h.get("command", ""))]
            did.extend(f"{event} hook removed: {h['command']}"
                       for h in group.get("hooks", []) if ours(h.get("command", "")))
            if kept:
                keep_groups.append({**group, "hooks": kept})
        if keep_groups:
            settings["hooks"][event] = keep_groups
        else:
            del settings["hooks"][event]

    if did and not check:
        f.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return did


def uninstall(target: Path, check: bool) -> int:
    """Remove exactly what was installed. Anything edited since is left alone and reported."""
    removed, kept, absent = [], [], 0
    for src, _, dest in payload_files():
        dst = target / dest
        if not dst.is_file():
            absent += 1
        elif filecmp.cmp(src, dst, shallow=False):
            removed.append(dest)
            if not check:
                dst.unlink()
        else:
            kept.append(dest)

    marker = target / MARKER
    if marker.is_file():
        removed.append(MARKER)
        if not check:
            marker.unlink()

    if not check:   # prune the directories we created, deepest first, only if now empty
        for d in sorted({(target / r).parent for r in removed}, key=lambda q: -len(q.parts)):
            while d != target and d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                d = d.parent

    verb = "would remove" if check else "removed"
    print(f"target:   {target}")
    print(f"{verb}: {len(removed)} file(s)")
    if absent:
        print(f"absent:   {absent} file(s) were not there")
    if kept:
        print(f"\nleft in place — these differ from what was installed, so they are yours now:")
        for r in kept[:15]:
            print(f"  {r}")
        if len(kept) > 15:
            print(f"  … and {len(kept) - 15} more")
    if (lines := unwire(target, check)):
        print("\nhooks:")
        for line in lines:
            print(f"  {line}")
    if check:
        print("\n--check: nothing removed.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="project root to install into")
    ap.add_argument("--check", action="store_true", help="report only; change nothing")
    ap.add_argument("--force", action="store_true", help="overwrite files whose content differs")
    ap.add_argument("--update", action="store_true",
                    help="bring an existing install up to date: replace the read-only files that "
                         "differ (skills, tools, lessons), add anything missing, and leave the "
                         "project's own edits to video/ alone. What update.py runs.")
    ap.add_argument("--no-update-hook", action="store_true",
                    help="do not wire the SessionStart update check into the target. The skills "
                         "work; they just stay at the version installed today, forever")
    ap.add_argument("--no-feedback-hook", action="store_true",
                    help="do not wire the friction hooks into the target. The skills work; they "
                         "just stop learning, and nothing comes back to the lab")
    ap.add_argument("--uninstall", action="store_true",
                    help="remove what was installed, leave anything you edited, unwire the hooks")
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
    if a.uninstall:
        return uninstall(target, a.check)
    if not target.exists():
        if a.check:
            print(f"note: {target} does not exist; it would be created")
        else:
            target.mkdir(parents=True)

    payload = list(payload_files())
    if a.skills_only:
        payload = [(s, r, d) for s, r, d in payload if r.startswith(".claude/skills")]
        print("! --skills-only: video/ is not being copied. natural-voice will only work if the\n"
              "  target already has this repository's video/ tree at its root.\n")

    new, same, differ = [], [], []
    for src, r, dest in payload:
        dst = target / dest
        if not dst.exists():
            new.append((src, dest))
        elif filecmp.cmp(src, dst, shallow=False):
            same.append(dest)
        else:
            differ.append((src, dest))

    print(f"target:    {target}")
    print(f"payload:   {len(payload)} files")
    print(f"  new:     {len(new)}")
    print(f"  same:    {len(same)}")
    print(f"  differ:  {len(differ)}")

    # --force overwrites everything that differs; --update only the files that are ours by
    # contract. Both leave a target's own work in video/ where it is.
    overwrite = differ if a.force else [d for d in differ if a.update and is_contract(d[1])]
    leave = [d for d in differ if d not in overwrite]

    if overwrite:
        print(f"\nStale, and will be replaced ({len(overwrite)}) — read-only by contract:")
        for _, r in overwrite[:10]:
            print(f"  {r}")
        if len(overwrite) > 10:
            print(f"  … and {len(overwrite) - 10} more")
    if leave:
        print(f"\nAlready present and different ({len(leave)}):")
        for _, r in leave[:15]:
            print(f"  {r}")
        if len(leave) > 15:
            print(f"  … and {len(leave) - 15} more")
        if not (a.force or a.update):
            print("\nNothing written. Look at these, then re-run with --force to overwrite them.")
            return 1
        print("  left alone — method and records are the project's. --force overwrites them.")

    features = tuple(k for k in FEATURES if not getattr(a, f"no_{k}_hook"))

    if a.check:
        if a.update:
            print(f"\nupdate: {len(new) + len(overwrite)} file(s) stale, {len(leave)} left alone")
        if features:
            did = wire(target, features, check=True)
            print("\nhooks would be wired into the target:")
            for line in did or ["  (already wired)"]:
                print(f"  {line}")
        print("\n--check: nothing written.")
        return 0

    written = 0
    for src, r in new + overwrite:
        dst = target / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written += 1
    marker = target / MARKER
    if not marker.is_file():
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(MARKER_TEXT, encoding="utf-8")
        written += 1
    print(f"\nwrote {written} file(s)")
    print(f"added to {target.name}/: " + ", ".join(sorted(
        {d.split("/")[0] + "/" for _, _, d in payload})) +
        f"\n  everything but .claude/ and video/ lives inside video/, so this project gains one\n"
        f"  directory, not three. {MARKER} says what it is and how to remove it.")

    # Verify in the target, using the copy of the checker that just landed there.
    ok = True
    for where, link in [(".claude/skills/natural-voice/SKILL.md", "../../../video/natural-voice/README.md"),
                        (".claude/skills/education-video/SKILL.md", "interview.md")]:
        f = target / where
        if not f.exists() or not (f.parent / link).resolve().exists():
            print(f"! {where} cannot reach {link}", file=sys.stderr)
            ok = False
    for src, r, dest in payload:
        if r.startswith(".claude/skills") and sha(src) != sha(target / dest):
            print(f"! {dest} did not copy byte-identical", file=sys.stderr)
            ok = False

    if not ok:
        return 1
    print("verified — skills byte-identical, geometry intact.")

    if features:
        did = wire(target, features, a.check)
        if did:
            print("\nhooks wired into the target:")
            for line in did:
                print(f"  {line}")
            print("  Runs of these skills now read feedback/lessons/ and send what went wrong\n"
                  "  back as a pull request, and a session here starts by checking GitHub for a\n"
                  "  newer version. --no-feedback-hook and --no-update-hook opt out.")
        else:
            print("\nhooks: already wired.")
    if a.update:
        print(f"update: {written} file(s) refreshed, {len(leave)} left alone")
    if not a.skills_only:
        print("Run this in the target to check everything:\n"
              f"  python {dest_of('tools/check_links.py')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
