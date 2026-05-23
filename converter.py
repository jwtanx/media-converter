"""Convert local video files to audio formats using ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

from utils import format_file_size

ProgressCallback = Callable[[str], None]

# Maps UI quality label to ffmpeg audio bitrate
AUDIO_QUALITY_MAP: dict[str, str] = {
    "320 kbps (best)": "320k",
    "256 kbps": "256k",
    "192 kbps (default)": "192k",
    "128 kbps": "128k",
    "96 kbps": "96k",
    "64 kbps (low)": "64k",
}

AUDIO_FORMATS = ("mp3", "m4a", "wav", "flac", "ogg", "opus")
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".wmv", ".m4v"}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def estimate_output_audio_size(video_path: Path, audio_format: str, quality_label: str) -> str:
    """Rough estimate: use video file size as upper bound; audio is usually smaller."""
    if not video_path.exists():
        return "Unknown"
    video_size = video_path.stat().st_size
    # Compressed audio is typically 5–15% of video for similar duration
    ratio = 0.12 if audio_format in ("mp3", "m4a", "ogg", "opus") else 0.5
    estimate = int(video_size * ratio)
    return f"~{format_file_size(estimate)} (estimate)"


def convert_video_to_audio(
    video_path: Path,
    output_dir: Path,
    audio_format: str,
    quality_label: str,
    on_progress: ProgressCallback,
    on_log: ProgressCallback,
) -> Path:
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg is not installed or not on PATH. "
            "Install ffmpeg and restart the app."
        )

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{video_path.stem}.{audio_format}"
    output_path = output_dir / out_name

    bitrate = AUDIO_QUALITY_MAP.get(quality_label, "192k")
    on_progress(f"Converting to {audio_format.upper()} at {bitrate}…")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
    ]

    if audio_format == "mp3":
        cmd.extend(["-codec:a", "libmp3lame", "-b:a", bitrate])
    elif audio_format == "m4a":
        cmd.extend(["-codec:a", "aac", "-b:a", bitrate])
    elif audio_format == "opus":
        cmd.extend(["-codec:a", "libopus", "-b:a", bitrate])
    elif audio_format == "ogg":
        cmd.extend(["-codec:a", "libvorbis", "-b:a", bitrate])
    elif audio_format == "flac":
        cmd.extend(["-codec:a", "flac"])
    elif audio_format == "wav":
        cmd.extend(["-codec:a", "pcm_s16le"])
    else:
        cmd.extend(["-b:a", bitrate])

    cmd.append(str(output_path))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "Conversion failed").strip()
        raise RuntimeError(err[-500:])

    size = format_file_size(output_path.stat().st_size)
    on_log(f"Saved: {output_path} ({size})")
    on_progress("Conversion complete.")
    return output_path
