"""Where the intro film's audio tools find the repo, the shared audio engine, and ffmpeg.

The engine is `video/engine/` -- `dsp.py`, `mix_audio.py`, `voice_chain.py`, `narrate.py` and
`check_score.py`, written for the assembly film and shared with this one. The BS.1770-4
loudness meter, the true-peak limiter, the van Herk sliding maximum and the pitch set all live
there and are not copied here: a second copy of a loudness meter is a second answer to the same
question. This module only puts that directory on the path and hands back the two executables.
"""

from __future__ import annotations

import sys
from pathlib import Path

# .../video/education/intro/audio/intro_env.py -> audio, intro, education, video, repo
REPO = Path(__file__).resolve().parents[4]
FILM = REPO / "video" / "education" / "intro"
ENGINE = REPO / "video" / "engine"

if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

# The film and the two documents it was cut against.
VIDEO = FILM / "picture" / "Temperature Controller Intro 1080p.mp4"
HTML = FILM / "picture" / "Temperature Controller Intro.html"
SCRIPT = FILM / "script" / "voiceover-script.md"
OUT = REPO / "video" / "out" / "education"


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
