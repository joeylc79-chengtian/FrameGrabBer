from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import uuid

from video_info import ParsedVideoInfo


def build_thumbnail(ffmpeg_exe: str, info: ParsedVideoInfo) -> str | None:
    output_dir = os.path.join(tempfile.gettempdir(), "video_frame_extractor_thumbs")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{uuid.uuid4().hex}.png")
    seek_seconds = min(max(0.0, info.duration * 0.1), 1.0)
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    command = [
        ffmpeg_exe,
        "-y",
        "-ss",
        "%.3f" % seek_seconds,
        "-i",
        info.path,
        "-frames:v",
        "1",
        "-vf",
        "scale=144:-1",
        output_path,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            creationflags=creationflags,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not os.path.isfile(output_path):
        return None
    return output_path
