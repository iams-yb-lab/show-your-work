"""Test matrix for how `tools/friction.py` gets friction out of a machine.

Run it after touching that file: `python3 tools/test_friction_route.py`. Exits non-zero on any
failure. Nothing here touches the network, the real buffer, or GitHub: `FRICTION_STATE` points at a
temporary directory, `gh` is replaced by a table of answers, and the lab and the sender's fork are
local bare repositories.

Three things are worth testing and are all here:

  the route     who can push where, decided from two API answers and then cached
  the names     an inbox file and branch that do not collide between two senders
  the mechanics that a commit really lands on the right repository, carrying the whole tree

The mechanical case is the one that matters most. `flush` used to build its commit inside whatever
checkout it could find, which meant it could push a friction branch to the origin of the user's own
project. These cases build in a scratch repo of the loop's own and assert where the branch arrived.
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="friction-route-"))
fails = 0


def load(state: Path):
    """A fresh module, reading its state directory from the environment as it always does."""
    state.mkdir(parents=True, exist_ok=True)
    os.environ["FRICTION_STATE"] = str(state)
    spec = importlib.util.spec_from_file_location("friction_under_test", HERE / "friction.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check(name: str, got, want) -> None:
    global fails
    ok = got == want
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL':4}  {name}")
    if not ok:
        print(f"        got  {got!r}\n        want {want!r}")


def quietly(fn, *args, **kw):
    """Run it with its own printing swallowed. This file's output is the matrix, not the loop's."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kw)


def faker(*replies):
    """Stand in for `gh`. Each reply is (substring of the arguments, (ok, output)), tried in
    order; anything unmatched fails the way an unreachable API does."""
    def fake(*args, timeout=60):
        joined = " ".join(args)
        for needle, reply in replies:
            if needle in joined:
                return reply
        return False, ""
    return fake


# ------------------------------------------------------------------ the route

UP = "repos/iams-yb-lab/show-your-work"
MINE = "repos/someone/show-your-work"
FORK_TSV = "iams-yb-lab/show-your-work\thttps://github.com/someone/show-your-work.git"
FORK_URL = "https://github.com/someone/show-your-work.git"
WHO = ("api user", (True, "someone"))

ROUTE_CASES = [
    # name, gh answers, wanted route dict subset
    ("no gh at all", faker(("", (None, ""))), {"route": "stuck", "why": "no-gh"}),
    ("gh not signed in", faker(("api user", (False, "not logged in"))),
     {"route": "stuck", "why": "auth"}),
    ("signed in, GitHub unreachable", faker(WHO), {"route": "stuck", "why": "unreachable"}),
    ("push rights on the lab", faker(WHO, (UP, (True, "true"))),
     {"route": "direct", "url": "https://github.com/iams-yb-lab/show-your-work.git"}),
    ("read-only, fork already there",
     faker(WHO, (UP, (True, "false")), (MINE, (True, FORK_TSV))),
     {"route": "fork", "url": FORK_URL}),
    ("read-only, fork has to be made",
     faker(WHO, (UP, (True, "false")), ("repo fork", (True, "")), (MINE, (True, FORK_TSV))),
     {"route": "fork", "url": FORK_URL}),
    ("read-only, forking refused",
     faker(WHO, (UP, (True, "false"))), {"route": "stuck", "why": "fork"}),
    # A repository of the right name that is somebody's own project, not a fork of the lab: the
    # exact place a friction branch must never be pushed to.
    ("same name, not a fork of the lab",
     faker(WHO, (UP, (True, "false")), (MINE, (True, "\thttps://github.com/someone/x.git"))),
     {"route": "stuck", "why": "fork"}),
]

for i, (name, fake, want) in enumerate(ROUTE_CASES):
    m = load(TMP / f"route-{i}")
    m.gh = fake
    got = m.resolve_route()
    check(f"route: {name}", {k: got.get(k) for k in want}, want)

# The names. Bare host on the direct route, so the lab's existing inboxes are undisturbed; the
# handle in front on the fork route, because `mac` and `macbook-pro` collide between two senders.
m = load(TMP / "names")
m.gh = faker(WHO, (UP, (True, "true")))
check("name: direct route is the bare host", m.resolve_route()["name"], m.host())

m = load(TMP / "names-fork")
m.gh = faker(WHO, (UP, (True, "false")), (MINE, (True, FORK_TSV)))
check("name: fork route carries the handle", m.resolve_route()["name"], f"someone-{m.host()}")
check("slug: mixed case and dots", m.slug("Some.One_X"), "some-one-x")

# Cached, because it costs two API calls and almost never changes — and asked again on demand,
# because access can be granted or taken away.
m = load(TMP / "cache")
m.gh = faker(WHO, (UP, (True, "true")))
first = m.resolve_route()
m.gh = faker(("", (None, "")))                 # gh has vanished; the cache must still answer
check("cache: answered without asking again", m.resolve_route(), first)
check("cache: force re-asks", m.resolve_route(force=True)["route"], "stuck")


# -------------------------------------------------------------- the redaction

REDACT = [
    ("a plain rule", "Agree the voice on one line before generating the whole script", None),
    ("an absolute path", "the file was in /Users/someone/film", "an absolute path"),
    ("a Windows path", "it lived at C:\\Users\\someone", "an absolute path"),
    ("a home-relative path", "put it in ~/Movies/cut", "a home-relative path"),
    ("a UNC path", "the share \\\\studio\\renders was full", "a UNC path"),
    ("a file URL", "the log at file:///var/log said so", "a file:// URL"),
    ("an email address", "ask someone@example.com first", "an email address"),
    ("an at-sign that is not an address", "the @ in the name broke the glob", None),
]
m = load(TMP / "redact")
for name, value, want in REDACT:
    check(f"redaction: {name}", m.leak_in(value), want)


# ------------------------------------------------------------- the mechanics

def run(*args, cwd=None):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, cwd=cwd,
                       env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
    assert r.returncode == 0, f"{args}: {r.stderr.strip()}"
    return r.stdout.strip()


def build_lab(root: Path):
    """A lab repository with a `main`, and a fork of it — both bare, both local."""
    lab, fork, work = root / "lab.git", root / "fork.git", root / "work"
    run("git", "init", "--bare", "-q", lab)
    run("git", "init", "-q", "-b", "main", work)
    (work / "feedback").mkdir(parents=True)
    (work / "feedback" / "README.md").write_text("the format\n", encoding="utf-8")
    (work / "MAP.md").write_text("the map\n", encoding="utf-8")
    run("git", "add", "-A", cwd=work)
    run("git", "commit", "-q", "-m", "the lab", cwd=work)
    run("git", "push", "-q", lab, "main:main", cwd=work)
    run("git", "clone", "-q", "--bare", lab, fork)      # a fork: same objects, own refs
    return lab, fork


def entry(rule: str) -> dict:
    return {"date": "2026-08-23", "host": "testbox", "skill": "natural-voice", "gate": "",
            "complaint": "c", "mistake": "mi", "fix": "f", "rule": rule}


def files_on(repo: Path, ref: str) -> list[str]:
    return sorted(run("git", "-C", repo, "ls-tree", "-r", "--name-only", ref).splitlines())


LAB, FORK = build_lab(TMP / "world")
NAME = "someone-testbox"
BRANCH, INBOX = f"friction/{NAME}", f"feedback/inbox/{NAME}.md"
ROUTE = {"route": "fork", "url": str(FORK), "name": NAME, "login": "someone"}

m = load(TMP / "mech")
m.UPSTREAM_URL = str(LAB)                 # the lab, as this test's world knows it
m.open_pr = lambda *a, **k: None          # opening a request is gh's job, tested above

# --check says what it would do and changes nothing.
check("mechanics: --check reports", quietly(m.send, ROUTE, [entry("first rule")], True), True)
check("mechanics: --check pushed nothing",
      subprocess.run(["git", "-C", str(FORK), "rev-parse", "--verify", "--quiet",
                      f"refs/heads/{BRANCH}"], capture_output=True).returncode != 0, True)

# First real send: the branch appears on the fork, not on the lab.
check("mechanics: first send", quietly(m.send, ROUTE, [entry("first rule")], False), True)
check("mechanics: branch is on the fork",
      bool(run("git", "-C", FORK, "rev-parse", f"refs/heads/{BRANCH}")), True)
check("mechanics: the lab got nothing",
      subprocess.run(["git", "-C", str(LAB), "rev-parse", "--verify", "--quiet",
                      f"refs/heads/{BRANCH}"], capture_output=True).returncode != 0, True)
check("mechanics: branch keeps the one-pr exemption prefix", BRANCH.startswith("friction/"), True)

# The whole tree travels, plus exactly one new file. A branch that dropped the repository would
# still push and would still open a request.
check("mechanics: whole tree, one file added",
      files_on(FORK, BRANCH), sorted(files_on(LAB, "main") + [INBOX]))

body = run("git", "-C", FORK, "cat-file", "blob", f"refs/heads/{BRANCH}:{INBOX}")
check("mechanics: inbox has its header", f"# Friction from `{NAME}`" in body, True)
check("mechanics: inbox has the entry", "first rule" in body, True)

# Second send accumulates onto the branch rather than replacing it.
check("mechanics: second send", quietly(m.send, ROUTE, [entry("second rule")], False), True)
body = run("git", "-C", FORK, "cat-file", "blob", f"refs/heads/{BRANCH}:{INBOX}")
check("mechanics: first entry survived", "first rule" in body, True)
check("mechanics: second entry appended", "second rule" in body, True)
check("mechanics: one commit per send",
      len(run("git", "-C", FORK, "log", "--format=%h", BRANCH).splitlines()), 3)

# The user's own repositories are not touched: the loop worked entirely inside its own bare repo.
check("mechanics: scratch repo is the loop's own", (m.SCRATCH / "HEAD").is_file(), True)
check("mechanics: nothing was cloned into the world",
      sorted(p.name for p in (TMP / "world").iterdir()), ["fork.git", "lab.git", "work"])

# A route that cannot be reached loses nothing: the buffer is the record until a push succeeds.
m.PENDING.write_text(json.dumps(entry("held back")) + "\n", encoding="utf-8")
dead = dict(ROUTE, url=str(TMP / "world" / "nowhere.git"))
check("mechanics: unreachable route sends nothing", quietly(m.send, dead, [entry("held back")], False),
      False)
check("mechanics: buffer kept", "held back" in m.PENDING.read_text(encoding="utf-8"), True)


# --------------------------------- flush end to end, including the re-resolve

class Args:
    check = False


m = load(TMP / "flush")
m.UPSTREAM_URL = str(LAB)
m.open_pr = lambda *a, **k: None
m.PENDING.parent.mkdir(parents=True, exist_ok=True)
m.PENDING.write_text(json.dumps(entry("flushed rule")) + "\n", encoding="utf-8")
# A cached route that has gone stale — the shape of losing access, or of a fork being deleted.
m.ROUTE.write_text(json.dumps(dict(ROUTE, url=str(TMP / "world" / "gone.git"))), encoding="utf-8")
m.gh = faker(WHO, (UP, (True, "false")), (MINE, (True, f"iams-yb-lab/show-your-work\t{FORK}")))

check("flush: exits 0", quietly(m.cmd_flush, Args()), 0)
check("flush: buffer emptied", m.PENDING.read_text(encoding="utf-8").strip(), "")
check("flush: kept a copy of what left",
      "flushed rule" in m.FLUSHED.read_text(encoding="utf-8"), True)
check("flush: re-resolved past the stale route",
      json.loads(m.ROUTE.read_text(encoding="utf-8"))["url"], str(FORK))
check("flush: landed on the branch",
      "flushed rule" in run("git", "-C", FORK, "cat-file", "blob",
                            f"refs/heads/friction/someone-{m.host()}:"
                            f"feedback/inbox/someone-{m.host()}.md"), True)

# Nothing to send is not a failure, and must not resolve a route or touch anything.
m2 = load(TMP / "empty")
m2.gh = faker(("", (None, "")))
check("flush: empty buffer exits 0", quietly(m2.cmd_flush, Args()), 0)
check("flush: empty buffer decided no route", m2.ROUTE.is_file(), False)


# ------------------------------------------ the one thing allowed to be said

m3 = load(TMP / "auth")
m3.gh = faker(("api user", (False, "not logged in")))
m3.PENDING.parent.mkdir(parents=True, exist_ok=True)
m3.PENDING.write_text(json.dumps(entry("waiting on auth")) + "\n", encoding="utf-8")
said = []
m3.out_json = said.append
check("auth: exits 0", quietly(m3.cmd_flush, Args()), 0)
check("auth: says it once", len(said), 1)
check("auth: names the command", "gh auth login" in said[0]["systemMessage"], True)
check("auth: buffer kept", "waiting on auth" in m3.PENDING.read_text(encoding="utf-8"), True)
check("auth: exits 0 again", quietly(m3.cmd_flush, Args()), 0)
check("auth: never says it twice", len(said), 1)

shutil.rmtree(TMP, ignore_errors=True)
print("\nALL PASS" if not fails else f"\n{fails} FAILURE(S)")
sys.exit(1 if fails else 0)
