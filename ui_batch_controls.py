from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence

from theme import FONT_FAMILY, Theme
from ui_models import ExportSettingsState, VideoItem
from ui_widgets import TimeSlider, input_entry, muted_label


class PerVideoFpsControls(tk.Frame):
    def __init__(self, master: tk.Misc, theme: Theme) -> None:
        super().__init__(master, bg=theme.panel)
        self._theme = theme

    def render(self, items: Sequence[VideoItem], enabled: bool) -> None:
        for child in self.winfo_children():
            child.destroy()
        if not items:
            muted_label(self, self._theme, "导入多个视频后可分别设置帧率", 8).pack(anchor="w")
            return
        if not enabled:
            muted_label(self, self._theme, "关闭时，所有视频使用上方统一帧率", 8).pack(anchor="w")
            return
        for index, item in enumerate(items):
            row = tk.Frame(self, bg=self._theme.panel_alt, highlightthickness=1, highlightbackground=self._theme.border)
            row.pack(fill="x", pady=(8, 0))
            tk.Label(
                row,
                text=f"{index + 1}. {item.info.name}",
                font=(FONT_FAMILY, 9, "bold"),
                bg=self._theme.panel_alt,
                fg=self._theme.text,
                anchor="w",
            ).pack(side="left", fill="x", expand=True, padx=(12, 8), pady=10)
            tk.Label(
                row,
                text=f"最高 {item.info.fps:.2f}",
                font=(FONT_FAMILY, 8),
                bg=self._theme.panel_alt,
                fg=self._theme.text_subtle,
            ).pack(side="left", padx=(0, 8))
            input_entry(row, self._theme, item.target_fps, 7).pack(side="right", padx=(0, 12), pady=8)


class RangeControls(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        settings: ExportSettingsState,
        on_change: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=theme.panel)
        self._theme = theme
        self._settings = settings
        self._on_change = on_change

    def render(self, items: Sequence[VideoItem]) -> None:
        for child in self.winfo_children():
            child.destroy()
        if not items:
            muted_label(self, self._theme, "导入视频后可设置片段范围", 8).pack(anchor="w")
            return
        if not self._settings.use_time_range.get():
            muted_label(self, self._theme, "开启后，每个视频会显示自己的开始与结束范围", 8).pack(anchor="w")
            return
        for index, item in enumerate(items):
            self._build_video_row(index, item)

    def _build_video_row(self, index: int, item: VideoItem) -> None:
        card = tk.Frame(self, bg=self._theme.panel_alt, highlightthickness=1, highlightbackground=self._theme.border)
        card.pack(fill="x", pady=(8, 0))
        header = tk.Frame(card, bg=self._theme.panel_alt)
        header.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(
            header,
            text=f"{index + 1}. {item.info.name}",
            font=(FONT_FAMILY, 9, "bold"),
            bg=self._theme.panel_alt,
            fg=self._theme.text,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        tk.Label(
            header,
            text=_format_timecode(item.info.duration),
            font=(FONT_FAMILY, 8),
            bg=self._theme.panel_alt,
            fg=self._theme.text_subtle,
        ).pack(side="right")
        self._build_time_row(card, "开始", item, item.start_seconds, item.start_text)
        self._build_time_row(card, "结束", item, item.end_seconds, item.end_text)

    def _build_time_row(
        self,
        master: tk.Misc,
        label_text: str,
        item: VideoItem,
        seconds_var: tk.DoubleVar,
        text_var: tk.StringVar,
    ) -> None:
        row = tk.Frame(master, bg=self._theme.panel_alt)
        row.pack(fill="x", padx=12, pady=(2, 8))
        tk.Label(
            row,
            text=label_text,
            font=(FONT_FAMILY, 8),
            bg=self._theme.panel_alt,
            fg=self._theme.text_subtle,
            width=4,
            anchor="w",
        ).pack(side="left", padx=(0, 6))
        slider = TimeSlider(
            row,
            self._theme,
            seconds_var,
            0.0,
            float(item.info.duration),
            lambda selected=item: self._sync_item_from_slider(selected),
            bg=self._theme.panel_alt,
        )
        slider.pack(side="left", fill="x", expand=True)
        input_entry(row, self._theme, text_var, 9).pack(side="right", padx=(8, 0))

    def _sync_item_from_slider(self, item: VideoItem) -> None:
        if item.syncing:
            return
        start = float(item.start_seconds.get())
        end = float(item.end_seconds.get())
        if start >= end:
            start = max(0.0, end - 0.1)
            item.start_seconds.set(start)
        item.syncing = True
        try:
            item.start_text.set(_format_timecode(start))
            item.end_text.set(_format_timecode(end))
        finally:
            item.syncing = False
        self._on_change()


def _format_timecode(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
