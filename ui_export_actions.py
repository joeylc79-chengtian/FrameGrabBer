from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from export_plan import ExportPlanError
from export_runner import run_export_jobs
from theme import Theme
from ui_export_controller import build_jobs
from ui_models import ExportSettingsState, VideoItem


class ExportActions:
    def __init__(
        self,
        ffmpeg_exe: str | None,
        items: list[VideoItem],
        settings: ExportSettingsState,
        message_queue: queue.Queue[tuple],
    ) -> None:
        self._ffmpeg_exe = ffmpeg_exe
        self._items = items
        self._settings = settings
        self._queue = message_queue
        self.running = False
        self._cancel_event: threading.Event | None = None

    def start(self, progress: ttk.Progressbar | None, label: tk.Label | None, set_status, theme: Theme) -> bool:
        if self.running:
            return False
        if not self._items:
            messagebox.showwarning("提示", "请先添加视频")
            return False
        if not self._ffmpeg_exe:
            messagebox.showerror("错误", "找不到 FFmpeg")
            return False
        try:
            jobs = build_jobs(self._ffmpeg_exe, self._items, self._settings)
        except ExportPlanError as exc:
            messagebox.showerror("设置错误", str(exc))
            return False
        self.running = True
        expected_total = sum(job.expected_count for job in jobs)
        self._cancel_event = threading.Event()
        if progress:
            if expected_total > 0:
                progress.configure(mode="determinate", maximum=expected_total, value=0)
            else:
                progress.configure(mode="indeterminate", maximum=100, value=0)
                progress.start(15)
        if label:
            label.configure(text=f"预计 {expected_total:,} 张")
        set_status(f"正在导出 {len(jobs)} 个视频...", theme.accent)
        threading.Thread(target=run_export_jobs, args=(jobs, self._queue, self._cancel_event), daemon=True).start()
        return True

    def cancel(self, set_status, theme: Theme) -> bool:
        if not self.running or not self._cancel_event:
            return False
        self._cancel_event.set()
        set_status("正在停止导出并清理未完成文件...", theme.error)
        return True

    def handle_message(
        self,
        msg: tuple,
        progress: ttk.Progressbar | None,
        label: tk.Label | None,
        set_status,
        set_running_ui: Callable[[bool], None],
        theme: Theme,
    ) -> None:
        handle_worker_message(
            msg,
            progress,
            label,
            set_status,
            self._finish,
            set_running_ui,
            theme.accent,
            theme.success,
            theme.error,
        )

    def _finish(self) -> None:
        self.running = False
        self._cancel_event = None


def handle_worker_message(
    msg: tuple,
    progress: ttk.Progressbar | None,
    progress_label: tk.Label | None,
    set_status: Callable[[str, str | None], None],
    finish_running: Callable[[], None],
    set_running_ui: Callable[[bool], None],
    accent: str,
    success: str,
    error: str,
) -> None:
    kind = msg[0]
    if kind == "job":
        _, index, total, name = msg
        set_status(f"正在处理 {index}/{total}: {name}", accent)
        return
    if kind == "preview":
        _, index, total = msg
        if progress_label:
            progress_label.configure(text=f"视频 {index}/{total}: 正在生成低清预览视频")
        return
    if kind == "progress":
        _update_progress(msg, progress, progress_label)
        return
    if kind == "done":
        _, output_dirs, count, total_jobs = msg
        _finish_success(
            output_dirs,
            count,
            total_jobs,
            progress,
            progress_label,
            set_status,
            finish_running,
            set_running_ui,
            success,
        )
        return
    if kind == "cancelled":
        _finish_cancelled(progress, progress_label, set_status, finish_running, set_running_ui, error)
        return
    if kind == "error":
        _, err_text = msg
        _finish_error(err_text, progress, progress_label, set_status, finish_running, set_running_ui, error)


def _update_progress(msg: tuple, progress: ttk.Progressbar | None, progress_label: tk.Label | None) -> None:
    _, frame, _pct, text = msg
    if progress:
        if progress.cget("mode") == "indeterminate":
            progress.configure(mode="determinate", maximum=frame + 100, value=frame)
        else:
            progress["value"] = frame
    if progress_label:
        progress_label.configure(text=text)


def _finish_success(
    output_dirs: list[str],
    count: int,
    total_jobs: int,
    progress: ttk.Progressbar | None,
    progress_label: tk.Label | None,
    set_status: Callable[[str, str | None], None],
    finish_running: Callable[[], None],
    set_running_ui: Callable[[bool], None],
    success: str,
) -> None:
    finish_running()
    set_running_ui(False)
    if progress:
        progress.stop()
        progress.configure(mode="determinate", value=100, maximum=100)
    if progress_label:
        progress_label.configure(text=f"完成：{count:,} 张")
    set_status("导出完成", success)
    output_text = output_dirs[0] if total_jobs == 1 else f"{total_jobs} 个输出文件夹"
    if messagebox.askyesno("完成", f"导出完成！\n共导出 {count:,} 张图片\n输出: {output_text}\n\n是否打开第一个输出文件夹？"):
        os.startfile(output_dirs[0])


def _finish_error(
    err_text: str,
    progress: ttk.Progressbar | None,
    progress_label: tk.Label | None,
    set_status: Callable[[str, str | None], None],
    finish_running: Callable[[], None],
    set_running_ui: Callable[[bool], None],
    error: str,
) -> None:
    finish_running()
    set_running_ui(False)
    if progress:
        progress.stop()
        progress.configure(mode="determinate", value=0, maximum=100)
    if progress_label:
        progress_label.configure(text="")
    set_status("导出失败", error)
    messagebox.showerror("错误", f"导出过程出错：\n{err_text}")


def _finish_cancelled(
    progress: ttk.Progressbar | None,
    progress_label: tk.Label | None,
    set_status: Callable[[str, str | None], None],
    finish_running: Callable[[], None],
    set_running_ui: Callable[[bool], None],
    error: str,
) -> None:
    finish_running()
    set_running_ui(False)
    if progress:
        progress.stop()
        progress.configure(mode="determinate", value=0, maximum=100)
    if progress_label:
        progress_label.configure(text="已停止")
    set_status("已停止导出，未完成文件已清理", error)
