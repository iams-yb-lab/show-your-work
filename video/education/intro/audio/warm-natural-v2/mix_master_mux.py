"""Mix the restored voice and happy score, then stream-copy the original video."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import soundfile as sf


FFMPEG = Path(
    r"C:\Users\iams1\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
)
FFPROBE = FFMPEG.with_name("ffprobe.exe")


def run(arguments: list[str], *, stderr: bool = False) -> str:
    process = subprocess.run(arguments, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if process.returncode:
        print(process.stderr[-8000:])
        raise RuntimeError(f"Command failed with exit code {process.returncode}: {arguments[0]}")
    return process.stderr if stderr else process.stdout


def probe(path: Path) -> dict:
    output = run([
        str(FFPROBE), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ])
    return json.loads(output)


def duration(path: Path) -> float:
    return float(probe(path)["format"]["duration"])


def loudness(path: Path) -> dict:
    log = run([
        str(FFMPEG), "-hide_banner", "-i", str(path), "-af",
        "loudnorm=I=-16:TP=-1.5:print_format=json", "-f", "null", "-",
    ], stderr=True)
    return json.loads(log[log.rindex("{"):log.rindex("}") + 1])


def linear_loudnorm(source: Path, target: Path, target_i: float, target_tp: float) -> None:
    measured = loudness(source)
    filter_value = (
        f"loudnorm=I={target_i}:TP={target_tp}:LRA=15:linear=true:"
        f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
    )
    run([
        str(FFMPEG), "-y", "-hide_banner", "-i", str(source), "-af", filter_value,
        "-ar", "48000", "-c:a", "pcm_s24le", str(target),
    ])


def video_stream_md5(path: Path) -> str:
    return run([
        str(FFMPEG), "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-map", "0:v:0", "-c", "copy", "-f", "md5", "-",
    ]).strip()


def temporary_path(final: Path) -> Path:
    return final.with_name(f"{final.stem}.partial{final.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", type=Path, required=True)
    parser.add_argument("--music", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--audio-out", type=Path, required=True)
    parser.add_argument("--video-out", type=Path, required=True)
    args = parser.parse_args()

    voice = args.voice.resolve()
    music = args.music.resolve()
    source_video = args.video.resolve()
    work = args.work.resolve()
    final_audio = args.audio_out.resolve()
    final_video = args.video_out.resolve()
    work.mkdir(parents=True, exist_ok=True)
    final_audio.parent.mkdir(parents=True, exist_ok=True)
    if final_audio.exists() or final_video.exists():
        raise FileExistsError("Final revision already exists; refusing to replace it")
    audio_partial = temporary_path(final_audio)
    video_partial = temporary_path(final_video)
    audio_partial.unlink(missing_ok=True)
    video_partial.unlink(missing_ok=True)

    video_duration = duration(source_video)
    manifest = json.loads((voice / "manifest.json").read_text(encoding="utf-8"))
    if len(manifest) != 49:
        raise RuntimeError(f"Expected 49 voice cues, received {len(manifest)}")

    inputs: list[str] = []
    chains: list[str] = []
    labels: list[str] = []
    fit_report: list[dict] = []
    voice_target = -16.0

    for index, entry in enumerate(manifest):
        source = voice / f"line{entry['line']:02d}_best.wav"
        info = sf.info(source)
        clip_duration = info.frames / info.samplerate
        # Tempo is based on spoken content, not the protected breath/post-roll. The quiet tail may
        # overlap the next cue's leading silence; it is never truncated merely to fit a caption box.
        speech_duration = max(
            0.1,
            float(entry["speech_end_in_source"]) - float(entry["source_start"]),
        )
        slot = max(0.3, float(entry["end"]) - float(entry["start"]) - 0.08)
        tempo = max(1.0, speech_duration / slot)
        measured = loudness(source)
        gain = voice_target - float(measured["input_i"])
        delay_ms = round(float(entry["start"]) * 1000)
        inputs.extend(["-i", str(source)])
        tempo_filter = f"atempo={tempo:.8f}," if tempo > 1.0005 else ""
        # Transparent proximity/clarity correction only. No denoise, gate, exciter, reverb,
        # compressor, or headphone-style spectral subtraction.
        eq = (
            "highpass=f=45,"
            "equalizer=f=115:t=q:w=0.9:g=1.7,"
            "equalizer=f=900:t=q:w=1.1:g=-0.5,"
            "equalizer=f=4000:t=q:w=1:g=1.2,"
            "highshelf=f=10000:g=1.8,"
        )
        chains.append(
            f"[{index}:a]{tempo_filter}aresample=48000,{eq}volume={gain:.3f}dB,"
            f"aformat=channel_layouts=stereo,adelay={delay_ms}:all=1[v{index}]"
        )
        labels.append(f"[v{index}]")
        fit_report.append({
            "line": entry["line"],
            "clip_duration": clip_duration,
            "speech_duration": speech_duration,
            "protected_tail_seconds": entry["protected_tail_seconds"],
            "slot": slot,
            "tempo": tempo,
            "gain_db": gain,
        })

    chains.append(
        f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,"
        f"apad=whole_dur={video_duration},atrim=0:{video_duration}[voice]"
    )
    filter_graph = ";".join(chains)
    (work / "narration-filter.txt").write_text(filter_graph, encoding="utf-8")
    narration_bus = work / "narration-bus.wav"
    run([
        str(FFMPEG), "-y", "-hide_banner", *inputs, "-filter_complex", filter_graph,
        "-map", "[voice]", "-c:a", "pcm_f32le", str(narration_bus),
    ])

    music_normalized = work / "happy-welcoming-music-minus29.5.wav"
    linear_loudnorm(music, music_normalized, -29.5, -7.0)
    premix = work / "voice-and-music-premix.wav"
    run([
        str(FFMPEG), "-y", "-hide_banner", "-i", str(narration_bus),
        "-i", str(music_normalized), "-filter_complex",
        f"[0:a][1:a]amix=inputs=2:normalize=0,apad=whole_dur={video_duration},"
        f"atrim=0:{video_duration}[mix]",
        "-map", "[mix]", "-c:a", "pcm_f32le", str(premix),
    ])
    linear_loudnorm(premix, audio_partial, -14.0, -1.0)

    run([
        str(FFMPEG), "-y", "-hide_banner", "-i", str(source_video), "-i", str(audio_partial),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", "-shortest",
        str(video_partial),
    ])
    source_video_md5 = video_stream_md5(source_video)
    output_video_md5 = video_stream_md5(video_partial)
    if source_video_md5 != output_video_md5:
        raise RuntimeError(f"Video stream changed: {source_video_md5} != {output_video_md5}")
    if max(item["tempo"] for item in fit_report) > 1.15 + 1e-6:
        raise RuntimeError("Voice tempo exceeds the approved 1.15x ceiling")

    audio_partial.rename(final_audio)
    video_partial.rename(final_video)
    report = {
        "source_video": str(source_video),
        "final_audio": str(final_audio),
        "final_video": str(final_video),
        "video_stream_md5_identical": True,
        "video_stream_md5": source_video_md5,
        "video_reencoded": False,
        "final_loudness": loudness(final_audio),
        "voice_target_lufs": voice_target,
        "music_target_lufs": -29.5,
        "final_target_lufs": -14.0,
        "final_target_true_peak_db": -1.0,
        "noise_sources": 0,
        "music_ducking": False,
        "voice_denoise": False,
        "voice_gate": False,
        "voice_compression": False,
        "eq": {
            "highpass_hz": 45,
            "body_db_at_115_hz": 1.7,
            "boxiness_db_at_900_hz": -0.5,
            "presence_db_at_4000_hz": 1.2,
            "air_shelf_db_at_10000_hz": 1.8,
        },
        "max_tempo": max(item["tempo"] for item in fit_report),
        "minimum_protected_tail_seconds": min(item["protected_tail_seconds"] for item in fit_report),
        "line_fits": fit_report,
    }
    (work / "mix-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
