#!/usr/bin/env python3
"""Bring this machine's copy of the skills up to date with GitHub, at the start of a session.

    update.py hook     SessionStart hook — check, apply what is safe, stay silent when current
    update.py check    say what it would do, change nothing
    update.py apply    do it now, with human output

Two places this runs, and it works out which by looking at what is around it:

  the checkout   fetch the lab and fast-forward, if that is all it takes. The skills here ARE
                 the installation, so a fast-forward is the whole update.

  a project the skills were installed into   update the checkout on this machine first — found by
                 the pointer `install_skills.py` leaves at ~/.claude/skill-friction/home.txt — then
                 re-install the payload into this project from it. With no checkout on the machine
                 there is nothing to update from, and it says so rather than looking successful.

The lab — `iams-yb-lab/show-your-work` — is named here as an identity, not discovered from the
checkout's remotes. `origin` is trusted only when it *is* the lab: on a fork `origin` is the fork,
and a fork that has fallen behind would otherwise update the skills to its own stale copy and report
success. Off the lab, the lab's `main` is fetched by URL into a ref of this tool's own, so no remote
is added to anyone's checkout and nothing new appears in their branch list.

What it overwrites and what it will not: `install_skills.py --update` draws that line, and the
reasoning lives there. Short version — the read-only files are replaced, the method and the records
are only ever added to.

Three contracts, the same ones friction.py works under:

  Never bother the user.   No prompt, no question, no mid-run interruption. A line of context when
                           something happened, silence when nothing did.
  Never break a turn.      Every path exits 0. Git missing, no network, no rights: say nothing
                           and try again next session.
  Never touch work.        Fast-forward only. A diverged or dirty checkout is reported and left
                           exactly as it is — never merged, never rebased, never stashed.

Turn it off on one machine with SHOW_YOUR_WORK_UPDATE=off in the environment; `check` and `apply`
still work by hand. `tools/test_update_route.py` covers where an update comes from against local
repositories standing in for the lab and a fork; run it after any edit.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Do not anchor on the checkout: walk up to the tree that holds the skills. Works whether this file
# sits in <checkout>/tools/ or, once installed, in <project>/.claude/skills/_shared/tools/.
ROOT = next((p for p in Path(__file__).resolve().parents
             if (p / ".claude" / "skills" / "natural-voice").is_dir()), None)

# Machine-local state, shared with friction.py because home.txt — the pointer to the checkout — is
# already there and both halves need it. Overridable so the whole path can be exercised on a
# scratch clone without touching the real one.
STATE = Path(os.environ.get("FRICTION_STATE")
             or Path.home() / ".claude" / "skill-friction").expanduser()
HOME_TXT = STATE / "home.txt"
MEMO = STATE / "update.json"

# The lab, named as an identity and not as a path — the one repository the skills update from.
# friction.py carries the same constant for the same reason, so take it from there when it is beside
# us and a rename cannot move one and leave the other behind.
try:
    from friction import UPSTREAM as LAB
except Exception:                         # a neighbour that will not import must not stop a session
    LAB = "iams-yb-lab/show-your-work"
LAB_URL = f"https://github.com/{LAB}.git"
LAB_REF = "refs/show-your-work/lab-main"  # this tool's own namespace: no remote, no branch, no tag
LAB_MAIN = "the lab's main"               # how the messages name it, and how run() spots the route

# Every form git accepts for that one repository, and nothing that merely contains its name: a host
# of anything but github.com is somebody else's server.
LAB_URL_RE = re.compile(r"^(?:(?:https?|ssh|git)://)?(?:[^@/]+@)?github\.com(?::\d+)?[:/]"
                        + re.escape(LAB) + r"$", re.I)

HOOK_SECONDS = 150        # what the SessionStart hook may spend copying, under its own timeout
MIN_GAP_MINUTES = 15      # a resume five minutes later does not need to ask GitHub again
STALE_DAYS = 7            # offline this long and you deserve to be told you might be behind
OFF_VALUES = {"off", "0", "no", "never", "false"}


def disabled() -> bool:
    return os.environ.get("SHOW_YOUR_WORK_UPDATE", "").strip().lower() in OFF_VALUES


def read_hook() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, OSError):
        return {}


def git(repo: Path, *args, timeout: int = 30):
    """Run git, return (ok, output). Never raises — a helper must not be why a turn fails."""
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                                "GCM_INTERACTIVE": "never"})
        return r.returncode == 0, (r.stdout or "").strip() or (r.stderr or "").strip()
    except (OSError, subprocess.SubprocessError):
        return False, ""


def first_line(text: str) -> str:
    return (text or "").strip().splitlines()[0][:160] if (text or "").strip() else ""


# ------------------------------------------------------------------ where we are

def is_checkout(p: Path | None) -> bool:
    """The repository itself, as opposed to a project the skills were installed into: only the
    checkout carries the installer."""
    return bool(p) and (p / "tools" / "install_skills.py").is_file() and (p / ".claude" / "skills").is_dir()


def home_checkout() -> Path | None:
    """The clone on this machine, if one is known and still looks like itself."""
    cands = []
    if HOME_TXT.is_file():
        try:
            cands.append(Path(HOME_TXT.read_text(encoding="utf-8").strip()).expanduser())
        except OSError:
            pass
    cands.append(ROOT)
    for c in cands:
        if is_checkout(c):
            return c
    return None


# ------------------------------------------------------------------ memo (local)

def load_memo() -> dict:
    try:
        return json.loads(MEMO.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def save_memo(memo: dict) -> None:
    try:
        MEMO.parent.mkdir(parents=True, exist_ok=True)
        MEMO.write_text(json.dumps(memo), encoding="utf-8")
    except OSError:
        pass                              # a memo we cannot write costs one extra fetch, nothing more


def since(stamp: str | None) -> float:
    """Minutes since an ISO stamp; a very large number if there is no usable one."""
    try:
        return (datetime.now() - datetime.fromisoformat(stamp)).total_seconds() / 60
    except (TypeError, ValueError):
        return float(10 ** 9)


# ------------------------------------------------------------------ the git half

def names_lab(url: str) -> bool:
    """True if a remote URL is the lab itself, in any of the forms git accepts for it."""
    u = (url or "").strip().rstrip("/")
    return bool(LAB_URL_RE.match(u[:-4] if u.lower().endswith(".git") else u))


def upstream_of(repo: Path) -> tuple[str, str]:
    """What this checkout must measure itself against: (ref to compare, how to name it).

    `origin` is used only where it is the lab. Everywhere else — a fork, or a checkout whose remote
    was pointed somewhere private — the lab's own `main` is the answer, because a fork answers
    "current" while the skills inside it sit months behind."""
    ok, url = git(repo, "remote", "get-url", "origin")
    if ok and names_lab(url):
        return "@{upstream}", ""
    return LAB_REF, LAB_MAIN


def sync(repo: Path, apply: bool) -> tuple[str, str, int, str]:
    """Fetch, then fast-forward if that is all it takes. Returns (state, detail, commits behind,
    what it compared against).

    States that mean *do not act*: no-git, detached, no-upstream, offline (all silent), diverged and
    blocked (both reported — they need a person). current and ahead are fine as they are; the Stop
    hook is what pushes `ahead`."""
    if not git(repo, "rev-parse", "--git-dir")[0]:
        return "no-git", "", 0, ""
    ok, branch = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    if not ok or not branch:
        return "detached", "", 0, ""

    ref, src = upstream_of(repo)
    src = src or f"origin/{branch}"
    if ref == LAB_REF:
        # By URL and into a ref of our own: no remote is added to someone else's checkout, nothing
        # appears in their branch list, and no `origin` anywhere can redirect this.
        if not git(repo, "fetch", "--quiet", "--no-tags", LAB_URL,
                   f"+refs/heads/main:{LAB_REF}", timeout=45)[0]:
            return "offline", branch, 0, src
    else:
        if not git(repo, "rev-parse", "--abbrev-ref", "@{upstream}")[0]:
            return "no-upstream", branch, 0, src
        if not git(repo, "fetch", "--quiet", "origin", timeout=45)[0]:
            return "offline", branch, 0, src

    ok, counts = git(repo, "rev-list", "--left-right", "--count", f"{ref}...HEAD")
    try:
        behind, ahead = (int(x) for x in counts.split())
    except (ValueError, AttributeError):
        return "offline", branch, 0, src
    if behind == 0:
        return ("ahead" if ahead else "current"), branch, ahead, src
    if ahead:
        return "diverged", branch, behind, src
    if not apply:
        return "behind", branch, behind, src

    # Fast-forward only. Git refuses this itself if a local change would be overwritten, which is
    # the safety we want — no dirty-tree guess of our own, no stash, no rebase.
    ok, msg = git(repo, "merge", "--ff-only", ref, timeout=60)
    return ("updated", branch, behind, src) if ok else ("blocked", first_line(msg), behind, src)


def verify(repo: Path) -> str:
    """Run the checker that travelled with the update. A pull that lands broken must not be quiet."""
    for rel in ("tools/check_links.py", ".claude/skills/_shared/tools/check_links.py",
                "video/tools/check_links.py"):
        script = repo / rel
        if not script.is_file():
            continue
        try:
            r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                               timeout=120, cwd=str(repo))
        except (OSError, subprocess.SubprocessError):
            return ""
        if r.returncode != 0:
            return first_line((r.stdout or "") + "\n" + (r.stderr or "")) or "check_links.py failed"
        return ""
    return ""


# --------------------------------------------------------------- the install half

def reinstall(clone: Path, target: Path, apply: bool, budget: int) -> tuple[str, bool]:
    """Re-install the payload from the clone into this project. Returns (summary line, ok).

    `budget` is seconds: generous by hand, short in the hook, because a SessionStart hook that
    overruns its own timeout is killed mid-copy. A cut-short copy leaves files that differ, which
    is exactly what the next run notices and replaces."""
    script = clone / "tools" / "install_skills.py"
    if not script.is_file():
        return "", True
    argv = [sys.executable, str(script), str(target), "--update"] + ([] if apply else ["--check"])
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=budget, cwd=str(clone))
    except (OSError, subprocess.SubprocessError):
        return "", True
    out = (r.stdout or "") + (r.stderr or "")
    line = next((q.strip() for q in out.splitlines() if q.startswith("update:")), "")
    return line, r.returncode == 0


# ---------------------------------------------------------------------- the work

def run(apply: bool, budget: int = 900) -> tuple[list[str], list[str]]:
    """Do the update. Returns (notable lines, quiet lines) — the hook prints the first list only."""
    notable, quiet = [], []
    if ROOT is None:
        return notable, ["not inside a tree that holds .claude/skills/natural-voice/ — "
                         "nothing to update"]

    here_is_checkout = is_checkout(ROOT)
    clone = ROOT if here_is_checkout else home_checkout()

    if clone is None:
        quiet.append("no show-your-work checkout on this machine")
        if occasionally("no-clone"):
            notable.append(
                "The skills installed here cannot update themselves: no show-your-work checkout "
                "on this machine. Clone it, then run its tools/install_skills.py on this project.")
        return notable, quiet

    state, detail, n, src = sync(clone, apply)
    where = "" if here_is_checkout else " (the checkout the skills came from)"
    plural = "commit" if n == 1 else "commits"

    if state == "updated":
        notable.append(f"Updated the skills to {src}{where}: {n} new {plural} from GitHub.")
        if (bad := verify(clone)):
            notable.append(f"But the check on the new version FAILS: {bad}")
    elif state == "behind":
        notable.append(f"{n} {plural} behind {src}{where} — not applied (check only).")
    elif state == "diverged":
        notable.append(f"The checkout{where} has diverged from {src}: {n} {plural} behind "
                       f"and local commits of its own. Left alone; it needs a person.")
    elif state == "blocked":
        notable.append(f"{n} {plural} behind {src}, and the fast-forward was refused: {detail}. "
                       f"Nothing was changed.")
    else:
        quiet.append(f"checkout: {state}" + (f" ({detail})" if detail else ""))

    fetched = state in {"current", "ahead", "updated", "behind", "diverged", "blocked"}
    # Worth saying once, and only once: the answers above came from somewhere other than the remote
    # this checkout was cloned from, and someone reading them would otherwise assume `origin`.
    if fetched and src == LAB_MAIN and occasionally("not-the-lab"):
        notable.append(f"This checkout's `origin` is not the lab, so the skills were measured "
                       f"against {LAB} itself rather than against `origin`.")
    if fetched:
        stamp("last_ok")
    elif state == "offline" and (age := since(slot().get("last_ok"))) > STALE_DAYS * 24 * 60:
        if occasionally("stale"):
            notable.append(f"Cannot reach GitHub. This copy of the skills was last confirmed "
                           f"current {int(age / 60 / 24)} days ago, so it may be behind.")

    # In a project, the skills are a copy. Refresh it whether or not the checkout moved: the copy
    # can be stale on its own — installed once, months ago, and never touched since.
    if not here_is_checkout and state != "no-git":
        line, ok = reinstall(clone, ROOT, apply, budget)
        # The installer's own summary line: "update: N file(s) refreshed|stale, M left alone".
        counts = [int(w) for w in line.split() if w.isdigit()]
        count, left = (counts + [0, 0])[:2]
        also = (f" {left} method or example file(s) differ from the checkout and were left "
                f"alone — "
                f"run the installer with --force to replace those too.") if left else ""
        if count and apply:
            notable.append(f"Refreshed {count} installed file(s) in this project from the "
                           f"checkout.{also}")
        elif count:
            notable.append(f"{count} installed file(s) here are behind the checkout — not "
                           f"applied.{also}")
        elif line:
            quiet.append(line)
        if not ok:
            quiet.append("install_skills.py --update reported a problem")
    return notable, quiet


# The memo is keyed per tree, because one machine can have the checkout and several projects.
_SLOT: dict = {}


def slot() -> dict:
    if not _SLOT:
        _SLOT.update(load_memo().get(str(ROOT), {}))
    return _SLOT


def stamp(key: str) -> None:
    slot()[key] = datetime.now().isoformat(timespec="seconds")


def occasionally(key: str) -> bool:
    """True at most once a week per tree, so a standing condition is a note and not a nag."""
    if since(slot().get(f"said-{key}")) < STALE_DAYS * 24 * 60:
        return False
    stamp(f"said-{key}")
    return True


def flush_memo() -> None:
    if not _SLOT:
        return
    memo = load_memo()
    memo[str(ROOT)] = {**memo.get(str(ROOT), {}), **_SLOT}
    save_memo(memo)


# -------------------------------------------------------------------- commands

def cmd_hook(_a) -> int:
    hook = read_hook()
    if hook.get("source") == "compact":
        return 0                          # mid-session: a summary is not a reason to change files
    if disabled() or ROOT is None:
        return 0
    if since(slot().get("last_try")) < MIN_GAP_MINUTES:
        return 0
    stamp("last_try")
    flush_memo()

    notable, _ = run(apply=True, budget=HOOK_SECONDS)
    flush_memo()
    if not notable:
        return 0                          # nothing to say: stay silent
    text = " ".join(notable)
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "SessionStart",
                               "additionalContext": "show-your-work update check: " + text},
        "systemMessage": "skills: " + text[:300],
    }))
    return 0


def cmd_report(a) -> int:
    if disabled():
        print("SHOW_YOUR_WORK_UPDATE is off in this environment; the hook does nothing. "
              "This run ignores that.")
    notable, quiet = run(apply=a.cmd == "apply")
    for line in notable:
        print(line)
    for line in quiet:
        print(f"({line})")
    if not notable and not quiet:
        print("already current with the lab.")
    flush_memo()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hook", help="SessionStart hook: apply what is safe, silent when current")
    sub.add_parser("check", help="report only; change nothing")
    sub.add_parser("apply", help="update now, with human output")
    a = ap.parse_args(argv)
    a.cmd = a.cmd or "check"
    try:
        return cmd_hook(a) if a.cmd == "hook" else cmd_report(a)
    except Exception as exc:              # a session must start even if this file has a bug
        if a.cmd != "hook":
            print(f"update failed: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
