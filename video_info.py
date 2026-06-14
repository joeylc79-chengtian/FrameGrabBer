from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm", ".m4v", ".mpg", ".mpeg"}


@dataclass(frozen=True)
class ParsedVideoInfo:
    path: str
    name: str
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float


def is_video_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS


def parse_video_info(video_path: str, ffmpeg_exe: str) -> ParsedVideoInfo | None:
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        result = subprocess.run(
            [ffmpeg_exe, "-i", video_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        stderr = result.stderr
        duration = _parse_duration(stderr)
        width, height = _parse_size(stderr)
        fps = _parse_fps(stderr)
        if width <= 0 or height <= 0 or duration <= 0:
            return None
        return ParsedVideoInfo(
            path=video_path,
            name=os.path.basename(video_path),
            width=width,
            height=height,
            fps=round(fps, 2),
            total_frames=int(duration * fps),
            duration=duration,
        )
    except OSError:
        return None


def _parse_duration(stderr: str) -> float:
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", stderr)
    if not match:
        return 0.0
    hours, minutes, seconds = map(int, match.groups()[:3])
    fraction = float("0." + match.group(4))
    return hours * 3600 + minutes * 60 + seconds + fraction


def _parse_size(stderr: str) -> tuple[int, int]:
    match = re.search(r"Stream #\d+:\d+.*Video:.*\s(\d+)x(\d+)", stderr)
    if not match:
        return 0, 0
    return int(match.group(1)), int(match.group(2))


def _parse_fps(stderr: str) -> float:
    match = re.search(r"(\d+\.?\d*)\s*fps", stderr)
    if not match:
        return 30.0
    return float(match.group(1))
