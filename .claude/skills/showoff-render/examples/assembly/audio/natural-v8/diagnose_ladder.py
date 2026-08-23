r"""Which step kills the naturalness? Four rungs, one variable each.

The student auditioned `prompt_B_slower_0.78.wav` against
`audition_B_slow078.m4a` and reported the prompt sounding markedly more
natural. That comparison has four variables in it at once: engine (Kokoro
direct vs an EditX clone of it), text, MossFormer2 restoration, and EQ. It
cannot say which one did the damage.

EXPERIMENTS.md's protocol is one variable at a time. Same voice, same two
lines, same loudness, four rungs:

  1_kokoro_direct   Kokoro am_onyx @0.78 speaking the lines. Raw 24 kHz.
  2_editx_raw       EditX cloning that prompt. Raw 24 kHz, untrimmed.
  3_editx_sr        rung 2 + MossFormer2_SR_48K.
  4_editx_sr_eq     rung 3 + the reconstructed v7.2 EQ.  (= what was auditioned)

Read it as a ladder. If 1 >> 2, the clone step is the problem and the engine
should change. If 1 ~ 2 but 3 or 4 is worse, the processing is the problem and
the engine stays. Rungs 2-4 already exist from the audition run; only rung 1 is
generated here.

This is a diagnosis, not a slate of candidates to choose a film from.

Run in `%TEMP%\sr-venv` (kokoro + torch + ffmpeg).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

FF_BIN = (
    r"C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
)
os.environ["PATH"] += os.pathsep + FF_BIN
FF = str(Path(FF_BIN) / "ffmpeg.exe")

import numpy as np
import torch
import soundfile as sf

# Anchored by walking up to the directory that holds the video tree, so this
# file works in any checkout it is lifted into. See _shared/README.md.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / ".claude" / "skills" / "natural-voice").is_dir())
ROOT = REPO / "out" / "showoff" / "natural-v8"
B = ROOT / "audition" / "B_slow078"
OUT = ROOT / "ladder"
OUT.mkdir(parents=True, exist_ok=True)

LINES = {
    1: "It all begins with a bare board... and an idea precise enough to become real.",
    6: "Until the instrument stands complete... ready to master the invisible frontier "
       "between heat... and control.",
}
SPEED = 0.78
VOICE = "am_onyx"
SEED = 20260813
GAP_S = 1.5
MATCH_LUFS = -18.0


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-3000:])
        sys.exit(1)
    return p.stderr


def integrated_lufs(path):
    err = run([FF, "-hide_banner", "-i", str(path),
               "-af", "loudnorm=I=-16:TP=-1.5:print_format=json", "-f", "null", "-"])
    return float(json.loads(err[err.rindex("{"): err.rindex("}") + 1])["input_i"])


def main():
    # rung 1: the prompt's own engine, speaking the film's words
    from kokoro import KPipeline

    pipe = KPipeline(lang_code="a", device="cuda" if torch.cuda.is_available() else "cpu")
    for lid, text in LINES.items():
        torch.manual_seed(SEED + lid)
        chunks = [a for _, _, a in pipe(text, voice=VOICE, speed=SPEED)]
        y = torch.cat(chunks).numpy().astype(np.float32)
        sf.write(str(OUT / f"1_kokoro_direct_line{lid}.wav"), y, 24000)
        print(f"kokoro line{lid}: {len(y) / 24000:.2f}s", flush=True)

    rungs = {
        "1_kokoro_direct": lambda lid: OUT / f"1_kokoro_direct_line{lid}.wav",
        "2_editx_raw": lambda lid: B / f"line{lid}_audition.wav",
        "3_editx_sr": lambda lid: B / f"line{lid}_sr.wav",
        "4_editx_sr_eq": lambda lid: B / f"line{lid}_eq.wav",
    }

    report = {}
    for name, src in rungs.items():
        paths = [src(lid) for lid in LINES]
        for p in paths:
            if not p.exists():
                print(f"missing {p} — run make_audition.py first")
                return 1
        # one gain for the rung, from both its lines, so rungs compare fairly
        gain = MATCH_LUFS - float(np.mean([integrated_lufs(p) for p in paths]))
        report[name] = round(gain, 2)

        ins, chains, order = [], [], []
        for i, p in enumerate(paths):
            ins += ["-i", str(p)]
            chains.append(
                f"[{i}:a]volume={gain:.2f}dB,aresample=48000,aformat=channel_layouts=mono[c{i}]")
            order.append(f"[c{i}]")
            if i < len(paths) - 1:
                chains.append(f"aevalsrc=0:d={GAP_S}:s=48000,aformat=channel_layouts=mono[g{i}]")
                order.append(f"[g{i}]")
        fc = ";".join(chains) + f";{''.join(order)}concat=n={len(order)}:v=0:a=1[out]"
        dst = ROOT / f"ladder_{name}.m4a"
        run([FF, "-y", "-hide_banner", *ins, "-filter_complex", fc, "-map", "[out]",
             "-c:a", "aac", "-b:a", "256k", str(dst)])
        print(f"wrote {dst}  (gain {gain:+.2f} dB)", flush=True)

    (OUT / "ladder-report.json").write_text(
        json.dumps(dict(match_lufs=MATCH_LUFS, gains_db=report,
                        kokoro=dict(voice=VOICE, speed=SPEED, seed=SEED)), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
