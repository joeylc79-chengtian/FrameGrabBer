from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog

from theme import FONT_FAMILY, Theme
from ui_models import ExportSettingsState
from ui_option_controls import OptionRow
from ui_widgets import SegmentedControl, button, input_entry


class OutputOptionsSection:
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        state: ExportSettingsState,
        on_value_change: Callable[[], None],
    ) -> None:
        self._master = master
        self._theme = theme
        self._state = state
        self._on_value_change = on_value_change
        self._output_button: tk.Button | None = None
        self._format_control: SegmentedControl | None = None
        self._build_format()
        self._build_output_dir()

    def sync_controls(self) -> None:
        output_enabled = self._state.output_mode.get() == "custom"
        self._output_entry.configure(state="normal" if output_enabled else "disabled")
        if self._output_button:
            self._output_button.configure(state="normal" if output_enabled else "disabled")

    def _build_format(self) -> None:
        tk.Label(
            self._master,
            text="图片格式",
            font=(FONT_FAMILY, 10),
            bg=self._theme.panel,
            fg=self._theme.text_muted,
        ).pack(anchor="w", pady=(16, 8))
        self._format_control = SegmentedControl(
            self._master,
            self._theme,
            variable=self._state.image_format,
            values=("png", "jpg"),
            command=self._on_value_change,
        )
        self._format_control.pack(anchor="w")

    def refresh_theme(self, theme: Theme) -> None:
        self._theme = theme
        if self._format_control:
            self._format_control.refresh(theme)

    def _build_output_dir(self) -> None:
        tk.Label(
            self._master,
            text="导出目录",
            font=(FONT_FAMILY, 10),
            bg=self._theme.panel,
            fg=self._theme.text_muted,
        ).pack(anchor="w", pady=(18, 8))
        OptionRow(
            self._master,
            self._theme,
            text="跟随视频所在文件夹",
            variable=self._state.output_mode,
            value="source",
            command=self._output_mode_changed,
            kind="radio",
            muted=True,
        ).pack(anchor="w")
        OptionRow(
            self._master,
            self._theme,
            text="指定导出文件夹",
            variable=self._state.output_mode,
            value="custom",
            command=self._output_mode_changed,
            kind="radio",
            muted=True,
        ).pack(anchor="w", pady=(2, 6))
        path_row = tk.Frame(self._master, bg=self._theme.panel)
        path_row.pack(fill="x")
        self._output_entry = input_entry(path_row, self._theme, self._state.output_dir, 30, lambda _entry: self._on_value_change())
        self._output_entry.pack(side="left", fill="x", expand=True)
        self._output_button = button(path_row, self._theme, "浏览", self._choose_output_dir)
        self._output_button.pack(side="right", padx=(8, 0))

    def _output_mode_changed(self) -> None:
        self.sync_controls()
        self._on_value_change()

    def _choose_output_dir(self) -> None:
        if self._state.output_mode.get() != "custom":
            return
        folder = filedialog.askdirectory(title="选择导出文件夹")
        if not folder:
            return
        self._state.output_mode.set("custom")
        self._state.output_dir.set(folder)
        self.sync_controls()
        self._on_value_change()
