from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence

from theme import FONT_FAMILY, Theme
from ui_batch_controls import PerVideoFpsControls, RangeControls, clamp_fps_text, clamp_step_text
from ui_models import ExportSettingsState, VideoItem
from ui_option_controls import OptionRow
from ui_output_options import OutputOptionsSection
from ui_widgets import ScrollableFrame, entry_last_valid, input_entry, muted_label, panel, remember_entry_value, section_title


class ExportSettingsView(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        state: ExportSettingsState,
        on_value_change: Callable[[], None],
        on_structure_change: Callable[[], None],
        on_target_fps_toggle: Callable[[], None],
        on_time_range_toggle: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=theme.bg)
        self._theme = theme
        self._state = state
        self._on_value_change = on_value_change
        self._on_structure_change = on_structure_change
        self._on_target_fps_toggle = on_target_fps_toggle
        self._on_time_range_toggle = on_time_range_toggle
        self._items: Sequence[VideoItem] = ()
        self._container = panel(self, theme)
        self._container.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        self._title = section_title(self._container, self._theme, "导出设置")
        self._title.pack(anchor="w", padx=22, pady=(18, 4))
        self._scroll = ScrollableFrame(self._container, self._theme)
        self._scroll.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self._content = tk.Frame(self._scroll.content, bg=self._theme.panel)
        self._content.pack(fill="both", expand=True, padx=8, pady=6)
        self._build_interval_mode()
        self._build_target_fps()
        self._build_time_range()
        self._build_preview()
        self._divider()
        self._output_options = OutputOptionsSection(self._content, self._theme, self._state, self._on_value_change)

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
            OptionRow(
                option,
                self._theme,
                text=text,
                variable=self._state.interval,
                value=value,
                command=self._structure_changed,
                kind="radio",
            ).pack(anchor="w")
            if value == "自定义":
                custom = tk.Frame(option, bg=self._theme.panel)
                custom.pack(anchor="w", padx=(24, 0), pady=(2, 0))
                self._custom_step_entry = input_entry(
                    custom,
                    self._theme,
                    self._state.custom_step,
                    5,
                    lambda entry: self._commit_custom_step(entry),
                )
                self._custom_step_entry.pack(side="left")
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
        OptionRow(
            self._target_frame,
            self._theme,
            text="指定帧率导出",
            variable=self._state.use_target_fps,
            command=self._on_target_fps_toggle,
        ).pack(side="left")
        self._target_entry = input_entry(
            self._target_frame,
            self._theme,
            self._state.target_fps,
            8,
            lambda entry: self._commit_target_fps(entry),
        )
        self._target_entry.pack(side="right")
        tk.Label(
            self._target_frame,
            text="fps",
            font=(FONT_FAMILY, 9),
            bg=self._theme.panel,
            fg=self._theme.text_muted,
        ).pack(side="right", padx=(0, 8))

        self._per_video_frame = tk.Frame(self._content, bg=self._theme.panel)
        OptionRow(
            self._per_video_frame,
            self._theme,
            text="不同视频分别设置帧率",
            variable=self._state.use_per_video_fps,
            command=self._structure_changed,
            muted=True,
        ).pack(anchor="w")
        muted_label(self._per_video_frame, self._theme, "批量导出时可让每个视频使用自己的目标帧率", 8).pack(anchor="w")
        self._per_video_fps = PerVideoFpsControls(self._per_video_frame, self._theme, self._on_value_change)
        self._per_video_fps.pack(fill="x", pady=(4, 0))

    def _build_time_range(self) -> None:
        self._range_frame = tk.Frame(self._content, bg=self._theme.panel)
        self._range_frame.pack(fill="x", pady=(16, 6))
        OptionRow(
            self._range_frame,
            self._theme,
            text="只导出视频片段",
            variable=self._state.use_time_range,
            command=self._on_time_range_toggle,
        ).pack(anchor="w")
        self._range_body = RangeControls(self._content, self._theme, self._state, self._on_value_change)
        self._range_body.pack(fill="x")

    def _build_preview(self) -> None:
        row = tk.Frame(self._content, bg=self._theme.panel)
        row.pack(fill="x", pady=(14, 8))
        OptionRow(
            row,
            self._theme,
            text="低清预览视频",
            variable=self._state.make_preview,
            command=self._on_value_change,
        ).pack(anchor="w")
        muted_label(row, self._theme, "导出后在图片文件夹内生成 MP4，用来快速检查播放节奏", 8).pack(anchor="w")

    def _divider(self) -> None:
        tk.Frame(self._content, bg=self._theme.border, height=1).pack(fill="x", pady=(18, 8))

    def render(self, items: Sequence[VideoItem]) -> None:
        self._items = items
        self._target_entry.configure(state="normal" if self._state.use_target_fps.get() else "disabled")
        self._output_options.sync_controls()
        if len(items) > 1 and self._state.use_target_fps.get():
            self._per_video_frame.pack(fill="x", pady=(4, 0), after=self._target_frame)
        else:
            self._per_video_frame.pack_forget()
        self._per_video_fps.render(items, bool(self._state.use_per_video_fps.get()))
        self._range_body.render(items)

    def reset_dynamic_sections(self) -> None:
        self._per_video_fps.reset()
        self._range_body.reset()

    def refresh_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.configure(bg=theme.bg)
        self._container.configure(bg=theme.panel, highlightbackground=theme.border)
        self._content.configure(bg=theme.panel)
        self._scroll.refresh_theme(theme)
        self._per_video_fps.refresh_theme(theme)
        self._range_body.refresh_theme(theme)
        self._output_options.refresh_theme(theme)

    def scroll_position(self) -> float:
        return float(self._scroll.canvas.yview()[0])

    def restore_scroll_position(self, position: float) -> None:
        def restore() -> None:
            self._scroll.canvas.configure(scrollregion=self._scroll.canvas.bbox("all"))
            self._scroll.canvas.yview_moveto(position)

        self.after(80, restore)

    def _structure_changed(self) -> None:
        self._per_video_fps.reset()
        self._range_body.reset()
        self._on_structure_change()

    def _output_mode_changed(self) -> None:
        self._output_options.sync_controls()
        self._on_value_change()

    def _commit_target_fps(self, entry: tk.Entry | None = None) -> str:
        target = entry or self._target_entry
        fallback = entry_last_valid(target, "24")
        self._state.target_fps.set(clamp_fps_text(self._state.target_fps.get(), self._max_target_fps(), fallback))
        remember_entry_value(target)
        self._on_value_change()
        return "break"

    def _commit_custom_step(self, entry: tk.Entry | None = None) -> str:
        target = entry or self._custom_step_entry
        fallback = entry_last_valid(target, "5")
        self._state.custom_step.set(clamp_step_text(self._state.custom_step.get(), fallback))
        remember_entry_value(target)
        self._on_value_change()
        return "break"

    def _max_target_fps(self) -> float:
        if not self._items:
            return 120.0
        return max(0.1, min(item.info.fps for item in self._items))
