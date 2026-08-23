"""Test matrix for where `tools/update.py` takes an update from.

Run it after touching that file: `python3 tools/test_update_route.py`. Exits non-zero on any
failure. Nothing here touches the network or the real checkout: the lab and a fork of it are local
bare repositories, `LAB_URL` is pointed at the local lab, and `FRICTION_STATE` is a temporary
directory.

The case that matters is the one the live routes found in `friction.py` and this file had one door
along: a project installed from a **fork** that has fallen behind. Its `origin` is the fork, the
fork says "current", and the skills sit at whatever the fork last saw — silently. So every case here
asserts *which repository the content arrived from*, not merely that something happened.
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="update-route-"))
fails = 0


def load(state: Path, lab_url: str | None = None):
    """A fresh module, reading its state directory from the environment as it always does."""
    state.mkdir(parents=True, exist_ok=True)
    os.environ["FRICTION_STATE"] = str(state)
    spec = importlib.util.spec_from_file_location("update_under_test", HERE / "update.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if lab_url:
        m.LAB_URL = lab_url               # the lab, as this test's world knows it
    return m


def check(name: str, got, want) -> None:
    global fails
    ok = got == want
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL':4}  {name}")
    if not ok:
        print(f"        got  {got!r}\n        want {want!r}")


def run(*args, cwd=None):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, cwd=cwd,
                       env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
    assert r.returncode == 0, f"{args}: {r.stderr.strip()}"
    return r.stdout.strip()


def has_ref(repo: Path, ref: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", ref],
                          capture_output=True).returncode == 0


# ---------------------------------------------------- is this remote the lab itself

M = load(TMP / "urls")
LAB = M.LAB

URLS = [
    ("https", f"https://github.com/{LAB}.git", True),
    ("https, no suffix", f"https://github.com/{LAB}", True),
    ("https, trailing slash", f"https://github.com/{LAB}/", True),
    ("scp form", f"git@github.com:{LAB}.git", True),
    ("ssh URL", f"ssh://git@github.com/{LAB}.git", True),
    ("ssh URL with a port", f"ssh://git@github.com:22/{LAB}.git", True),
    ("shouting", f"HTTPS://GitHub.com/{LAB.upper()}.GIT", True),
    # Everything a fork or a project looks like. Trusting any of these is the bug.
    ("somebody's fork", "https://github.com/someone/show-your-work.git", False),
    ("the same name elsewhere", "https://gitlab.com/" + LAB + ".git", False),
    ("a host that only mentions it", f"https://elsewhere.example/github.com/{LAB}.git", False),
    ("the lab's name inside a longer one", f"https://github.com/{LAB}-mirror.git", False),
    ("a local path", "/home/someone/show-your-work", False),
    ("no remote at all", "", False),
]
for name, url, want in URLS:
    check(f"is the lab: {name}", M.names_lab(url), want)


# ------------------------------------------------------------------- the mechanics

def world(root: Path):
    """A lab that moved on, and a fork of it that stopped one commit back."""
    lab, fork, work = root / "lab.git", root / "fork.git", root / "labwork"
    run("git", "init", "--bare", "-q", lab)
    run("git", "symbolic-ref", "HEAD", "refs/heads/main", cwd=lab)
    run("git", "init", "-q", "-b", "main", work)
    (work / "tools").mkdir(parents=True)
    (work / "tools" / "install_skills.py").write_text("# the installer\n", encoding="utf-8")
    (work / ".claude" / "skills" / "natural-voice").mkdir(parents=True)
    (work / ".claude" / "skills" / "natural-voice" / "SKILL.md").write_text("v1\n", encoding="utf-8")
    run("git", "add", "-A", cwd=work)
    run("git", "commit", "-q", "-m", "the lab", cwd=work)
    run("git", "push", "-q", lab, "main:main", cwd=work)
    run("git", "clone", "-q", "--bare", lab, fork)     # the fork: stops at this commit
    # The lab moves on. This file exists nowhere but the lab, so it is the proof of where an
    # update came from.
    (work / ".claude" / "skills" / "natural-voice" / "SKILL.md").write_text("v2\n", encoding="utf-8")
    (work / "LATEST-FROM-THE-LAB.md").write_text("only the lab has this\n", encoding="utf-8")
    run("git", "add", "-A", cwd=work)
    run("git", "commit", "-q", "-m", "the lab moved on", cwd=work)
    run("git", "push", "-q", lab, "main:main", cwd=work)
    return lab, fork


LAB_GIT, FORK_GIT = world(TMP / "world")
PROOF = "LATEST-FROM-THE-LAB.md"


def clone_of(remote: Path, name: str) -> Path:
    dest = TMP / "clones" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    run("git", "clone", "-q", remote, dest)
    return dest


# A checkout of the fork. Against its own `origin` it is perfectly up to date, which is exactly
# how the skills inside it went stale without anyone being told.
fork_co = clone_of(FORK_GIT, "fork")
m = load(TMP / "fork", str(LAB_GIT))
check("fork: `origin` is not the lab", m.names_lab(run("git", "-C", fork_co, "remote", "get-url",
                                                       "origin")), False)
check("fork: current against its own origin",
      run("git", "-C", fork_co, "rev-list", "--count", "@{upstream}...HEAD"), "0")

state, _, n, src = m.sync(fork_co, apply=False)
check("fork: check sees it is behind the lab", (state, n), ("behind", 1))
check("fork: and says what it measured against", src, m.LAB_MAIN)
check("fork: check changed nothing", (fork_co / PROOF).is_file(), False)

state, _, n, src = m.sync(fork_co, apply=True)
check("fork: apply fast-forwards", (state, n), ("updated", 1))
check("fork: the lab's content arrived", (fork_co / PROOF).is_file(), True)
check("fork: and the skill is the lab's version",
      (fork_co / ".claude/skills/natural-voice/SKILL.md").read_text(encoding="utf-8"), "v2\n")
check("fork: fetched into a ref of our own", has_ref(fork_co, m.LAB_REF), True)
check("fork: no remote was added to the checkout",
      run("git", "-C", fork_co, "remote"), "origin")
check("fork: no branch was added either",
      run("git", "-C", fork_co, "branch", "--format=%(refname:short)"), "main")

# Where `origin` *is* the lab, nothing changes: the branch the person is on is what they are
# measured against, and no second fetch is invented. An absent lab-ref is the proof.
lab_co = clone_of(LAB_GIT, "lab")
run("git", "-C", lab_co, "reset", "-q", "--hard", "HEAD~1")   # one behind, tracking the lab
m = load(TMP / "lab", str(LAB_GIT))
m.names_lab = lambda url: True                                # this local path stands in for the lab
state, detail, n, src = m.sync(lab_co, apply=True)
check("lab: apply fast-forwards", (state, n), ("updated", 1))
check("lab: measured against the branch's own upstream", src, f"origin/{detail}")
check("lab: no lab-ref was fetched", has_ref(lab_co, m.LAB_REF), False)

# A checkout with no `origin` at all used to be a dead end — "no-remote", nothing done. The lab is
# named, so there is always somewhere to update from.
bare_co = clone_of(FORK_GIT, "no-remote")
run("git", "-C", bare_co, "remote", "remove", "origin")
m = load(TMP / "no-remote", str(LAB_GIT))
state, _, n, src = m.sync(bare_co, apply=True)
check("no origin: still updates from the lab", (state, n, src), ("updated", 1, m.LAB_MAIN))
check("no origin: the lab's content arrived", (bare_co / PROOF).is_file(), True)

# Work of its own on top: reported, and left exactly as it is.
mine_co = clone_of(FORK_GIT, "diverged")
(mine_co / "mine.md").write_text("my own work\n", encoding="utf-8")
run("git", "-C", mine_co, "add", "-A")
run("git", "-C", mine_co, "commit", "-q", "-m", "mine")
head = run("git", "-C", mine_co, "rev-parse", "HEAD")
m = load(TMP / "diverged", str(LAB_GIT))
state, _, n, src = m.sync(mine_co, apply=True)
check("diverged: reported against the lab", (state, n, src), ("diverged", 1, m.LAB_MAIN))
check("diverged: history untouched", run("git", "-C", mine_co, "rev-parse", "HEAD"), head)
check("diverged: own work still there", (mine_co / "mine.md").is_file(), True)

# A lab that cannot be reached is silent, never an error.
gone_co = clone_of(FORK_GIT, "offline")
m = load(TMP / "offline", str(TMP / "world" / "nowhere.git"))
state, _, n, _ = m.sync(gone_co, apply=True)
check("offline: silent state", (state, n), ("offline", 0))
check("offline: nothing arrived", (gone_co / PROOF).is_file(), False)


# ------------------------------------------------------------- what the user reads

whole_co = clone_of(FORK_GIT, "reported")
m = load(TMP / "reported", str(LAB_GIT))
m.ROOT = whole_co
notable, _ = m.run(apply=True)
check("report: says the update came from the lab",
      any(f"Updated the skills to {m.LAB_MAIN}" in line for line in notable), True)
check("report: names the lab once, because origin is not it",
      sum(m.LAB in line for line in notable), 1)

notable, _ = m.run(apply=True)
check("report: current, so nothing to say", notable, [])
check("report: and the note is not repeated",
      any(m.LAB in line for line in m.run(apply=True)[0]), False)


print(f"\n{'all passed' if not fails else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)
