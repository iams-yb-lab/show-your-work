#!/usr/bin/env python3
"""Check that this repository still holds together.

    python tools/check_links.py          # human output, exit 1 on failure
    python tools/check_links.py --hook   # hook mode: read JSON on stdin, exit 2 on failure
    python tools/check_links.py --bless  # rewrite tools/skill-hashes.txt (see below)

Three checks, in order of how badly they hurt when they fail:

  geometry   the skills reach their method by relative path. `natural-voice/SKILL.md` is a short
             document whose entire content is "the method is over there"; if `over there` does not
             resolve, the skill still loads and still sounds authoritative while being empty.

  skills     the three skills are read-only and were copied byte-identical. A hash mismatch means
             something edited one, which is the failure this repository most wants to notice.

  travel     `video/` and `.claude/skills/` are what `install_skills.py` copies into another
             project. A link from inside them to a file in the repository root resolves fine here
             and breaks the moment it is installed anywhere else — a bug that is invisible until
             someone else has it.

  links      every relative link in every markdown file points at something that exists.

Links that deliberately point outside this repository live in EXTERNAL below, each with a reason.
Adding one is a decision to be made on purpose, which is why it costs a line of code.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
HASHES = Path(__file__).resolve().parent / "skill-hashes.txt"

SKIP_DIRS = {".git", "__pycache__", "out", ".venv", "venv", "node_modules"}

# Links that point at files which were deliberately left in the source repository.
# key: repo-relative posix path of the linking file -> reason it is allowed to dangle.
EXTERNAL: dict[str, str] = {}

# This repository must not need any other one. Nothing may name an absolute path into a different
# checkout as a *live* path — no default, no fallback, no import. The files below name one inside a
# record of what happened on a particular machine on a particular day; nothing reads them, and
# rewriting a record to look tidy in a new repository falsifies it. Everything else must be clean.
RECORDS = {
    "video/education/intro/audio/warm-natural-v2/education-v2-generation-settings.json":
        "provenance: which prompt and which take produced each line. The prompt WAV it names now "
        "lives at video/natural-voice/profiles/warm-natural/warm_narrator_prompt.wav",
    "video/natural-voice/profiles/deep-onyx-slow/prompt-selection.json":
        "the prompt audition record required by the profile contract: every candidate, its "
        "measurements and where it was written at the time",
    "video/education/how-to-make-an-explainer/DESIGN-PROMPT.md":
        "the handoff prompt as it was actually pasted into Claude Design, kept verbatim",
    "video/education/intro/audio/warm-natural-v2/final-report.json":
        "generated run report: what the v2 pipeline produced and where it wrote it",
    "video/education/intro/audio/warm-natural-v2/pipeline-status.json":
        "generated run report, as above",
    "video/education/intro/audio/warm-natural-v2/pipeline.log":
        "the raw console log of the v2 run, kept unedited",
}

FOREIGN = re.compile(r"[a-zA-Z]:[\\/]{1,2}temperature-controller", re.I)

# The load-bearing relative paths: (file containing the link, link as written in it).
GEOMETRY = [
    (".claude/skills/natural-voice/SKILL.md", "../../../video/natural-voice/README.md"),
    (".claude/skills/natural-voice/SKILL.md", "../../../video/natural-voice/EXPERIMENTS.md"),
    (".claude/skills/natural-voice/SKILL.md", "../../../video/natural-voice/profiles/warm-natural/"),
    (".claude/skills/education-video/SKILL.md", "interview.md"),
    (".claude/skills/education-video/SKILL.md", "images.md"),
    ("video/natural-voice/README.md", "../engine/voice_chain.py"),
    ("video/natural-voice/README.md", "../showoff/assembly/audio/VOICE-LOG.md"),
    ("video/natural-voice/README.md", "profiles/warm-natural/"),
]

# Cited by showoff-render as its evidence base, in prose rather than as a markdown link.
CITED = [
    ("showoff-render", "video/showoff/assembly/RENDER-LOG.md"),
]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def markdown_files():
    for p in sorted(ROOT.rglob("*.md")):
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        yield p


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def is_local(target: str) -> bool:
    """A link we can resolve on disk, as opposed to a URL, an anchor or a Windows path."""
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return False
    if re.match(r"^[A-Za-z]:[\\/]", target) or target.startswith("\\\\"):
        return False  # absolute path in a record; not this repository's to resolve
    return True


def check_geometry(fail):
    for where, link in GEOMETRY:
        src = ROOT / where
        if not src.exists():
            fail("geometry", where, "the file that carries the link is missing")
            continue
        if link not in src.read_text(encoding="utf-8"):
            fail("geometry", where, f"no longer contains the link {link!r}")
            continue
        if not (src.parent / link).resolve().exists():
            fail("geometry", where, f"{link} does not resolve — the skill cannot reach its method")
    for skill, path in CITED:
        if not (ROOT / path).exists():
            fail("geometry", f".claude/skills/{skill}/SKILL.md",
                 f"cites {path}, which is not here — the rule has lost its evidence")


def check_skills(fail, bless=False):
    live = {rel(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(SKILLS.rglob("*.md"))}
    if bless:
        HASHES.write_text(
            "# sha256 of every skill file, byte-identical to the source repository.\n"
            "# The skills are read-only; a mismatch here means one was edited.\n"
            "# Regenerate ONLY after an edit the user authorised with the exact phrase.\n"
            + "".join(f"{h}  {n}\n" for n, h in live.items()), encoding="utf-8")
        print(f"blessed {len(live)} skill files -> {rel(HASHES)}")
        return
    if not HASHES.exists():
        fail("skills", rel(HASHES), "missing — run --bless to record the skill hashes")
        return
    want = {}
    for line in HASHES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            h, _, n = line.partition("  ")
            want[n] = h
    for name, h in want.items():
        if name not in live:
            fail("skills", name, "recorded in skill-hashes.txt but not present")
        elif live[name] != h:
            fail("skills", name, "CHANGED — the skills are read-only (see CLAUDE.md)")
    for name in live:
        if name not in want:
            fail("skills", name, "present but not recorded — run --bless if it was added on purpose")


def check_independence(fail):
    """No live path may name another checkout. This repository stands on its own."""
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        r = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in r.parts):
            continue
        if p.suffix.lower() in {".wav", ".png", ".mp4", ".pyc", ".zip", ".srt"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        name = r.as_posix()
        if name in RECORDS or name == "tools/check_links.py":
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if FOREIGN.search(line):
                fail("independence", f"{name}:{n}",
                     "names an absolute path into another checkout — make it relative, take it "
                     "from the environment, or declare the file a record in RECORDS")


def check_travel(fail):
    """Nothing inside the installable payload may link outside it."""
    travels = (".claude/skills/", "video/")
    for p in markdown_files():
        name = rel(p)
        if not name.startswith(travels) or name in EXTERNAL:
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for target in LINK_RE.findall(line):
                target = target.split(" ")[0].split("#")[0].strip()
                if not target or not is_local(target):
                    continue
                dest = (p.parent / target).resolve()
                try:
                    d = dest.relative_to(ROOT).as_posix()
                except ValueError:
                    fail("travel", f"{name}:{n}", f"{target} escapes the repository")
                    continue
                if not d.startswith((".claude/skills", "video")):
                    fail("travel", f"{name}:{n}",
                         f"{target} points at {d}, which install_skills.py does not copy")


def check_links(fail):
    for p in markdown_files():
        name = rel(p)
        allowed = name in EXTERNAL
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for target in LINK_RE.findall(line):
                target = target.split(" ")[0].split("#")[0].strip()
                if not target or not is_local(target):
                    continue
                if (p.parent / target).resolve().exists():
                    continue
                if allowed:
                    continue  # documented in EXTERNAL
                fail("links", f"{name}:{n}", f"{target} does not exist")


def main(argv):
    hook_mode = "--hook" in argv
    if hook_mode:
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            return 0
        path = (payload.get("tool_input") or {}).get("file_path", "")
        if not path.endswith(".md"):
            return 0
        try:
            Path(path).resolve().relative_to(ROOT)
        except ValueError:
            return 0

    failures = []
    def fail(check, where, message):
        failures.append((check, where, message))

    if "--bless" in argv:
        check_skills(fail, bless=True)
        return 0

    check_geometry(fail)
    check_skills(fail)
    check_independence(fail)
    check_travel(fail)
    check_links(fail)

    out = sys.stderr if hook_mode else sys.stdout
    if not failures:
        if not hook_mode:
            n = len(list(markdown_files()))
            print(f"ok — geometry intact, skills unmodified, no path into another checkout, "
                  f"payload self-contained, links resolve ({n} markdown files)")
        return 0

    for check in ("geometry", "skills", "independence", "travel", "links"):
        items = [(w, m) for c, w, m in failures if c == check]
        if not items:
            continue
        print(f"[{check}]", file=out)
        for where, message in items[:12]:
            print(f"  {where}: {message}", file=out)
        if len(items) > 12:
            print(f"  … and {len(items) - 12} more", file=out)
        print(file=out)
    return 2 if hook_mode else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
