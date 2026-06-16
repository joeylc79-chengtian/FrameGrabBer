from __future__ import annotations

import queue
import tkinter as tk

from background_media import apply_ffmpeg_ready, apply_thumbnail_ready, start_ffmpeg_probe


class AppWorkerMixin:
    def _start_ffmpeg_probe(self) -> None:
        self._ffmpeg_after_id = None
        self._set_status("正在准备 FFmpeg...", self._theme.text_muted)
        start_ffmpeg_probe(self._queue)

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                self._handle_worker_message(msg)
        except queue.Empty:
            pass
        self._poll_after_id = self.after(200, self._poll_queue)

    def _handle_worker_message(self, msg: tuple) -> None:
        if msg and msg[0] == "ffmpeg":
            apply_ffmpeg_ready(self, msg)
            return
        if msg and msg[0] == "thumbnail":
            apply_thumbnail_ready(self, msg)
            return
        self._export_actions.handle_message(
            msg,
            self._progress,
            self._progress_label,
            self._set_status,
            self._action_bar.set_running if self._action_bar else lambda _running: None,
            self._theme,
        )

    def _start_export(self) -> None:
        self._export_actions._ffmpeg_exe = self._ffmpeg_exe
        if self._export_actions.running:
            self._export_actions.cancel(self._set_status, self._theme)
            return
        if self._export_actions.start(self._progress, self._progress_label, self._set_status, self._theme):
            if self._action_bar:
                self._action_bar.set_running(True)

    def _set_status(self, text: str, color: str | None = None) -> None:
        if not self._status_label:
            return
        self._status_label.configure(text=text, fg=color or self._theme.text_subtle)

    def destroy(self) -> None:
        if self._poll_after_id:
            try:
                self.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None
        if self._settings_after_id:
            try:
                self.after_cancel(self._settings_after_id)
            except tk.TclError:
                pass
            self._settings_after_id = None
        for attr in ("_drop_after_id", "_ffmpeg_after_id"):
            after_id = getattr(self, attr, None)
            if not after_id:
                continue
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
            setattr(self, attr, None)
        super().destroy()
