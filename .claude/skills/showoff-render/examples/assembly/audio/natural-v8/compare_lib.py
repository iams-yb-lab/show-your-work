r"""Headroom-safe, lossless comparison packaging.

Written after a real failure. `make_audition.py` and `diagnose_ladder.py` both
loudness-matched by computing `gain = target_LUFS - integrated_LUFS` and
applying it as static gain, with no check on what that did to the peaks. The
sources peaked around -4 to -10 dBFS, the gains were +6 to +8.6 dB, and every
delivered file came out between +0.6 and +3.0 dBFS — clipped — and was then AAC
encoded on top. The student heard it instantly: "the tone is completely fine,
but the acoustic effect is so much worse". That is the signature of clipping,
and it invalidated both comparisons.

`natural-voice/method/README.md` requires loudness matching before any
comparison, because louder sounds superficially better. It does not license
matching *upward into the ceiling*. So:

  * the match level is derived from the material, not chosen in advance. The
    common target is the loudest level at which EVERY set still has at least
    `HEADROOM_DB` of true-peak room. Sets stay matched to each other; the whole
    comparison simply sits lower.
  * output is lossless WAV. A lossy encode is one more variable, and the files
    these get compared against are untouched WAVs.
  * static gain only. No limiter, no normalisation per file — a limiter would
    fix the number by changing the sound, which is the thing being judged.
"""
import json
import subprocess
import sys
from pathlib import Path

FF_BIN = (
    r"C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
)
FF = str(Path(FF_BIN) / "ffmpeg.exe")

HEADROOM_DB = 1.0  # minimum true-peak room below 0 dBFS in every delivered file
GAP_S = 1.5


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


def true_peak_dbfs(path):
    err = run([FF, "-hide_banner", "-i", str(path),
               "-af", "ebur128=peak=true", "-f", "null", "-"])
    peaks = [float(t.split()[0]) for t in err.split("Peak:")[1:] if "dBFS" in t.split("\n")[0]
             for t in [t.strip().split(" dBFS")[0]]]
    if not peaks:
        # fall back to sample peak
        err = run([FF, "-hide_banner", "-i", str(path), "-af", "astats", "-f", "null", "-"])
        peaks = [float(l.split(":")[1]) for l in err.splitlines() if "Peak level dB" in l]
    return max(peaks)


def measure_sets(sets):
    """sets: {name: [paths]} -> {name: {lufs, peak}} using the set's own files."""
    out = {}
    for name, paths in sets.items():
        for p in paths:
            if not Path(p).exists():
                raise FileNotFoundError(p)
        lufs = sum(integrated_lufs(p) for p in paths) / len(paths)
        peak = max(true_peak_dbfs(p) for p in paths)
        out[name] = dict(lufs=lufs, peak=peak)
    return out


def solve_target(meas):
    """Loudest common target leaving HEADROOM_DB of true-peak room everywhere.

    For a set at L LUFS peaking at P dBFS, a target T applies gain (T - L) and
    lands the peak at P + T - L. Requiring that to stay at or below
    -HEADROOM_DB gives T <= -HEADROOM_DB - P + L. The binding set wins.
    """
    return min(-HEADROOM_DB - m["peak"] + m["lufs"] for m in meas.values())


def build(sets, out_dir, prefix, gap_s=GAP_S, sample_rate=48000):
    """Concatenate each set's files at a common, headroom-safe level."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    meas = measure_sets(sets)
    target = solve_target(meas)
    report = dict(target_lufs=round(target, 2), headroom_db=HEADROOM_DB, sets={})

    for name, paths in sets.items():
        m = meas[name]
        gain = target - m["lufs"]
        ins, chains, order = [], [], []
        for i, p in enumerate(paths):
            ins += ["-i", str(p)]
            chains.append(
                f"[{i}:a]volume={gain:.2f}dB,aresample={sample_rate},"
                f"aformat=sample_fmts=flt:channel_layouts=mono[c{i}]")
            order.append(f"[c{i}]")
            if i < len(paths) - 1:
                chains.append(
                    f"aevalsrc=0:d={gap_s}:s={sample_rate},"
                    f"aformat=sample_fmts=flt:channel_layouts=mono[g{i}]")
                order.append(f"[g{i}]")
        fc = ";".join(chains) + f";{''.join(order)}concat=n={len(order)}:v=0:a=1[out]"
        dst = out_dir / f"{prefix}{name}.wav"
        run([FF, "-y", "-hide_banner", *ins, "-filter_complex", fc, "-map", "[out]",
             "-c:a", "pcm_s24le", "-ar", str(sample_rate), str(dst)])

        got = true_peak_dbfs(dst)
        status = "ok" if got <= -0.5 else "STILL HOT"
        print(f"  {name:<18} {m['lufs']:7.2f} LUFS  peak {m['peak']:6.2f} -> "
              f"gain {gain:+6.2f} dB -> true peak {got:6.2f} dBFS  [{status}]", flush=True)
        report["sets"][name] = dict(
            source_lufs=round(m["lufs"], 2), source_peak_dbfs=round(m["peak"], 2),
            gain_db=round(gain, 2), out_true_peak_dbfs=round(got, 2), file=str(dst))

    print(f"\ncommon target {target:.2f} LUFS, every file <= {-HEADROOM_DB:.1f} dBTP", flush=True)
    return report
