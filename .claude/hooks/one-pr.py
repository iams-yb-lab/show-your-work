#!/usr/bin/env python3
"""PreToolUse gate: one open pull request at a time.

Contract, deliberately narrow:

  - Fires only on a Bash command that would OPEN a pull request (`gh pr create`).
    Everything else — push, list, view, merge, close — passes untouched.
  - DENIES when `origin` already has an open pull request. Two open requests is a
    queue the reviewer did not ask for, and this repository accumulated five stale
    branches and a duplicate request that way. The refusal names the open one.
  - DENIES a second request for the branch you are already on: that request exists,
    a push updates it.
  - ALLOWS whenever it cannot be sure — `gh` missing, not logged in, no network,
    malformed input. A gate that blocks work because GitHub was unreachable is worse
    than the thing it prevents. Never guesses.

There is no bypass flag. If the refusal is wrong, the user decides in chat, which is
the same shape as every other rule in CLAUDE.md.
"""

import json
import re
import subprocess
import sys

# `gh ... pr create`, but only where a command can actually start: the beginning of
# the string, or just after a separator. Anchoring matters — matching the bare text
# anywhere denies `grep "gh pr create"` and every echo of a test payload, including
# the ones that test this file.
CREATE = re.compile(
    r"(?:^|[\n;&|(]|&&|\|\|)\s*gh\s+[^\n;&|]*?\bpr\s+create\b"
)


def allow() -> None:
    """Say nothing and let the call through."""
    sys.exit(0)


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def gh(*args: str) -> str | None:
    """Run gh and return stdout, or None if it cannot answer."""
    try:
        done = subprocess.run(
            ("gh",) + args, capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        allow()

    if event.get("tool_name") != "Bash":
        allow()
    command = (event.get("tool_input") or {}).get("command") or ""
    if not CREATE.search(command):
        allow()

    raw = gh("pr", "list", "--state", "open", "--json", "number,title,headRefName")
    if raw is None:
        allow()  # cannot ask GitHub: not this hook's business to block on that
    try:
        open_prs = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        allow()
    if not open_prs:
        allow()

    try:
        branch = subprocess.run(
            ("git", "rev-parse", "--abbrev-ref", "HEAD"),
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        branch = ""

    mine = [pr for pr in open_prs if pr.get("headRefName") == branch]
    if mine:
        pr = mine[0]
        deny(
            f"#{pr['number']} is already open for this branch ({branch}). "
            f"Push to it instead of opening a second one: git push"
        )

    listed = ", ".join(f"#{pr['number']} {pr.get('title', '')}".strip() for pr in open_prs)
    deny(
        f"This repository allows one open pull request at a time, and {listed} "
        f"is open. Add this work to that branch, or wait for it to merge. "
        f"CLAUDE.md, 'every change arrives as a pull request'. If that is wrong "
        f"here, ask the user rather than working around it."
    )


if __name__ == "__main__":
    main()
