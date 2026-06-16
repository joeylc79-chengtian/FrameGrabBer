from __future__ import annotations

import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app_bootstrap import DND_FILES, BaseTk, apply_window_icon, enable_drag_and_drop, pause_redraw, resume_redraw
from background_media import start_thumbnail_jobs
from ui_app_workers import AppWorkerMixin
from theme import Theme, ThemeMode, configure_ttk_styles, resolve_theme
from ui_export_actions import ExportActions
from ui_export_controller import build_estimate_text
from ui_export_settings import ExportSettingsView
from ui_models import ExportSettingsState, VideoItem
from ui_shell import AppFooter, AppHeader, ExportActionBar
from ui_theme_apply import apply_theme_tree
from ui_video_queue import VideoQueueView
from video_queue_controller import add_video_paths, extract_video_paths, sync_item_from_text


MAX_VIDEO_COUNT = 20


class App(AppWorkerMixin, BaseTk):
    def __init__(self) -> None:
        super().__init__()
        self.withdraw()
        self.title("视频逐帧抽图工具 V0.9")
        self.geometry("1180x720")
        self.minsize(980, 640)
        self.resizable(True, True)

        apply_window_icon(self)
        self._theme_mode = tk.StringVar(self, value=ThemeMode.SYSTEM.value)
        self._theme = resolve_theme(ThemeMode.SYSTEM)
        self._settings = ExportSettingsState(self)
        self._ffmpeg_exe: str | None = None
        self._ffmpeg_ready = False
        self._items: list[VideoItem] = []
        self._queue: queue.Queue[tuple] = queue.Queue()
        self._export_actions = ExportActions(self._ffmpeg_exe, self._items, self._settings, self._queue)
        self._main_frame: tk.Frame | None = None
        self._header: AppHeader | None = None
        self._action_bar: ExportActionBar | None = None
        self._footer: AppFooter | None = None
        self._video_queue_view: VideoQueueView | None = None
        self._settings_view: ExportSettingsView | None = None
        self._progress: ttk.Progressbar | None = None
        self._progress_label: tk.Label | None = None
        self._status_label: tk.Label | None = None
        self._poll_after_id: str | None = None
        self._settings_after_id: str | None = None
        self._drop_after_id: str | None = None
        self._ffmpeg_after_id: str | None = None

        self._build_shell()
        self._poll_queue()
        self._drop_after_id = self.after(150, self._register_drop)
        self._ffmpeg_after_id = self.after(220, self._start_ffmpeg_probe)
        self.bind_all("<Button-1>", self._clear_entry_focus, add="+")
        self.after_idle(self._show_ready_window)

    def _show_ready_window(self) -> None:
        self.update_idletasks()
        self.deiconify()

    def _build_shell(self) -> None:
        self.configure(bg=self._theme.bg)
        configure_ttk_styles(self, self._theme)
        if self._main_frame:
            self._main_frame.destroy()
        self._main_frame = tk.Frame(self, bg=self._theme.bg)
        self._main_frame.pack(fill="both", expand=True, padx=18, pady=14)
        self._header = AppHeader(self._main_frame, self._theme, self._theme_mode, self._change_theme)
        body = tk.Frame(self._main_frame, bg=self._theme.bg)
        body.pack(fill="both", expand=True, pady=(14, 14))
        body.grid_columnconfigure(0, weight=4, uniform="body")
        body.grid_columnconfigure(1, weight=7, uniform="body")
        body.grid_rowconfigure(0, weight=1)
        self._video_queue_view = VideoQueueView(
            body,
            self._theme,
            self._select_videos,
            self._clear_videos,
            self._remove_video_item,
        )
        self._video_queue_view.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._settings_view = ExportSettingsView(
            body,
            self._theme,
            self._settings,
            self._on_settings_change,
            self._on_settings_structure_change,
            self._on_target_fps_toggle,
            self._on_time_range_toggle,
        )
        self._settings_view.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self._action_bar = ExportActionBar(self._main_frame, self._theme, self._start_export)
        self._footer = AppFooter(self._main_frame, self._theme)
        self._progress = self._footer.progress
        self._progress_label = self._footer.progress_label
        self._status_label = self._footer.status_label
        self._render()

    def _register_drop(self) -> None:
        self._drop_after_id = None
        if not enable_drag_and_drop(self):
            return
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_drop)

    def _clear_entry_focus(self, event: tk.Event) -> None:
        widget = getattr(event, "widget", None)
        if isinstance(widget, tk.Entry):
            return
        focused = self.focus_get()
        if isinstance(focused, tk.Entry):
            self.focus_set()

    def _select_videos(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择视频文件（可多选）",
            filetypes=[
                ("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm *.m4v"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self._add_video_paths(list(paths))

    def _on_drop(self, event: tk.Event) -> None:
        raw_data = getattr(event, "data", "")
        video_paths = extract_video_paths(self, raw_data)
        if video_paths:
            self._add_video_paths(video_paths)
            return
        messagebox.showinfo("提示", "请拖入视频文件（MP4 / MOV / MKV / AVI 等）")

    def _add_video_paths(self, paths: list[str]) -> None:
        if not self._ffmpeg_ready:
            messagebox.showinfo("提示", "FFmpeg 还在准备中，请稍等一下再导入视频")
            return
        if not self._ffmpeg_exe:
            messagebox.showerror("错误", "找不到 FFmpeg，无法读取视频信息")
            return
        result = add_video_paths(
            self,
            self._items,
            paths,
            self._ffmpeg_exe,
            MAX_VIDEO_COUNT,
            self._settings.target_fps.get(),
            self._sync_item_from_text,
            self._schedule_settings_refresh,
        )
        if self._items:
            self._refresh_queue()
        if result.reached_limit:
            messagebox.showinfo("提示", f"最多一次导入 {MAX_VIDEO_COUNT} 个视频")
        if result.added:
            self._set_status(f"已添加 {result.added} 个视频", self._theme.success)
            start_thumbnail_jobs(self._ffmpeg_exe, self._items, self._queue)
        elif result.skipped:
            self._set_status("没有添加新视频，可能是重复文件或无法读取", self._theme.error)
        self._render()

    def _sync_item_from_text(self, item: VideoItem) -> None:
        if sync_item_from_text(item):
            self._schedule_settings_refresh()

    def _remove_video_item(self, index: int) -> None:
        if index < 0 or index >= len(self._items):
            return
        removed = self._items.pop(index)
        self._set_status(f"已移除 {removed.info.name}", self._theme.text_muted)
        self._render()

    def _clear_videos(self) -> None:
        if not self._items:
            return
        self._items.clear()
        self._set_status("已清空视频列表", self._theme.text_muted)
        self._render()

    def _on_settings_change(self) -> None:
        self._schedule_estimate_refresh()

    def _on_settings_structure_change(self) -> None:
        if self._settings.interval.get() != "每帧" and self._settings.use_target_fps.get():
            self._settings.use_target_fps.set(False)
            self._settings.use_per_video_fps.set(False)
        if self._settings_view:
            self._settings_view.reset_dynamic_sections()
        self._refresh_settings()

    def _on_target_fps_toggle(self) -> None:
        if self._settings.use_target_fps.get() and self._settings.interval.get() != "每帧":
            self._settings.use_target_fps.set(False)
            self._settings.use_per_video_fps.set(False)
            messagebox.showinfo("提示", "请先选择“逐帧”模式，指定帧率导出只适用于逐帧导出。")
        if not self._settings.use_target_fps.get():
            self._settings.use_per_video_fps.set(False)
            if not self._settings.target_fps.get().strip():
                self._settings.target_fps.set("24")
        if self._settings_view:
            self._settings_view.reset_dynamic_sections()
        self._refresh_settings()

    def _on_time_range_toggle(self) -> None:
        enabled = bool(self._settings.use_time_range.get())
        for item in self._items:
            item.use_range.set(enabled)
        if self._settings_view:
            self._settings_view.reset_dynamic_sections()
        self._refresh_settings()

    def _change_theme(self) -> None:
        try:
            mode = ThemeMode(self._theme_mode.get())
        except ValueError:
            mode = ThemeMode.SYSTEM
        old_theme = self._theme
        self._theme = resolve_theme(mode)
        self._apply_theme(old_theme)

    def _apply_theme(self, old_theme: Theme) -> None:
        pause_redraw(self)
        try:
            self.configure(bg=self._theme.bg)
            apply_theme_tree(self, old_theme, self._theme)
            if self._header:
                self._header.theme_control.refresh(self._theme)
            if self._video_queue_view:
                self._video_queue_view.refresh_theme(self._theme)
            if self._settings_view:
                self._settings_view._theme = self._theme
                self._settings_view.refresh_theme(self._theme)
            self._refresh_estimate()
        finally:
            resume_redraw(self)

    def _render(self) -> None:
        self._refresh_queue()
        self._refresh_settings()
        if self._header:
            self._header.theme_control.refresh(self._theme)

    def _refresh_queue(self) -> None:
        if self._video_queue_view:
            self._video_queue_view.render(self._items)

    def _refresh_settings(self) -> None:
        self._settings_after_id = None
        estimate = build_estimate_text(self._items, self._settings)
        if self._settings_view:
            self._settings_view.render(self._items)
        if self._action_bar:
            self._action_bar.set_estimate(estimate)

    def _schedule_estimate_refresh(self) -> None:
        if self._settings_after_id:
            try:
                self.after_cancel(self._settings_after_id)
            except tk.TclError:
                pass
        self._settings_after_id = self.after(120, self._refresh_estimate)

    def _refresh_estimate(self) -> None:
        self._settings_after_id = None
        if self._action_bar:
            self._action_bar.set_estimate(build_estimate_text(self._items, self._settings))

    def _schedule_settings_refresh(self) -> None:
        if self._settings_after_id:
            try:
                self.after_cancel(self._settings_after_id)
            except tk.TclError:
                pass
        self._settings_after_id = self.after(80, self._refresh_settings)
