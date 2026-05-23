"""Shared helpers for size formatting and path handling."""

from __future__ import annotations


def format_file_size(size_bytes: int | float | None) -> str:
    """Format byte count as B, KB, MB, or GB."""
    if size_bytes is None or size_bytes <= 0:
        return "Unknown"

    size = float(size_bytes)
    units = ("B", "KB", "MB", "GB", "TB")
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.2f} {units[unit_index]}"


def sanitize_filename(name: str) -> str:
    """Remove characters invalid on Windows paths."""
    invalid = '<>:"/\\|?*'
    cleaned = "".join(c if c not in invalid else "_" for c in name)
    return cleaned.strip(" .") or "download"
