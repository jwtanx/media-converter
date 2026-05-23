# Media Converter

Desktop app for downloading YouTube videos and audio, plus converting local video files to audio. Built with Python, [yt-dlp](https://github.com/yt-dlp/yt-dlp), and ffmpeg.

## Download (Windows)

**[Releases](https://github.com/jwtanx/media-converter/releases)** — get `YouTubeDownloader.exe` from the latest release. No Python install required.

| Release | Notes |
|---------|--------|
| [v1.0.0](https://github.com/jwtanx/media-converter/releases/tag/v1.0.0) | First release — standalone Windows executable |

### Requirements for the .exe

- **ffmpeg** must be installed and on your `PATH` ([download](https://ffmpeg.org/download.html)). Needed for merging video+audio, YouTube audio extraction, and the Convert tab.

## Features

- **Download Video** — YouTube URL, resolution picker, container (default MP4), estimated file size
- **Download Audio** — YouTube audio only (default MP3; also M4A, WAV, FLAC, OGG, Opus)
- **Convert to Audio** — Convert local video files on disk to audio with quality presets

## Run from source

```powershell
cd youtube-downloader
python -m venv .venv
.\install_deps.bat
.\.venv\Scripts\python.exe main.py
```

## Build executable

```powershell
.\build_exe.bat
```

Output: `dist\YouTubeDownloader.exe`

## Privacy

This app does not send analytics or telemetry. Downloads contact only the video host (e.g. YouTube) via yt-dlp. See `privacy.py` for hardened defaults (no SponsorBlock, no sidecar metadata files, no yt-dlp disk cache).

Install dependencies with `install_deps.bat` to avoid pip’s version-check phone-home.

## License

Use responsibly and comply with the terms of service of sites you download from.
