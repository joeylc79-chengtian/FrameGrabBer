from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import filedialog, ttk

from theme import FONT_FAMILY, Theme
from ui_batch_controls import PerVideoFpsControls, RangeControls
from ui_models import ExportSettingsState, VideoItem
from ui_widgets import ScrollableFrame, button, input_entry, muted_label, panel, section_title


class ExportSettingsView(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        state: ExportSettingsState,
        on_change: Callable[[], None],
        on_target_fps_toggle: Callable[[], None],
        on_time_range_toggle: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=theme.bg)
        self._theme = theme
        self._state = state
        self._on_change = on_change
        self._on_target_fps_toggle = on_target_fps_toggle
        self._on_time_range_toggle = on_time_range_toggle
        self._items: Sequence[VideoItem] = ()
        self._selected_index = 0
        self._container = panel(self, theme)
        self._container.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        self._scroll = ScrollableFrame(self._container, self._theme)
        self._scroll.pack(fill="both", expand=True, padx=14, pady=14)
        self._content = tk.Frame(self._scroll.content, bg=self._theme.panel)
        self._content.pack(fill="both", expand=True, padx=8, pady=6)
        section_title(self._content, self._theme, "导出设置").pack(anchor="w")
        self._build_interval_mode()
        self._build_target_fps()
        self._build_time_range()
        self._build_preview()
        self._divider()
        self._build_format()
        self._build_output_dir()

    def _build_interval_mode(self) -> None:
        tk.Label(
            self._content,
            text="抽帧模式",
            font=(FONT_FAMILY, 10),
            bg=self._theme.panel,
            fg=self._theme.text_muted,
        ).pack(anchor="w", pady=(22, 8))
        row = tk.Frame(self._content, bg=self._theme.panel)
        row.pack(fill="x")
        for text, value in (("逐帧", "每帧"), ("每秒一帧", "每秒1帧"), ("每几帧抽一帧", "自定义")):
            option = tk.Frame(row, bg=self._theme.panel)
            option.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk.Radiobutton(
                option,
                text=text,
                value=value,
                variable=self._state.interval,
                command=self._on_change,
                font=(FONT_FAMILY, 10),
                bg=self._theme.panel,
                fg=self._theme.text,
                activebackground=self._theme.panel,
                activeforeground=self._theme.text,
                selectcolor=self._theme.panel,
            ).pack(anchor="w")
            if value == "自定义":
                custom = tk.Frame(option, bg=self._theme.panel)
                custom.pack(anchor="w", padx=(24, 0), pady=(2, 0))
                input_entry(custom, self._theme, self._state.custom_step, 5).pack(side="left")
                tk.Label(
                    custom,
                    text="帧",
                    font=(FONT_FAMILY, 9),
                    bg=self._theme.panel,
                    fg=self._theme.text_muted,
                ).pack(
                    side="left",
                    padx=(6, 0),
                )

    def _build_target_fps(self) -> None:
        self._target_frame = tk.Frame(self._content, bg=self._theme.panel)
        self._target_frame.pack(fill="x", pady=(16, 4))
        tk.Checkbutton(
            self._target_frame,
            text="指定帧率导出",
            variable=self._state.use_target_fps,
            command=self._on_target_fps_toggle,
            font=(FONT_FAMILY, 10),
            bg=self._theme.panel,
            fg=self._theme.text,
            activebackground=self._theme.panel,
            activeforeground=self._theme.text,
            selectcolor=self._theme.panel,
        ).pack(side="left")
        self._target_entry = input_entry(self._target_frame, self._theme, self._state.target_fps, 8)
        self._target_entry.pack(side="right")
        tk.Label(
            self._target_frame,
            text="fps",
            font=(FONT_FAMILY, 9),
            bg=self._theme.panel,
            fg=self._theme.text_muted,
        ).pack(side="right", padx=(0, 8))

        self._per_video_frame = tk.Frame(self._content, bg=self._theme.panel)
        tk.Checkbutton(
            self._per_video_frame,
            text="不同视频分别设置帧率",
            variable=self._state.use_per_video_fps,
            command=self._on_change,
            font=(FONT_FAMILY, 9),
            bg=self._theme.panel,
            fg=self._theme.text_muted,
            activebackground=self._theme.panel,
            activeforeground=self._theme.text,
            selectcolor=self._theme.panel,
        ).pack(anchor="w")
        muted_label(self._per_video_frame, self._theme, "批量导出时可让每个视频使用自己的目标帧率", 8).pack(anchor="w")
        self._per_video_fps = PerVideoFpsControls(self._per_video_frame, self._theme)
        self._per_video_fps.pack(fill="x", pady=(4, 0))

    def _build_time_range(self) -> None:
        self._range_frame = tk.Frame(self._content, bg=self._theme.panel)
        self._range_frame.pack(fill="x", pady=(16, 6))
        tk.Checkbutton(
            self._range_frame,
            text="只导出视频片段",
            variable=self._state.use_time_range,
            command=self._on_time_range_toggle,
            font=(FONT_FAMILY, 10),
            bg=self._theme.panel,
            fg=self._theme.text,
            activebackground=self._theme.panel,
            activeforeground=self._theme.text,
            selectcolor=self._theme.panel,
        ).pack(anchor="w")
        self._range_body = RangeControls(self._content, self._theme, self._state, self._on_change)
        self._range_body.pack(fill="x")

    def _build_preview(self) -> None:
        row = tk.Frame(self._content, bg=self._theme.panel)
        row.pack(fill="x", pady=(14, 8))
        tk.Checkbutton(
            row,
            text="低清预览视频",
            variable=self._state.make_preview,
            command=self._on_change,
            font=(FONT_FAMILY, 10),
            bg=self._theme.panel,
            fg=self._theme.text,
            activebackground=self._theme.panel,
            activeforeground=self._theme.text,
            selectcolor=self._theme.panel,
        ).pack(anchor="w")
        muted_label(row, self._theme, "导出后在图片文件夹内生成 MP4，用来快速检查播放节奏", 8).pack(anchor="w")

    def _build_format(self) -> None:
        tk.Label(
            self._content,
            text="图片格式",
            font=(FONT_FAMILY, 10),
            bg=self._theme.panel,
            fg=self._theme.text_muted,
        ).pack(anchor="w", pady=(16, 8))
        self._format_combo = ttk.Combobox(
            self._content,
            textvariable=self._state.image_format,
            values=("png", "jpg"),
            state="readonly",
            font=(FONT_FAMILY, 10),
            width=8,
        )
        self._format_combo.pack(anchor="w")
        self._format_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_change())

    def _build_output_dir(self) -> None:
        tk.Label(
            self._content,
            text="导出目录",
            font=(FONT_FAMILY, 10),
            bg=self._theme.panel,
            fg=self._theme.text_muted,
        ).pack(anchor="w", pady=(18, 8))
        tk.Radiobutton(
            self._content,
            text="跟随视频所在文件夹",
            value="source",
            variable=self._state.output_mode,
            command=self._on_change,
            font=(FONT_FAMILY, 9),
            bg=self._theme.panel,
            fg=self._theme.text,
            activebackground=self._theme.panel,
            activeforeground=self._theme.text,
            selectcolor=self._theme.panel,
        ).pack(anchor="w")
        tk.Radiobutton(
            self._content,
            text="指定导出文件夹",
            value="custom",
            variable=self._state.output_mode,
            command=self._on_change,
            font=(FONT_FAMILY, 9),
            bg=self._theme.panel,
            fg=self._theme.text,
            activebackground=self._theme.panel,
            activeforeground=self._theme.text,
            selectcolor=self._theme.panel,
        ).pack(anchor="w", pady=(2, 6))
        path_row = tk.Frame(self._content, bg=self._theme.panel)
        path_row.pack(fill="x")
        self._output_entry = input_entry(path_row, self._theme, self._state.output_dir, 30)
        self._output_entry.pack(side="left", fill="x", expand=True)
        button(path_row, self._theme, "浏览", self._choose_output_dir).pack(side="right", padx=(8, 0))

    def _divider(self) -> None:
        tk.Frame(self._content, bg=self._theme.border, height=1).pack(fill="x", pady=(18, 8))

    def render(self, items: Sequence[VideoItem], selected_index: int) -> None:
        self._items = items
        self._selected_index = selected_index
        self._target_entry.configure(state="normal" if self._state.use_target_fps.get() else "disabled")
        self._output_entry.configure(state="normal" if self._state.output_mode.get() == "custom" else "disabled")
        if len(items) > 1 and self._state.use_target_fps.get():
            self._per_video_frame.pack(fill="x", pady=(4, 0), after=self._target_frame)
        else:
            self._per_video_frame.pack_forget()
        self._per_video_fps.render(items, bool(self._state.use_per_video_fps.get()))
        self._range_body.render(items)

    def _choose_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="选择导出文件夹")
        if not folder:
            return
        self._state.output_mode.set("custom")
        self._state.output_dir.set(folder)
        self._on_change()
