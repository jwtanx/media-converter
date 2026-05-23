"""
Privacy defaults for this app.

Network use:
  - YouTube (or the site in the URL) only, via yt-dlp, to fetch metadata and media.
  - No analytics, update checks, SponsorBlock, or other third-party endpoints from this app.
  - Local ffmpeg conversion does not use the network.

Install (pip): PyPI is contacted only to download packages. Use install_deps.bat
which disables pip's version-check phone-home.
"""

from __future__ import annotations

import os
from typing import Any


def apply_privacy_environment() -> None:
    """Set process env vars before imports that may trigger install/update checks."""
    os.environ.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    os.environ.setdefault("PIP_NO_PYTHON_VERSION_WARNING", "1")
    # Prevent yt-dlp CLI-style self-update if ever invoked as a subprocess
    os.environ.setdefault("YTDLP_NO_UPDATE", "1")


def privacy_ydl_opts(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    yt-dlp options with third-party / extra data exfiltration disabled.

    Does not block required contact with the video host (e.g. youtube.com).
    """
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # No sidecar metadata files
        "writeinfojson": False,
        "writethumbnail": False,
        "writesubtitles": False,
        "writeautomaticsub": False,
        "writedescription": False,
        "getcomments": False,
        "writelink": False,
        "writeurllink": False,
        "writewebloclink": False,
        "writedesktoplink": False,
        # No embedding extra network-fetched assets into output
        "embedthumbnail": False,
        "embed_metadata": False,
        "embed_chapters": False,
        # No SponsorBlock API (sponsor.ajay.app)
        "no_sponsorblock": True,
        "sponsorblock_remove": set(),
        "sponsorblock_mark": set(),
        # No persistent yt-dlp cache on disk (avoids stored URLs/ids in cache dir)
        "cachedir": False,
        # No browser cookie import
        "cookiesfrombrowser": None,
        "cookiefile": None,
    }
    if extra:
        opts.update(extra)
    return opts
