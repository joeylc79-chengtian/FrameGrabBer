from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from theme import FONT_FAMILY, Theme, ThemeMode
from ui_widgets import SegmentedControl, button


class AppHeader(tk.Frame):
    def __init__(self, master: tk.Misc, theme: Theme, theme_mode: tk.StringVar, on_theme_change: Callable[[], None]) -> None:
        super().__init__(master, bg=theme.bg)
        self.pack(fill="x")
        tk.Label(
            self,
            text="▦",
            font=(FONT_FAMILY, 18, "bold"),
            bg=theme.bg,
            fg=theme.text,
        ).pack(side="left", padx=(0, 10))
        tk.Label(
            self,
            text="视频逐帧抽图工具 V0.8",
            font=(FONT_FAMILY, 14, "bold"),
            bg=theme.bg,
            fg=theme.text,
        ).pack(side="left")
        self.theme_control = SegmentedControl(
            self,
            theme,
            theme_mode,
            tuple(mode.value for mode in ThemeMode),
            on_theme_change,
        )
        self.theme_control.pack(side="right")


class AppFooter(tk.Frame):
    def __init__(self, master: tk.Misc, theme: Theme) -> None:
        super().__init__(master, bg=theme.bg)
        self.pack(fill="x")
        self.progress = ttk.Progressbar(
            self,
            mode="determinate",
            maximum=100,
            style="App.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x", side="top")
        status_row = tk.Frame(self, bg=theme.bg)
        status_row.pack(fill="x", pady=(8, 0))
        self.status_label = tk.Label(
            status_row,
            text="就绪",
            font=(FONT_FAMILY, 9),
            bg=theme.bg,
            fg=theme.text_subtle,
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        self.progress_label = tk.Label(
            status_row,
            text="",
            font=(FONT_FAMILY, 9),
            bg=theme.bg,
            fg=theme.text_muted,
            anchor="e",
        )
        self.progress_label.pack(side="right")


class ExportActionBar(tk.Frame):
    def __init__(self, master: tk.Misc, theme: Theme, on_start: Callable[[], None]) -> None:
        super().__init__(master, bg=theme.bg)
        self.pack(fill="x", pady=(0, 10))
        self.estimate_label = tk.Label(
            self,
            text="导入视频后会显示预计输出张数",
            font=(FONT_FAMILY, 9),
            bg=theme.bg,
            fg=theme.text_muted,
            anchor="w",
        )
        self.estimate_label.pack(side="left", fill="x", expand=True)
        self.start_button = button(self, theme, "开始导出", on_start, primary=True)
        self.start_button.pack(side="right", ipadx=28, ipady=3)

    def set_estimate(self, text: str) -> None:
        self.estimate_label.configure(text=text)
