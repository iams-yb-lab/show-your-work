r"""v8 steps 7-10: restore, EQ, master, mux.

  7. gated MossFormer2_SR_48K restoration, clean-resample fallback per line
  8. minimal corrective EQ, then one continuous narration master
  9. the master is the timing authority; lines are placed by lexical onset
 10. music last, mux with the picture stream copied unchanged

Two departures from v7.2, both required by the method document:

  * lines are placed by subtracting each take's measured lead-in from its
    anchor, so the first word still lands on the frame it was written for while
    the file keeps its whole head and its 0.84-1.01 s tail. v7.2 trimmed the
    tails off and delayed by the anchor directly.
  * EQ is the high-pass alone. The warm narrator's five-band curve is
    explicitly profile-specific in the method document, and this is a different
    voice, so nothing else is applied without a measured reason.

No atempo: this read is already unhurried at the source. No ducking, matching
the approved v7.2 mix. No compression, room tone, echo or exciter.

Run in `%TEMP%\sr-venv`.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FF_BIN = (
    r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin"
)
os.environ["PATH"] += os.pathsep + FF_BIN
FF = str(Path(FF_BIN) / "ffmpeg.exe")

import numpy as np
import librosa
import soundfile as sf

# Anchored by walking up to the directory that holds the video tree, so this
# file works in any checkout it is lifted into. See video/README.md.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / ".claude" / "skills" / "natural-voice").is_dir())
ROOT = REPO / "out" / "showoff" / "natural-v8"
TAKES = ROOT / "kokoro_takes"
WORK = ROOT / "master"
WORK.mkdir(parents=True, exist_ok=True)

VIDEO = REPO / "out" / "showoff" / "anim" / "assembly_purple_v2.mp4"
SCORE = REPO / "out" / "showoff" / "voice-rnd" / "cinematic_score_v2.wav"
OUT_MP4 = REPO / "out" / "showoff" / "anim" / "assembly_purple_v2_epic_v8.mp4"

DURATION = 84.0
VOICE_LUFS = -13.5      # v7.2's approved no-duck per-line target
MASTER_I, MASTER_TP = -14.0, -1.0
EQ = "highpass=f=45"    # see the module docstring

GATE_WER, GATE_DUR_FRAC, GATE_DUR_ABS, GATE_F0 = 0.12, 0.012, 0.050, 5.0


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-3000:])
        sys.exit(1)
    return p.stderr


def loudnorm_json(path):
    err = run([FF, "-hide_banner", "-i", str(path),
               "-af", "loudnorm=I=-16:TP=-1.5:print_format=json", "-f", "null", "-"])
    return json.loads(err[err.rindex("{"): err.rindex("}") + 1])


def true_peak(path):
    err = run([FF, "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
    vals = re.findall(r"Peak:\s*(-?\d+\.?\d*)\s*dBFS", err)
    return max(float(v) for v in vals) if vals else float("nan")


def norm_words(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()


def wer(ref, hyp):
    import difflib
    sm = difflib.SequenceMatcher(a=ref, b=hyp)
    return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes()
               if op != "equal") / max(1, len(ref))


def median_f0(y, sr):
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if f0.size else float("nan")


def hf_ratio(y, sr, cutoff=12000.0):
    S = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / sr)
    tot = S.sum()
    return float(S[f >= cutoff].sum() / tot) if tot > 0 else 0.0


def main():
    man = json.loads((TAKES / "manifest.json").read_text())

    # --- step 5, finished: one take per line, chosen for cross-line register
    #     consistency. The takes within a line are near-identical (same engine,
    #     same settings, deterministic bar sampling noise), so this is not a
    #     per-line quality choice -- which is the thing v7 had to undo.
    usable = [t for l in man["lines"] for t in l["takes"] if "median_f0_hz" in t and not t["over_cap"]]
    target_f0 = float(np.median([t["median_f0_hz"] for t in usable]))
    chosen = {}
    for line in man["lines"]:
        cands = [t for t in line["takes"] if "median_f0_hz" in t and not t["over_cap"]] \
            or [t for t in line["takes"] if "median_f0_hz" in t]
        chosen[line["line"]] = min(cands, key=lambda t: abs(t["median_f0_hz"] - target_f0))
    print(f"register target {target_f0:.1f} Hz; chosen "
          f"{[(l, chosen[l]['take'], chosen[l]['median_f0_hz']) for l in sorted(chosen)]}\n", flush=True)

    # --- step 7: gated restoration
    from clearvoice import ClearVoice
    cv = ClearVoice(task="speech_super_resolution", model_names=["MossFormer2_SR_48K"])
    import whisper
    asr = whisper.load_model("base.en", device="cuda")

    placed, sr_report = [], []
    for line in man["lines"]:
        lid = line["line"]
        t = chosen[lid]
        src = Path(t["path"])
        y0, s0 = librosa.load(str(src), sr=None)
        dur0, f00, hf0 = len(y0) / s0, median_f0(y0, s0), hf_ratio(y0, s0)

        dst = WORK / f"line{lid}_speech.wav"
        y = np.asarray(cv(input_path=str(src), online_write=False), dtype=np.float32).squeeze()
        sf.write(str(dst), y, 48000)
        dur1, f01, hf1 = len(y) / 48000, median_f0(y, 48000), hf_ratio(y, 48000)
        hyp = asr.transcribe(str(dst), language="en")["text"].strip()
        w = wer(norm_words(line["text"]), norm_words(hyp))

        ok = (w <= GATE_WER and abs(dur1 - dur0) <= GATE_DUR_FRAC * dur0 + GATE_DUR_ABS
              and abs(f01 - f00) <= GATE_F0 and hf1 > hf0)
        if not ok:
            run([FF, "-y", "-hide_banner", "-i", str(src), "-ar", "48000",
                 "-c:a", "pcm_f32le", str(dst)])
        print(f"line{lid}: {dur0:.2f}->{dur1:.2f}s  F0 {f00:.0f}->{f01:.0f} Hz  wer={w:.3f}  "
              f"HF>12k {hf0:.3%}->{hf1:.3%}  {'restored' if ok else 'FALLBACK to resample'}",
              flush=True)
        sr_report.append(dict(line=lid, restored=bool(ok), wer=round(w, 4),
                              f0_before=round(f00, 1), f0_after=round(f01, 1),
                              hf_before=round(hf0, 6), hf_after=round(hf1, 6)))

        # placement: anchor is where the FIRST WORD lands, so back off by the
        # lead-in. The file keeps its head and tail; only the delay changes.
        placed.append(dict(line=lid, path=dst, file_start=line["start"] - t["lex_start_s"],
                           anchor=line["start"], lex_start=t["lex_start_s"],
                           spoken_s=t["spoken_s"], duration_s=t["duration_s"]))

    # --- step 8: minimal EQ, per-line static gain, one continuous master
    ins, chains, mixes = [], [], []
    for i, p in enumerate(placed):
        m = loudnorm_json(p["path"])
        gain = VOICE_LUFS - float(m["input_i"])
        d = int(round(max(0.0, p["file_start"]) * 1000))
        ins += ["-i", str(p["path"])]
        chains.append(f"[{i}:a]volume={gain:.2f}dB,{EQ},aresample=48000,"
                      f"aformat=channel_layouts=stereo,adelay={d}|{d}[v{i}]")
        mixes.append(f"[v{i}]")
        end = p["file_start"] + p["duration_s"]
        print(f"line{p['line']}: {m['input_i']} LUFS  gain {gain:+.2f} dB  "
              f"file at {p['file_start']:.2f}s  first word {p['anchor']:.2f}s  ends {end:.2f}s",
              flush=True)
    narration = WORK / "narration_master.wav"
    run([FF, "-y", "-hide_banner", *ins, "-filter_complex",
         ";".join(chains) + f";{''.join(mixes)}amix=inputs={len(mixes)}:normalize=0,"
         f"apad=whole_dur={DURATION}[out]",
         "-map", "[out]", "-c:a", "pcm_f32le", str(narration)])
    print(f"\nnarration master: {narration}  ({loudnorm_json(narration)['input_i']} LUFS)", flush=True)

    # --- step 10: music last, then master and mux
    premix = WORK / "premix.wav"
    run([FF, "-y", "-hide_banner", "-i", str(narration), "-i", str(SCORE), "-filter_complex",
         "[0:a][1:a]amix=inputs=2:normalize=0,alimiter=limit=0.97:level=false[out]",
         "-map", "[out]", "-c:a", "pcm_f32le", str(premix)])
    m = loudnorm_json(premix)
    final = WORK / "final_mix.wav"
    run([FF, "-y", "-hide_banner", "-i", str(premix), "-af",
         f"loudnorm=I={MASTER_I}:TP={MASTER_TP}:LRA=15:linear=true:"
         f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
         f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}",
         "-ar", "48000", "-c:a", "pcm_s16le", str(final)])

    fm = loudnorm_json(final)
    tp = true_peak(final)
    print(f"premix {m['input_i']} LUFS -> master {fm['input_i']} LUFS, true peak {tp:.2f} dBFS",
          flush=True)
    if tp > -0.5:
        print("REFUSING TO MUX: master is hotter than -0.5 dBTP", flush=True)
        return 1

    run([FF, "-y", "-hide_banner", "-i", str(VIDEO), "-i", str(final),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
         "-shortest", str(OUT_MP4)])

    md5 = lambda f: run([FF, "-hide_banner", "-i", str(f), "-map", "0:v", "-c", "copy",
                         "-f", "md5", "-"]).strip().splitlines()[-1]
    a, b = md5(VIDEO), md5(OUT_MP4)
    print(f"\nwrote {OUT_MP4}")
    print(f"video md5 source {a}")
    print(f"video md5 muxed  {b}")
    print("picture identical" if a == b else "PICTURE CHANGED — investigate")

    (WORK / "v8-report.json").write_text(json.dumps(dict(
        engine="hexgrad/Kokoro-82M", voice="am_onyx", speed=0.78, atempo=None,
        eq=EQ, ducking=False, compression=False,
        voice_target_lufs=VOICE_LUFS, master_lufs=float(fm["input_i"]),
        master_true_peak_dbfs=round(tp, 2), score=str(SCORE),
        restoration=sr_report,
        placement=[{k: (str(v) if isinstance(v, Path) else v) for k, v in p.items()}
                   for p in placed],
        video_md5_source=a, video_md5_muxed=b), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
