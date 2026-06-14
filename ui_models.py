from __future__ import annotations

import tkinter as tk

from video_info import ParsedVideoInfo


class VideoItem:
    __slots__ = (
        "end_seconds",
        "end_text",
        "info",
        "start_seconds",
        "start_text",
        "syncing",
        "target_fps",
        "use_range",
    )

    def __init__(
        self,
        info: ParsedVideoInfo,
        use_range: tk.BooleanVar,
        start_seconds: tk.DoubleVar,
        end_seconds: tk.DoubleVar,
        start_text: tk.StringVar,
        end_text: tk.StringVar,
        target_fps: tk.StringVar,
    ) -> None:
        self.info = info
        self.use_range = use_range
        self.start_seconds = start_seconds
        self.end_seconds = end_seconds
        self.start_text = start_text
        self.end_text = end_text
        self.target_fps = target_fps
        self.syncing = False


class ExportSettingsState:
    def __init__(self, root: tk.Misc) -> None:
        self.interval = tk.StringVar(root, value="每帧")
        self.custom_step = tk.StringVar(root, value="5")
        self.use_target_fps = tk.BooleanVar(root, value=False)
        self.target_fps = tk.StringVar(root, value="24")
        self.use_per_video_fps = tk.BooleanVar(root, value=False)
        self.use_time_range = tk.BooleanVar(root, value=False)
        self.make_preview = tk.BooleanVar(root, value=False)
        self.image_format = tk.StringVar(root, value="png")
        self.output_mode = tk.StringVar(root, value="source")
        self.output_dir = tk.StringVar(root, value="")
