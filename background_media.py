from __future__ import annotations

import queue
import threading

from app_bootstrap import get_ffmpeg_exe
from ui_models import VideoItem
from video_thumbnail import build_thumbnail


def start_ffmpeg_probe(messages: queue.Queue[tuple]) -> None:
    threading.Thread(target=_probe_ffmpeg, args=(messages,), daemon=True).start()


def start_thumbnail_jobs(ffmpeg_exe: str | None, items: list[VideoItem], messages: queue.Queue[tuple]) -> None:
    if not ffmpeg_exe:
        return
    for index, item in enumerate(items):
        if item.thumbnail_status != "pending" or item.thumbnail_path:
            continue
        threading.Thread(target=_build_thumbnail, args=(ffmpeg_exe, index, item, messages), daemon=True).start()


def apply_ffmpeg_ready(app, msg: tuple) -> None:
    _kind, ffmpeg_exe = msg
    app._ffmpeg_exe = ffmpeg_exe
    app._export_actions._ffmpeg_exe = ffmpeg_exe
    app._ffmpeg_ready = True
    if ffmpeg_exe:
        app._set_status("就绪", app._theme.success)
    else:
        app._set_status("未找到 FFmpeg，请确认 imageio-ffmpeg 已安装", app._theme.error)


def apply_thumbnail_ready(app, msg: tuple) -> None:
    _kind, index, video_path, thumbnail_path = msg
    if index >= len(app._items):
        return
    item = app._items[index]
    if item.info.path != video_path:
        return
    item.thumbnail_path = thumbnail_path or ""
    item.thumbnail_status = "ready" if thumbnail_path else "failed"
    app._refresh_queue()


def _probe_ffmpeg(messages: queue.Queue[tuple]) -> None:
    messages.put(("ffmpeg", get_ffmpeg_exe()))


def _build_thumbnail(ffmpeg_exe: str, index: int, item: VideoItem, messages: queue.Queue[tuple]) -> None:
    path = build_thumbnail(ffmpeg_exe, item.info)
    messages.put(("thumbnail", index, item.info.path, path))
