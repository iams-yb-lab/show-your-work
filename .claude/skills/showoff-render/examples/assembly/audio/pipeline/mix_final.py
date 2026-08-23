"""Assemble the final mix: chosen Chatterbox lines + surviving score -> mp4.

Per line: measure integrated loudness, apply a *static* gain to -16 LUFS
(no dynamic processing on the voice — the humanising chains are what got
rejected). Music ducks under speech via sidechain compression. The sum is
two-pass loudnormed to -14 LUFS / -1 dBTP (linear), then muxed -c:v copy
so the picture stays MD5-identical.
"""
import json, os, subprocess, sys
from pathlib import Path

FF = r"C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
MEDIA = Path(r"C:\Users\<user>\AppData\Local\Temp\temperature-controller-media")
CB = MEDIA / (sys.argv[1] if len(sys.argv) > 1 else "chatterbox")
# The silent picture to mux against. No default: naming one project's render is what made this
# script unusable anywhere else. Set SHOWOFF_PICTURE to your own file.
VIDEO = Path(os.environ.get("SHOWOFF_PICTURE", ""))
SCORE = MEDIA / os.environ.get("SCORE_WAV", "cinematic_score.wav")
OUT_MP4 = MEDIA / (sys.argv[2] if len(sys.argv) > 2 else "assembly_purple_v2_epic_v3.mp4")
# optional per-voice-line filter chain (e.g. mic-character EQ), inserted after gain
VOICE_FX = sys.argv[3] if len(sys.argv) > 3 else ""
# "noduck" anywhere in argv: score runs untouched at full level, voice on top
NO_DUCK = "noduck" in sys.argv

VOICE_I = -13.5 if NO_DUCK else -16.0  # per-line integrated target before mixing


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-3000:])
        sys.exit(1)
    return p.stderr  # ffmpeg logs to stderr


def measure_loudnorm(path):
    err = run([FF, "-hide_banner", "-i", str(path),
               "-af", "loudnorm=I=-16:TP=-1.5:print_format=json", "-f", "null", "-"])
    j = err[err.rindex("{"): err.rindex("}") + 1]
    return json.loads(j)


def main():
    manifest = json.loads((CB / "manifest.json").read_text())

    # 1) two narration buses: the real one, and a sidechain copy advanced
    #    by SC_LEAD so the music is already down when the voice enters
    SC_LEAD = 0.35
    for which, lead in (("narration_bus", 0.0), ("narration_sc", SC_LEAD)):
        inputs, chains, mixes = [], [], []
        for i, line in enumerate(manifest):
            path = CB / f"line{line['line']}_best.wav"
            m = measure_loudnorm(path)
            gain = VOICE_I - float(m["input_i"])
            delay_ms = int(round(max(0.0, line["start"] - lead) * 1000))
            inputs += ["-i", str(path)]
            line_fx = os.environ.get(f"VOICE_FX_{line['line']}", VOICE_FX)
            fx = (line_fx + ",") if line_fx else ""
            chains.append(
                f"[{i}:a]volume={gain:.2f}dB,{fx}aresample=48000,aformat=channel_layouts=stereo,"
                f"adelay={delay_ms}|{delay_ms}[v{i}]")
            mixes.append(f"[v{i}]")
            if lead == 0.0:
                print(f"line {line['line']}: input_i={m['input_i']} LUFS, gain {gain:+.2f} dB, at {line['start']}s")
        fc = ";".join(chains) + f";{''.join(mixes)}amix=inputs={len(mixes)}:normalize=0,apad=whole_dur=84[out]"
        run([FF, "-y", "-hide_banner", *inputs, "-filter_complex", fc,
             "-map", "[out]", "-c:a", "pcm_f32le", str(CB / f"{which}.wav")])
    narr_wav = CB / "narration_bus.wav"

    # 2) sum with the score — ducked via the advanced sidechain, or untouched.
    #    ROOM_TONE_DB (e.g. "-56"): adds a constant band-limited pink room-tone
    #    bed at that RMS level, so the mix never falls to digital silence.
    premix = CB / "premix.wav"
    room_db = os.environ.get("ROOM_TONE_DB")
    air_in, air_fc = [], ""
    air_mix = ""
    if room_db is not None:
        air_in = ["-f", "lavfi", "-i", "anoisesrc=color=pink:sample_rate=48000:duration=84:amplitude=0.05:seed=20260812"]
        air_fc = (f"[3:a]highpass=f=150,lowpass=f=8000,volume={float(room_db)+32:.1f}dB,"
                  f"aformat=channel_layouts=stereo[air];")
        air_mix = "[air]"
    n_mix = 3 if air_mix else 2
    if NO_DUCK:
        fc = f"{air_fc}[1:a][0:a]{air_mix}amix=inputs={n_mix}:normalize=0,alimiter=limit=0.97:level=false[out]"
    else:
        fc = (f"{air_fc}[1:a][2:a]sidechaincompress=threshold=0.015:ratio=10:attack=80:release=1000:makeup=1[m];"
              f"[m][0:a]{air_mix}amix=inputs={n_mix}:normalize=0,alimiter=limit=0.97:level=false[out]")
    run([FF, "-y", "-hide_banner", "-i", str(narr_wav), "-i", str(SCORE),
         "-i", str(CB / "narration_sc.wav"), *air_in,
         "-filter_complex", fc, "-map", "[out]", "-c:a", "pcm_f32le", str(premix)])

    # 3) two-pass linear loudnorm to -14 LUFS / -1 dBTP
    m = measure_loudnorm(premix)
    ln = (f"loudnorm=I=-14:TP=-1.0:LRA=15:linear=true:"
          f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}")
    final_wav = CB / "final_mix.wav"
    run([FF, "-y", "-hide_banner", "-i", str(premix), "-af", ln,
         "-ar", "48000", "-c:a", "pcm_s16le", str(final_wav)])
    print("premix:", m["input_i"], "LUFS ->", measure_loudnorm(final_wav)["input_i"], "LUFS (target -14)")

    # 4) mux, video untouched
    run([FF, "-y", "-hide_banner", "-i", str(VIDEO), "-i", str(final_wav),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
         "-shortest", str(OUT_MP4)])
    print("wrote", OUT_MP4)

    # verify picture untouched
    md5 = lambda f: run([FF, "-hide_banner", "-i", str(f), "-map", "0:v", "-c", "copy", "-f", "md5", "-"]).strip().splitlines()[-1]
    print("video md5 original:", md5(VIDEO))
    print("video md5 muxed:   ", md5(OUT_MP4))


if __name__ == "__main__":
    main()
