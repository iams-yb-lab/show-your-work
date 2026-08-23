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
  - IGNORES `friction/<host>` entirely, in both directions. The friction loop keeps
    one standing request per machine open by design, so counting it would refuse
    every ordinary pull request from the moment a skill first ran. It is opened by
    `friction.py` from the `Stop` hook rather than through the Bash tool, so this
    gate never sees that call either way — but the exemption has to be explicit,
    because the bug it prevents looks like the rule working.
  - ALLOWS whenever it cannot be sure — `gh` missing, not logged in, no network,
    malformed input. A gate that blocks work because GitHub was unreachable is worse
    than the thing it prevents. Never guesses.

There is no bypass flag. If the refusal is wrong, the user decides in chat, which is
the same shape as every other rule in CLAUDE.md.

A `PreToolUse` matcher can only name a tool, not a command, so this runs on every
Bash call in the project: about 38 ms, nearly all of it interpreter startup. Nothing
is spawned and GitHub is not asked unless the command really opens a request, so the
cost does not grow. `tools/test_one_pr.py` covers 36 cases; run it after any edit.
"""

import json
import re
import shlex
import subprocess
import sys

# The friction loop's standing request lives on this prefix and does not count.
FRICTION = "friction/"

# Where one command ends and the next begins, as shlex hands them over.
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")"}

# `cat <<'TAG'`, `<<-TAG`, `<< "TAG"` — the start of a heredoc, whose body is data.
HEREDOC = re.compile(r"<<-?\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)[\"']?")

# Fallback only, for a line shlex cannot lex (an unbalanced quote). Anchored to a
# command position, which a bare substring search is not.
CREATE_RE = re.compile(r"^\s*gh\s+[^\n;&|]*?\bpr\s+create\b")


def _line_opens_a_pr(line: str) -> bool:
    """True when this one line runs `gh ... pr create` as a command.

    Lexed, not pattern-matched. A regex cannot see quoting, so it reads
    `grep "gh pr create"`, an echoed JSON payload and a heredoc as the real thing —
    including this file's own tests, which is how that flaw was found. shlex keeps a
    quoted string as one token, so `gh` only counts where the shell would treat it
    as a command name.
    """
    try:
        lex = shlex.shlex(line, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return bool(CREATE_RE.search(line))   # unlexable: fall back, anchored

    def is_sep(tok: str) -> bool:
        return tok in SEPARATORS or (bool(tok) and all(c in ";&|()" for c in tok))

    at_start = True
    for i, token in enumerate(tokens):
        if is_sep(token):
            at_start = True
            continue
        if at_start and token == "gh":
            rest = []
            for later in tokens[i + 1:]:
                if is_sep(later):
                    break                  # this command's own words only
                rest.append(later)
            for j, word in enumerate(rest[:-1]):
                if word == "pr" and rest[j + 1] == "create":
                    return True
        at_start = False
    return False


def opens_a_pr(command: str) -> bool:
    """True when `command` would actually run `gh ... pr create`.

    A newline is a command separator, so every line is examined on its own — a
    `gh pr create` on its own line in a multi-line command is the normal shape and
    was the one real bypass in the first version of this file. Heredoc bodies are
    skipped, because a document that quotes the phrase is not a command that runs it.
    """
    command = command.replace("\\\n", " ")     # a continued line is one command
    pending: list[str] = []                    # heredoc terminators still open

    for line in command.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue                           # inside a heredoc: data, not a command
        for match in HEREDOC.finditer(line):
            pending.append(match.group(1))
        if _line_opens_a_pr(line):
            return True
    return False


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
            ("gh",) + args, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def branch_now() -> str:
    """The current branch, or "" if git cannot say (detached, no repo, no git)."""
    try:
        done = subprocess.run(
            ("git", "rev-parse", "--abbrev-ref", "HEAD"),
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        allow()

    if event.get("tool_name") != "Bash":
        allow()
    command = (event.get("tool_input") or {}).get("command") or ""
    if not opens_a_pr(command):
        allow()

    if branch_now().startswith(FRICTION):
        allow()  # a friction request is never the one to refuse

    raw = gh("pr", "list", "--state", "open", "--json", "number,title,headRefName")
    if raw is None:
        allow()  # cannot ask GitHub: not this hook's business to block on that
    try:
        open_prs = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        allow()
    # The standing friction request is exempt — see the module docstring.
    open_prs = [pr for pr in open_prs
                if not str(pr.get("headRefName", "")).startswith(FRICTION)]
    if not open_prs:
        allow()

    branch = branch_now()
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
