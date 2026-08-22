"""Where the intro film's audio tools find the repo, the shared audio engine, and ffmpeg.

The engine is `_shared/audio/` -- `dsp.py`, `mix_audio.py`, `voice_chain.py`, `narrate.py` and
`check_score.py`, written for the assembly film and shared with this one. The BS.1770-4
loudness meter, the true-peak limiter, the van Herk sliding maximum and the pitch set all live
there and are not copied here: a second copy of a loudness meter is a second answer to the same
question. This module only puts that directory on the path and hands back the two executables.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Do not anchor on a depth. Walk up to the directory holding the skills and take everything
# from there: this file moved once already (video/education/intro/audio/ -> here) and a
# parents[4] would have survived the move still pointing somewhere, just not at the repo.
SKILLS = next(p for p in Path(__file__).resolve().parents
              if (p / "_shared").is_dir() and (p / "natural-voice").is_dir())
REPO = SKILLS.parents[1]                    # .claude/skills -> .claude -> the repository
FILM = SKILLS / "education-video" / "examples" / "intro"
ENGINE = SKILLS / "_shared" / "audio"

if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

# The two documents the film was cut against, and the picture.
#
# The silent 1080p master was deleted on 2026-08-22: it is derived from the HTML bundle beside
# it and re-made by education-video/method/export_html_video.py, which needs Playwright, Chrome
# and ffmpeg. Render it to OUT and pass --video if a tool needs the picture. Untested since the
# deletion: ffmpeg was not installed on the machine that made this change.
VIDEO = OUT / "picture" / "Temperature Controller Intro 1080p.mp4"
HTML = FILM / "picture" / "Temperature Controller Intro.html"
SCRIPT = FILM / "script" / "voiceover-script.md"
OUT = REPO / "out" / "education"


def find_ffmpeg() -> str:
    """ffmpeg is installed on the Windows box but outside the shell's PATH, so `which` finds
    nothing and it looks absent. `narrate.py` already holds the known location; use it rather
    than keeping a second copy of the path."""
    from narrate import find_ffmpeg as _find                       # noqa: PLC0415
    return _find()


def find_ffprobe() -> str:
    exe = find_ffmpeg()
    if not exe:
        return ""
    probe = Path(exe).with_name("ffprobe" + Path(exe).suffix)
    return str(probe) if probe.exists() else ""
