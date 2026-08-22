r"""Package the prompt audition: SR + the v7.2 EQ + loudness match, A vs B.

Produces exactly two things to listen to, because the decision is exactly one
question — which narrator. `video/natural-voice/README.md` forbids presenting a
matrix of rendered candidates and asking the listener to pick; this is the
prompt audition it *requires*, run before anything is committed to film.

Both sides get identical treatment, so the treatment cannot bias the choice:
  MossFormer2_SR_48K (gated, per-line clean-resample fallback)
    -> v7.2's condenser EQ
    -> static gain to a common integrated loudness

⚠ The EQ is a RECONSTRUCTION. v7.2's approved chain was passed to
`pipeline/mix_final.py` as an argv string and only ever recorded in prose in
VOICE-LOG.md ("highpass 50 Hz, +2 dB @ 110 Hz, +1.5 dB @ 4 kHz, +3 dB shelf @
10 kHz"). The literal filter string, and its Q values, are not on disk. What is
below is the natural reading of that description, not a recovered original.

Run in `%TEMP%\sr-venv` (clearvoice + torch).
"""
import json
import os
import re
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
AUD = ROOT / "audition"

TAGS = ["A_incumbent", "B_slow078"]
LINES = [1, 6]
GAP_S = 1.5
MATCH_LUFS = -18.0

# see the module docstring: reconstruction, not a recovered original
V72_EQ = (
    "highpass=f=50,"
    "equalizer=f=110:t=q:w=1.0:g=2,"
    "equalizer=f=4000:t=q:w=1.0:g=1.5,"
    "treble=g=3:f=10000"
)

# the method's restoration gates (README.md "Bandwidth restoration")
GATE_WER = 0.12
GATE_DUR_FRAC, GATE_DUR_ABS = 0.012, 0.050
GATE_F0_HZ = 5.0


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-3000:])
        sys.exit(1)
    return p.stderr


def norm_words(s):
    return re.sub(r"[^a-z0-9' ]+", " ", s.lower()).split()


def wer(ref, hyp):
    import difflib

    sm = difflib.SequenceMatcher(a=ref, b=hyp)
    errs = sum(
        max(i2 - i1, j2 - j1)
        for op, i1, i2, j1, j2 in sm.get_opcodes()
        if op != "equal"
    )
    return errs / max(1, len(ref))


def median_f0(y, sr):
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=300, sr=sr)
    f0 = f0[~np.isnan(f0)]
    return float(np.median(f0)) if f0.size else float("nan")


def hf_ratio(y, sr, cutoff=12000.0):
    S = np.abs(np.fft.rfft(y)) ** 2
    freqs = np.fft.rfftfreq(len(y), 1 / sr)
    tot = S.sum()
    return float(S[freqs >= cutoff].sum() / tot) if tot > 0 else 0.0


def integrated_lufs(path):
    err = run([FF, "-hide_banner", "-i", str(path),
               "-af", "loudnorm=I=-16:TP=-1.5:print_format=json", "-f", "null", "-"])
    return float(json.loads(err[err.rindex("{"): err.rindex("}") + 1])["input_i"])


def main():
    from clearvoice import ClearVoice

    cv = ClearVoice(task="speech_super_resolution", model_names=["MossFormer2_SR_48K"])
    import whisper

    asr = whisper.load_model("base.en", device="cuda")

    report = []
    for tag in TAGS:
        d = AUD / tag
        man = json.loads((d / "manifest.json").read_text())
        texts = {l["line"]: l["text"] for l in man["lines"]}
        stage = []

        for lid in LINES:
            src = d / f"line{lid}_audition.wav"
            y0, sr0 = librosa.load(str(src), sr=None)
            dur0, f00 = len(y0) / sr0, median_f0(y0, sr0)

            sr_path = d / f"line{lid}_sr.wav"
            y = np.asarray(cv(input_path=str(src), online_write=False), dtype=np.float32).squeeze()
            sf.write(str(sr_path), y, 48000)

            dur1, f01 = len(y) / 48000, median_f0(y, 48000)
            hyp = asr.transcribe(str(sr_path), language="en")["text"].strip()
            w = wer(norm_words(texts[lid]), norm_words(hyp))
            hf0, hf1 = hf_ratio(y0, sr0), hf_ratio(y, 48000)

            ok = (
                w <= GATE_WER
                and abs(dur1 - dur0) <= GATE_DUR_FRAC * dur0 + GATE_DUR_ABS
                and abs(f01 - f00) <= GATE_F0_HZ
                and hf1 > hf0
            )
            if not ok:
                # the method's fallback: ship a clean 48 kHz resample, never a
                # restoration that changed the performance
                run([FF, "-y", "-hide_banner", "-i", str(src), "-ar", "48000",
                     "-c:a", "pcm_f32le", str(sr_path)])
                print(f"  {tag} line{lid}: SR REJECTED -> clean resample", flush=True)

            print(
                f"  {tag} line{lid}: {dur0:.2f}->{dur1:.2f}s  F0 {f00:.0f}->{f01:.0f} Hz  "
                f"wer={w:.3f}  HF>12k {hf0:.3%}->{hf1:.3%}  {'accept' if ok else 'FALLBACK'}",
                flush=True,
            )
            stage.append(dict(line=lid, sr_accepted=bool(ok), duration_s=round(dur0, 3),
                              median_f0_hz=round(f00, 2), wer=round(w, 4),
                              hf_ratio_before=round(hf0, 6), hf_ratio_after=round(hf1, 6)))

            eq_path = d / f"line{lid}_eq.wav"
            run([FF, "-y", "-hide_banner", "-i", str(sr_path), "-af", V72_EQ,
                 "-ar", "48000", "-c:a", "pcm_f32le", str(eq_path)])

        report.append(dict(tag=tag, prompt_wav=man["prompt_wav"], lines=stage))

    # one common gain per tag, from the tag's own two lines, so A and B are
    # compared at matched loudness and the louder one cannot simply win
    gains = {}
    for tag in TAGS:
        d = AUD / tag
        ls = [integrated_lufs(d / f"line{lid}_eq.wav") for lid in LINES]
        gains[tag] = MATCH_LUFS - float(np.mean(ls))
        print(f"{tag}: lines at {[round(x, 2) for x in ls]} LUFS -> gain {gains[tag]:+.2f} dB",
              flush=True)

    for tag in TAGS:
        d = AUD / tag
        ins, chains, order = [], [], []
        for i, lid in enumerate(LINES):
            ins += ["-i", str(d / f"line{lid}_eq.wav")]
            chains.append(f"[{i}:a]volume={gains[tag]:.2f}dB,aformat=channel_layouts=mono[c{i}]")
            order.append(f"[c{i}]")
            if i < len(LINES) - 1:
                chains.append(
                    f"aevalsrc=0:d={GAP_S}:s=48000,aformat=channel_layouts=mono[g{i}]")
                order.append(f"[g{i}]")
        fc = ";".join(chains) + f";{''.join(order)}concat=n={len(order)}:v=0:a=1[out]"
        out_m4a = ROOT / f"audition_{tag}.m4a"
        run([FF, "-y", "-hide_banner", *ins, "-filter_complex", fc, "-map", "[out]",
             "-c:a", "aac", "-b:a", "256k", str(out_m4a)])
        print(f"wrote {out_m4a}", flush=True)

    (ROOT / "audition-report.json").write_text(
        json.dumps(
            dict(
                eq_chain=V72_EQ,
                eq_provenance="RECONSTRUCTED from VOICE-LOG.md prose; literal v7.2 string not on disk",
                match_lufs=MATCH_LUFS,
                gains_db={k: round(v, 2) for k, v in gains.items()},
                restoration_gates=dict(wer=GATE_WER, duration_frac=GATE_DUR_FRAC,
                                       duration_abs_s=GATE_DUR_ABS, median_f0_hz=GATE_F0_HZ),
                tags=report,
            ),
            indent=2,
        )
    )
    print(f"wrote {ROOT / 'audition-report.json'}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
