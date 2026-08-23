"""Test matrix for `.claude/hooks/one-pr.py` — the one-open-pull-request gate.

Run it after touching that hook: `python3 tools/test_one_pr.py`. Exits non-zero on
any failure. Two of these cases are regressions, both found by this file denying the
command that ran it: a quoted `&& gh pr create` inside a larger command, and a real
create on its own line in a multi-line script.
"""
import importlib.util
import io
import json
import sys
from pathlib import Path

P = str(Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "one-pr.py")
CREATE = "gh" + " pr create"          # split so this file never trips the hook it tests


def load():
    spec = importlib.util.spec_from_file_location("onepr", P)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(command, prs, branch, tool="Bash"):
    m = load()
    m.gh = (lambda *a: None) if prs is None else (lambda *a: json.dumps(prs))
    m.branch_now = lambda: branch
    sys.stdin = io.StringIO(json.dumps({"tool_name": tool, "tool_input": {"command": command}}))
    buf, real = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        m.main()
    except SystemExit:
        pass
    sys.stdout = real
    out = buf.getvalue().strip()
    if not out:
        return "allow", ""
    return "DENY", json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


WORK = [{"number": 8, "title": "One folder per skill",
         "headRefName": "restructure/one-folder-per-skill"}]
FRIC = [{"number": 9, "title": "friction from mac", "headRefName": "friction/mac"}]

CASES = [
    # --- the rule itself ---
    ("work PR open, new branch",        CREATE + " --fill",        WORK, "my/new", "DENY"),
    ("work PR open, same branch",       CREATE + " --fill",        WORK,
     "restructure/one-folder-per-skill", "DENY"),
    ("nothing open",                    CREATE + " --fill",        [],   "my/new", "allow"),
    ("two work PRs open",               CREATE + " --fill",
     WORK + [{"number": 7, "title": "Other", "headRefName": "b"}], "my/new", "DENY"),

    # --- the friction loop must never be blocked, and must never block ---
    ("only friction PR open",           CREATE + " --fill",        FRIC, "my/new", "allow"),
    ("friction + work open",            CREATE + " --fill", FRIC + WORK, "my/new", "DENY"),
    ("on a friction branch",            CREATE + " --fill",        WORK, "friction/mac", "allow"),

    # --- must never block on infrastructure ---
    ("GitHub unreachable",              CREATE + " --fill",        None, "my/new", "allow"),
    ("detached HEAD, nothing open",     CREATE + " --fill",        [],   "",       "allow"),

    # --- real creates, various shapes ---
    ("after &&",   "git push -u origin x && " + CREATE + " -f",    WORK, "my/new", "DENY"),
    ("after ;",    "git push ; " + CREATE,                         WORK, "my/new", "DENY"),
    ("newline",    "git push\n" + CREATE + " --fill",              WORK, "my/new", "DENY"),
    ("global flag", "gh --repo o/r pr create --fill",              WORK, "my/new", "DENY"),
    ("extra spaces", "gh   pr   create   --fill",                  WORK, "my/new", "DENY"),

    # --- mentions that are not creates ---
    ("gh pr list",   "gh pr list --state open",                    WORK, "my/new", "allow"),
    ("gh pr merge",  "gh pr merge 8 --squash",                     WORK, "my/new", "allow"),
    ("gh pr view",   "gh pr view 8",                               WORK, "my/new", "allow"),
    ("gh pr comment", "gh pr comment 8 --body x",                  WORK, "my/new", "allow"),
    ("plain push",   "git push -u origin my/new",                  WORK, "my/new", "allow"),
    ("echoed JSON",  "echo '{\"c\":\"" + CREATE + "\"}'",          WORK, "my/new", "allow"),
    ("grep for it",  'grep -rn "' + CREATE + '" .',                WORK, "my/new", "allow"),
    ("quoted with &&", 'echo "x && ' + CREATE + '"',               WORK, "my/new", "allow"),
    ("heredoc body", "cat <<'E'\n" + CREATE + "\nE",               WORK, "my/new", "allow"),
    ("in a filename", "cat notes-" + CREATE.replace(" ", "-") + ".txt", WORK, "my/new", "allow"),
    # `echo 'unclosed gh pr create` runs no create, so allow is right; the fallback
    # regex is anchored, so it only fires when the LINE starts with gh.
    ("unbalanced quote, not a create", "echo 'unclosed " + CREATE, WORK, "my/new", "allow"),
    ("unbalanced quote, real create", CREATE + " --title 'unclosed", WORK, "my/new", "DENY"),
    ("empty command", "",                                          WORK, "my/new", "allow"),
    ("multi-line script, create on own line",
     "set -e\ngit add -A\ngit commit -m x\n" + CREATE + " --fill", WORK, "my/new", "DENY"),
    ("indented on own line", "if true; then\n  " + CREATE + "\nfi", WORK, "my/new", "DENY"),
    ("line continuation", CREATE + " \\\n  --title x",             WORK, "my/new", "DENY"),
    ("heredoc, phrase inside", "cat > f <<'EOF'\n" + CREATE + "\nEOF", WORK, "my/new", "allow"),
    ("heredoc then real create",
     "cat > f <<'EOF'\nsome docs\nEOF\n" + CREATE,                 WORK, "my/new", "DENY"),
    ("python heredoc quoting it",
     "python3 - <<'PY'\nx = \"" + CREATE + "\"\nPY",               WORK, "my/new", "allow"),
]

fails = 0
for name, cmd, prs, br, want in CASES:
    got, why = run(cmd, prs, br)
    ok = got == want
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL':4}  {got:5}  {name}")
    if not ok:
        print(f"        wanted {want}; reason: {why[:100]}")

got, _ = run(CREATE, WORK, "my/new", tool="Read")
print(f"{'PASS' if got == 'allow' else 'FAIL':4}  {got:5}  non-Bash tool")
fails += got != "allow"

for label, payload in [("malformed stdin", "not json"), ("empty stdin", "")]:
    m = load()
    sys.stdin = io.StringIO(payload)
    buf, real = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        m.main()
    except SystemExit:
        pass
    sys.stdout = real
    got = "DENY" if buf.getvalue().strip() else "allow"
    print(f"{'PASS' if got == 'allow' else 'FAIL':4}  {got:5}  {label}")
    fails += got != "allow"

print("\nALL PASS" if not fails else f"\n{fails} FAILURE(S)")
sys.exit(1 if fails else 0)
