#!/usr/bin/env python3
"""Carry what went wrong in a skill run back to the skills, without bothering anyone.

    friction.py brief            PostToolUse(Skill) hook — inject the reviewed lessons for that skill
    friction.py note   ...       record one friction entry (Claude calls this, silently, at the end)
    friction.py check            Stop hook — a skill fired and nothing was recorded: remind Claude
    friction.py flush            Stop hook — buffer -> commit -> push -> open/update this machine's PR
    friction.py compact          fold reviewed inbox entries into feedback/lessons/ (run at merge)

The skills in this repository are read-only, which protects every future session from an unreviewed
tweak and throws away the one thing a run actually teaches: the moment the user had to correct
Claude. This is the other half of that rule. Friction is recorded as evidence, travels home as a
pull request, and once *reviewed* is read back at the start of the next run of that skill.

Three tiers, and the separation is the whole safety argument:

  raw         ~/.claude/skill-friction/pending.jsonl   machine-local, written in any project
  in flight   feedback/inbox/<host>.md on friction/<host>, one commit per session, one standing PR
  reviewed    feedback/lessons/<skill>.md on main       the ONLY tier that is ever read back

Nothing unreviewed can change how a skill behaves. Same guarantee as the read-only rule, applied
to the feedback loop.

Two hard contracts:

  Never bother the user.   No prompt, no question, no mid-run interruption. `check` blocks the Stop
                           hook, but a Stop block is addressed to Claude, not to the human; the
                           human sees a status line and the PR, nothing else.

  Never break a turn.      Every hook path exits 0. No network, no gh, no push rights, no git at
                           all: keep the buffer, say nothing, try again next session. Same contract
                           as .claude/hooks/git-autosync.sh.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

# Do not anchor on the checkout — video/README.md. Walk up to the tree that holds the method.
REPO = next((p for p in Path(__file__).resolve().parents
             if (p / "video" / "natural-voice").is_dir()), None)

# Machine-local, and overridable so the whole push path can be exercised against a scratch
# clone without touching the real buffer or opening a real pull request.
STATE = Path(os.environ.get("FRICTION_STATE")
             or Path.home() / ".claude" / "skill-friction").expanduser()
PENDING = STATE / "pending.jsonl"
FLUSHED = STATE / "flushed.jsonl"
SESSIONS = STATE / "sessions"
LATEST = STATE / "latest.txt"
HOME_TXT = STATE / "home.txt"

FIELDS = ("complaint", "mistake", "fix", "rule")
FIELD_CAP = 220           # a field longer than this is a transcript, not a lesson
LESSON_CAP_BYTES = 2048   # per-skill read-back budget; compact enforces it

# No film content, no client names, no machine paths. The lab repo is not a leak.
LEAKS = re.compile(r"(?:^|[\s(\"'])(?:/Users/|/home/|/private/|[A-Za-z]:[\\/])", re.I)

ENTRY_RE = re.compile(
    r"^### (?P<date>\d{4}-\d{2}-\d{2}) · (?P<skill>[\w.-]+)(?: · (?P<gate>[^\n]+))?\n"
    r"(?P<body>(?:- \*\*\w+:\*\* [^\n]*\n)+)", re.M)


# ---------------------------------------------------------------- small helpers

def out_json(payload: dict) -> None:
    print(json.dumps(payload))


def read_hook() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, OSError):
        return {}


def host() -> str:
    h = re.sub(r"[^a-z0-9-]+", "-", socket.gethostname().split(".")[0].lower()).strip("-")
    return h or "unknown-host"


def git(repo: Path, *args, env=None, stdin=None):
    """Run git, return (ok, stdout). Never raises — a helper must not be why a turn fails."""
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           timeout=45, input=stdin,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                                "GCM_INTERACTIVE": "never", **(env or {})})
        return r.returncode == 0, (r.stdout or "").strip() or (r.stderr or "").strip()
    except (OSError, subprocess.SubprocessError):
        return False, ""


def home_checkout() -> Path | None:
    """The clone of this repository on this machine, if one is known and still looks right."""
    for cand in (Path(HOME_TXT.read_text(encoding="utf-8").strip())
                 if HOME_TXT.is_file() else None, REPO):
        if cand and (cand / "feedback" / "lessons").is_dir() and (cand / ".claude" / "skills").is_dir():
            return cand
    return None


def lessons_dir() -> Path | None:
    """Reviewed lessons: the home checkout first, because those are current; then the payload copy."""
    for base in (home_checkout(), REPO):
        if base and (base / "feedback" / "lessons").is_dir():
            return base / "feedback" / "lessons"
    return None


def our_skills() -> set[str]:
    """The skills this repository owns — read off disk so nobody has to maintain a list."""
    for base in (REPO, home_checkout()):
        if base and (base / ".claude" / "skills").is_dir():
            return {p.name for p in (base / ".claude" / "skills").iterdir() if p.is_dir()}
    return set()


def how_to_call(cwd: str | None) -> str:
    """Spell the command relatively when we can. An absolute path would be machine-specific, so no
    committed permission rule could match it and the user would get a prompt — the one thing this
    whole mechanism is not allowed to do."""
    for base in (Path(cwd) if cwd else None, REPO):
        if base and (base / "tools" / "friction.py").is_file():
            return "python3 tools/friction.py"
    return f"python3 {Path(__file__).resolve()}"


def session_file(sid: str) -> Path:
    safe = re.sub(r"[^\w-]+", "-", sid or "unknown")[:80]
    return SESSIONS / f"{safe}.json"


def load_session(sid: str) -> dict:
    p = session_file(sid)
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"skills": [], "resolved": False, "blocked_once": False}


def save_session(sid: str, data: dict) -> None:
    SESSIONS.mkdir(parents=True, exist_ok=True)
    session_file(sid).write_text(json.dumps(data), encoding="utf-8")


# ------------------------------------------------------------------------ brief

BRIEF_TAIL = """\
When this session ends, if anything here went wrong — a correction, rework, a wrong assumption, a \
gate re-run — record it in one line each:
  {script} note --session {sid} --skill {skill} [--gate G] \
--complaint "what they said" --mistake "what I did" --fix "what worked" --rule "the line that \
would have prevented it" [--cost "2 turns"]
Clean run: {script} note --session {sid} --skill {skill} --none
Do this silently. Do not ask, do not mention it, do not discuss it — it is bookkeeping, not a \
conversation. No film content, no absolute paths."""


def cmd_brief(_a) -> int:
    hook = read_hook()
    if hook.get("tool_name") not in (None, "", "Skill"):
        return 0
    skill = ((hook.get("tool_input") or {}).get("skill") or "").split(":")[-1].strip()
    if not skill or skill not in our_skills():
        return 0

    sid = hook.get("session_id") or "unknown"
    data = load_session(sid)
    if skill not in data["skills"]:
        data["skills"].append(skill)
    save_session(sid, data)
    STATE.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(sid, encoding="utf-8")

    parts = []
    d = lessons_dir()
    f = d / f"{skill}.md" if d else None
    if f and f.is_file():
        body = f.read_text(encoding="utf-8")
        if re.search(r"^- \*\*", body, re.M):   # header only == nothing reviewed yet
            parts.append(f"Lessons already paid for in earlier runs of {skill} — do not repeat "
                         f"these:\n\n{body.strip()}")
    parts.append(BRIEF_TAIL.format(script=how_to_call(hook.get("cwd")), sid=sid, skill=skill))

    out_json({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                     "additionalContext": "\n\n".join(parts)}})
    return 0


# ------------------------------------------------------------------------- note

def cmd_note(a) -> int:
    sid = a.session or (LATEST.read_text(encoding="utf-8").strip() if LATEST.is_file() else "unknown")
    data = load_session(sid)

    if a.none:
        data["resolved"] = True
        save_session(sid, data)
        print("clean run recorded; nothing to send")
        return 0

    missing = [f for f in FIELDS if not getattr(a, f)]
    if missing:
        print(f"need {', '.join('--' + m for m in missing)} — or --none for a clean run",
              file=sys.stderr)
        return 2

    entry = {"date": date.today().isoformat(), "host": host(), "skill": a.skill,
             "gate": (a.gate or "").strip()}
    for f in FIELDS:
        v = " ".join(getattr(a, f).split())
        if LEAKS.search(v):
            print(f"--{f} contains an absolute path. Entries carry rules, never machine paths "
                  f"or film content.", file=sys.stderr)
            return 2
        if len(v) > FIELD_CAP:
            print(f"--{f} is {len(v)} chars, cap is {FIELD_CAP}. One line, not a transcript.",
                  file=sys.stderr)
            return 2
        entry[f] = v
    if a.cost:
        entry["cost"] = " ".join(a.cost.split())[:60]

    STATE.mkdir(parents=True, exist_ok=True)
    with PENDING.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    data["resolved"] = True
    save_session(sid, data)
    print(f"recorded: {a.skill} — {entry['rule'][:60]}")
    return 0


# ------------------------------------------------------------------------ check

BLOCK = """\
A skill from show-your-work ran this session ({skills}) and no friction entry was recorded. Before \
finishing: if the user corrected you, if anything was reworked, if a gate had to be re-run, or if \
you assumed something wrong — record it now, in one silent command, and say nothing about it to the \
user:
  {script} note --session {sid} --skill <skill> --complaint "..." --mistake "..." \
--fix "..." --rule "..."
If the run genuinely had no friction:
  {script} note --session {sid} --skill {first} --none
Then finish your reply as normal. Do not mention this step."""


def cmd_check(_a) -> int:
    hook = read_hook()
    sid = hook.get("session_id") or "unknown"
    data = load_session(sid)
    if not data["skills"] or data["resolved"]:
        return 0
    if hook.get("stop_hook_active") or data.get("blocked_once"):
        return 0   # asked once. Never loop, never nag.
    data["blocked_once"] = True
    save_session(sid, data)
    out_json({"decision": "block",
              "reason": BLOCK.format(skills=", ".join(data["skills"]), sid=sid,
                                     first=data["skills"][0],
                                     script=how_to_call(hook.get("cwd")))})
    return 0


# ------------------------------------------------------------------------ flush

def render(entries: list[dict]) -> str:
    chunks = []
    for e in entries:
        head = f"### {e['date']} · {e['skill']}"
        if e.get("gate"):
            head += f" · {e['gate']}"
        lines = [head]
        for f in FIELDS:
            lines.append(f"- **{f}:** {e.get(f, '')}")
        if e.get("cost"):
            lines.append(f"- **cost:** {e['cost']}")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def cmd_flush(a) -> int:
    if not PENDING.is_file() or not PENDING.read_text(encoding="utf-8").strip():
        return 0
    entries = []
    for line in PENDING.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not entries:
        return 0

    repo = home_checkout()
    if not repo:
        return 0                          # no clone here to push from; buffer waits
    ok, _ = git(repo, "rev-parse", "--git-dir")
    if not ok:
        return 0
    ok, origin = git(repo, "remote", "get-url", "origin")
    if not ok or not origin:
        return 0

    h = host()
    branch = f"friction/{h}"
    path = f"feedback/inbox/{h}.md"
    git(repo, "fetch", "--quiet", "origin", branch)

    base = ""
    for ref in (f"refs/remotes/origin/{branch}", f"refs/heads/{branch}", "refs/remotes/origin/main"):
        ok, sha = git(repo, "rev-parse", "--verify", "--quiet", ref)
        if ok and sha:
            base = sha
            break
    if not base:
        return 0

    ok, prior = git(repo, "show", f"{base}:{path}")
    if not ok:
        prior = (f"# Friction from `{h}`\n\n"
                 f"Raw entries, newest last, awaiting review. Format and redaction rule: "
                 f"`feedback/README.md`.\n")
    body = prior.rstrip() + "\n\n" + render(entries) + "\n"
    msg = (f"friction({h}): {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} — "
           + ", ".join(sorted({e['skill'] for e in entries})))

    if a.check:
        print(f"would append {len(entries)} entr(ies) to {path} on {branch} (base {base[:8]})\n"
              f"  message: {msg}\n  push to: {origin}")
        return 0

    # Build the commit with plumbing: no branch switch, no stash, the working tree is never touched.
    ok, blob = git(repo, "hash-object", "-w", "--stdin", stdin=body)
    if not ok or not blob:
        return 0
    with tempfile.TemporaryDirectory() as td:
        env = {"GIT_INDEX_FILE": str(Path(td) / "index")}
        if not git(repo, "read-tree", base, env=env)[0]:
            return 0
        if not git(repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)[0]:
            return 0
        ok, tree = git(repo, "write-tree", env=env)
    if not ok or not tree:
        return 0
    ok, commit = git(repo, "commit-tree", tree, "-p", base, "-m", msg)
    if not ok or not commit:
        return 0
    if not git(repo, "update-ref", f"refs/heads/{branch}", commit)[0]:
        return 0
    if not git(repo, "push", "--quiet", "origin", f"refs/heads/{branch}:refs/heads/{branch}")[0]:
        return 0                          # offline or no rights: buffer stays, retry next session

    # Pushed. The buffer has done its job; keep a local copy of what left.
    with FLUSHED.open("a", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    PENDING.write_text("", encoding="utf-8")
    open_pr(repo, branch, h)
    print(f"friction: pushed {len(entries)} entr(ies) to {branch}")
    return 0


def open_pr(repo: Path, branch: str, h: str) -> None:
    """One standing PR per machine. Opened once, updated by every later push."""
    try:
        r = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "open",
                            "--json", "number"], capture_output=True, text=True,
                           timeout=45, cwd=str(repo))
        if r.returncode == 0 and json.loads(r.stdout or "[]"):
            return                        # already open; the push updated it
        subprocess.run(["gh", "pr", "create", "--base", "main", "--head", branch,
                        "--title", f"friction from {h}",
                        "--body", "Friction recorded automatically while running the skills on "
                                  f"`{h}`. Raw entries only — review, then fold the ones worth "
                                  "keeping into `feedback/lessons/` with "
                                  "`python tools/friction.py compact`.\n\nOnly reviewed lessons on "
                                  "`main` are ever read back into a run."],
                       capture_output=True, text=True, timeout=60, cwd=str(repo))
    except (OSError, subprocess.SubprocessError, ValueError):
        return                            # no gh, no network: the branch is pushed, that is enough


# ---------------------------------------------------------------------- compact

def parse_inbox(repo: Path) -> list[dict]:
    found = []
    for p in sorted((repo / "feedback" / "inbox").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        for m in ENTRY_RE.finditer(text):
            e = {"date": m.group("date"), "skill": m.group("skill"),
                 "gate": (m.group("gate") or "").strip()}
            for line in m.group("body").splitlines():
                k = re.match(r"- \*\*(\w+):\*\* (.*)$", line)
                if k:
                    e[k.group(1)] = k.group(2).strip()
            found.append(e)
    return found


def cmd_compact(a) -> int:
    repo = home_checkout() or REPO
    if not repo:
        print("no checkout found", file=sys.stderr)
        return 2
    ldir = repo / "feedback" / "lessons"
    entries = parse_inbox(repo)
    if not entries:
        print("no inbox entries to fold in")
        return 0

    changed = []
    for skill in sorted({e["skill"] for e in entries}):
        f = ldir / f"{skill}.md"
        if not f.is_file():
            print(f"! no lessons file for {skill} — is it one of ours?", file=sys.stderr)
            continue
        text = f.read_text(encoding="utf-8")
        head, _, _ = text.partition("\n- **")
        lines = [l for l in text.splitlines() if l.startswith("- **")]
        index = {}
        for l in lines:
            key = re.sub(r"\W+", "", (re.match(r"- \*\*(.*?)\*\*", l) or re.match(r"(.*)", l))
                         .group(1).lower())[:60]
            index[key] = l

        for e in (x for x in entries if x["skill"] == skill):
            rule = e.get("rule", "").strip()
            if not rule:
                continue
            key = re.sub(r"\W+", "", rule.lower())[:60]
            prior = index.get(key)
            seen = 1
            if prior:
                m = re.search(r"seen (\d+)×", prior)
                seen = int(m.group(1)) + 1 if m else 2
            mistake = e.get("mistake", "").rstrip(".")
            gate = f" ({e['gate']})" if e.get("gate") else ""
            index[key] = (f"- **{rule}** — otherwise: {mistake}{gate}. "
                          f"*(seen {seen}×, last {e['date']})*")

        merged = sorted(index.values(),
                        key=lambda l: (-int((re.search(r'seen (\d+)×', l) or [0, 1])[1]), l))
        body = head.rstrip() + "\n\n" + "\n".join(merged) + "\n"
        if len(body.encode("utf-8")) > LESSON_CAP_BYTES:
            keep, size = [], len(head.encode("utf-8")) + 2
            for l in merged:
                size += len(l.encode("utf-8")) + 1
                if size > LESSON_CAP_BYTES:
                    break
                keep.append(l)
            print(f"! {skill}: over the {LESSON_CAP_BYTES}B read-back cap — kept the "
                  f"{len(keep)} most-seen of {len(merged)}", file=sys.stderr)
            body = head.rstrip() + "\n\n" + "\n".join(keep) + "\n"
        if body != text:
            changed.append(f.relative_to(repo).as_posix())
            if not a.check:
                f.write_text(body, encoding="utf-8")

    verb = "would update" if a.check else "updated"
    print(f"{verb}: {', '.join(changed) if changed else 'nothing'}")
    if changed and not a.check:
        print("The inbox entries stay as the record. Delete them in the same commit if they are "
              "fully folded in.")
    return 0


# ------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("brief", help="PostToolUse(Skill) hook: inject reviewed lessons").set_defaults(f=cmd_brief)

    n = sub.add_parser("note", help="record one friction entry")
    n.add_argument("--session"), n.add_argument("--skill", required=True), n.add_argument("--gate")
    for field in FIELDS:
        n.add_argument(f"--{field}")
    n.add_argument("--cost"), n.add_argument("--none", action="store_true",
                                             help="the run was clean; record that and send nothing")
    n.set_defaults(f=cmd_note)

    sub.add_parser("check", help="Stop hook: remind Claude if a skill ran unlogged").set_defaults(f=cmd_check)

    fl = sub.add_parser("flush", help="Stop hook: push the buffer as this machine's PR")
    fl.add_argument("--check", action="store_true", help="say what it would do; change nothing")
    fl.set_defaults(f=cmd_flush)

    c = sub.add_parser("compact", help="fold reviewed inbox entries into feedback/lessons/")
    c.add_argument("--check", action="store_true", help="say what it would do; change nothing")
    c.set_defaults(f=cmd_compact)

    a = ap.parse_args(argv)
    try:
        return a.f(a)
    except Exception as exc:                       # a hook must never be why a turn fails
        if a.cmd in ("brief", "check", "flush"):
            print(f"friction: {type(exc).__name__}", file=sys.stderr)
            return 0
        raise


if __name__ == "__main__":
    sys.exit(main())
