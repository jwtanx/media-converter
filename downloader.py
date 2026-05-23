"""YouTube video and audio download logic via yt-dlp."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yt_dlp

from privacy import privacy_ydl_opts
from utils import format_file_size, sanitize_filename


ProgressCallback = Callable[[str], None]


@dataclass
class FormatOption:
    format_id: str
    label: str
    ext: str
    resolution: str | None
    abr: float | None
    size_bytes: int | None

    @property
    def size_label(self) -> str:
        return format_file_size(self.size_bytes)


def _format_size_from_entry(fmt: dict[str, Any]) -> int | None:
    if fmt.get("filesize"):
        return int(fmt["filesize"])
    if fmt.get("filesize_approx"):
        return int(fmt["filesize_approx"])
    return None


def _video_label(fmt: dict[str, Any]) -> str:
    height = fmt.get("height")
    res = f"{height}p" if height else "unknown"
    ext = fmt.get("ext", "?")
    vcodec = fmt.get("vcodec", "none")
    note = " (no video)" if vcodec in (None, "none") else ""
    size = format_file_size(_format_size_from_entry(fmt))
    return f"{res} · {ext.upper()}{note} · ~{size}"


def _audio_label(fmt: dict[str, Any]) -> str:
    abr = fmt.get("abr")
    abr_str = f"{int(abr)} kbps" if abr else "unknown bitrate"
    ext = fmt.get("ext", "?")
    size = format_file_size(_format_size_from_entry(fmt))
    return f"{abr_str} · {ext.upper()} · ~{size}"


def fetch_video_info(url: str) -> dict[str, Any]:
    opts = privacy_ydl_opts({"skip_download": True})
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def _estimate_merged_size(info: dict[str, Any], height: int) -> int | None:
    """Sum best video at height and best audio stream sizes when known."""
    video_size: int | None = None
    audio_size: int | None = None
    for fmt in info.get("formats") or []:
        fmt_height = fmt.get("height") or 0
        size = _format_size_from_entry(fmt)
        if fmt.get("vcodec") not in (None, "none") and fmt_height == height and size:
            if video_size is None or size > video_size:
                video_size = size
        if fmt.get("acodec") not in (None, "none") and fmt.get("vcodec") in (None, "none"):
            if size and (audio_size is None or size > audio_size):
                audio_size = size
    if video_size and audio_size:
        return video_size + audio_size
    return video_size or audio_size


def list_video_formats(url: str) -> tuple[str, list[FormatOption]]:
    info = fetch_video_info(url)
    title = info.get("title", "video")
    heights: set[int] = set()

    for fmt in info.get("formats") or []:
        if fmt.get("vcodec") in (None, "none"):
            continue
        height = fmt.get("height")
        if height:
            heights.add(int(height))

    options: list[FormatOption] = []
    for height in sorted(heights, reverse=True):
        size = _estimate_merged_size(info, height)
        options.append(
            FormatOption(
                format_id=f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
                label=f"{height}p · merged video+audio · ~{format_file_size(size)}",
                ext="mp4",
                resolution=f"{height}p",
                abr=None,
                size_bytes=size,
            )
        )

    if not options:
        total = info.get("filesize") or info.get("filesize_approx")
        options.append(
            FormatOption(
                format_id="bestvideo+bestaudio/best",
                label=f"Best available · ~{format_file_size(total)}",
                ext="mp4",
                resolution="best",
                abr=None,
                size_bytes=total,
            )
        )
    return title, options


def list_audio_formats(url: str) -> tuple[str, list[FormatOption]]:
    info = fetch_video_info(url)
    title = info.get("title", "audio")
    seen: set[str] = set()
    options: list[FormatOption] = []

    for fmt in info.get("formats") or []:
        if fmt.get("acodec") in (None, "none"):
            continue
        if fmt.get("vcodec") not in (None, "none"):
            continue
        abr = fmt.get("abr")
        ext = fmt.get("ext", "m4a")
        key = f"{abr}-{ext}"
        if key in seen:
            continue
        seen.add(key)
        options.append(
            FormatOption(
                format_id=str(fmt["format_id"]),
                label=_audio_label(fmt),
                ext=ext,
                resolution=None,
                abr=float(abr) if abr else None,
                size_bytes=_format_size_from_entry(fmt),
            )
        )

    options.sort(key=lambda o: o.abr or 0, reverse=True)
    if not options:
        options.append(
            FormatOption(
                format_id="bestaudio/best",
                label="Best available · MP3 · ~Unknown",
                ext="mp3",
                resolution=None,
                abr=None,
                size_bytes=info.get("filesize") or info.get("filesize_approx"),
            )
        )
    return title, options


def _progress_hook(on_progress: ProgressCallback):
    def hook(status: dict[str, Any]) -> None:
        if status.get("status") != "downloading":
            return
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        downloaded = status.get("downloaded_bytes", 0)
        pct = status.get("_percent_str", "").strip()
        speed = status.get("_speed_str", "").strip()
        if total:
            msg = f"Downloading… {pct} ({format_file_size(downloaded)} / {format_file_size(total)}) {speed}"
        else:
            msg = f"Downloading… {pct} {speed}"
        on_progress(msg)

    return hook


def download_video(
    url: str,
    output_dir: Path,
    format_id: str,
    container: str,
    on_progress: ProgressCallback,
    on_log: ProgressCallback,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(title)s.%(ext)s")

    ydl_opts = privacy_ydl_opts(
        {
            "format": format_id,
            "outtmpl": outtmpl,
            "merge_output_format": container,
            "progress_hooks": [_progress_hook(on_progress)],
            "postprocessors": [],
        }
    )

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
        if container and path.suffix.lower() != f".{container.lower()}":
            candidate = path.with_suffix(f".{container}")
            if candidate.exists():
                path = candidate
        on_log(f"Saved: {path}")
        return path


def download_audio(
    url: str,
    output_dir: Path,
    format_id: str,
    audio_format: str,
    on_progress: ProgressCallback,
    on_log: ProgressCallback,
) -> Path:
    """Download audio only from YouTube (no local video conversion)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(title)s.%(ext)s")

    postprocessors: list[dict[str, Any]] = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_format,
            "preferredquality": "0",
        }
    ]

    ydl_opts = privacy_ydl_opts(
        {
            "format": format_id,
            "outtmpl": outtmpl,
            "progress_hooks": [_progress_hook(on_progress)],
            "postprocessors": postprocessors,
        }
    )

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = sanitize_filename(info.get("title", "audio"))
        path = output_dir / f"{title}.{audio_format}"
        if not path.exists():
            prepared = Path(ydl.prepare_filename(info))
            path = prepared.with_suffix(f".{audio_format}")
        on_log(f"Saved: {path}")
        return path
