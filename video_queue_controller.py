from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from export_plan import ExportPlanError, parse_timecode
from ui_models import VideoItem
from video_info import is_video_file, parse_video_info


@dataclass(frozen=True, slots=True)
class AddVideosResult:
    added: int
    skipped: int
    reached_limit: bool


def add_video_paths(
    root: tk.Misc,
    items: list[VideoItem],
    paths: list[str],
    ffmpeg_exe: str,
    max_count: int,
    target_fps_text: str,
    on_item_text_change: Callable[[VideoItem], None],
    on_item_fps_change: Callable[[], None],
) -> AddVideosResult:
    existing = {os.path.normcase(os.path.abspath(item.info.path)) for item in items}
    added = 0
    skipped = 0
    reached_limit = False
    for path in paths:
        if len(items) >= max_count:
            reached_limit = True
            break
        if not os.path.isfile(path) or not is_video_file(path):
            skipped += 1
            continue
        normalized = os.path.normcase(os.path.abspath(path))
        if normalized in existing:
            skipped += 1
            continue
        info = parse_video_info(path, ffmpeg_exe)
        if not info:
            skipped += 1
            continue
        item = create_video_item(root, info, target_fps_text, on_item_text_change, on_item_fps_change)
        items.append(item)
        existing.add(normalized)
        added += 1
    return AddVideosResult(added=added, skipped=skipped, reached_limit=reached_limit)


def extract_video_paths(root: tk.Misc, raw_data: str) -> list[str]:
    if not raw_data:
        return []
    try:
        paths = list(root.tk.splitlist(raw_data))
    except tk.TclError:
        paths = [raw_data]
    return [path.strip("{}") for path in paths if is_video_file(path.strip("{}"))]


def create_video_item(
    root: tk.Misc,
    info,
    target_fps_text: str,
    on_text_change: Callable[[VideoItem], None],
    on_fps_change: Callable[[], None],
) -> VideoItem:
    item = VideoItem(
        info=info,
        use_range=tk.BooleanVar(root, value=False),
        start_seconds=tk.DoubleVar(root, value=0.0),
        end_seconds=tk.DoubleVar(root, value=float(info.duration)),
        start_text=tk.StringVar(root, value="00:00"),
        end_text=tk.StringVar(root, value=format_timecode(info.duration)),
        target_fps=tk.StringVar(root, value=target_fps_text),
    )
    item.start_text.trace_add("write", lambda *_args, current=item: on_text_change(current))
    item.end_text.trace_add("write", lambda *_args, current=item: on_text_change(current))
    item.target_fps.trace_add("write", lambda *_args: on_fps_change())
    return item


def sync_item_from_text(item: VideoItem) -> bool:
    if item.syncing:
        return False
    try:
        start = parse_timecode(item.start_text.get())
        end = parse_timecode(item.end_text.get())
    except ExportPlanError:
        return True
    duration = float(item.info.duration)
    item.syncing = True
    try:
        item.start_seconds.set(min(max(0.0, start), duration))
        item.end_seconds.set(min(max(0.0, end), duration))
    finally:
        item.syncing = False
    return True


def format_timecode(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
