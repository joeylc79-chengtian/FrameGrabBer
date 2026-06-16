from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time

from export_plan import ExportJob


WorkerMessage = tuple
PROGRESS_INTERVAL_SECONDS = 0.15


class ExportCancelled(RuntimeError):
    pass


def run_export_jobs(
    jobs: list[ExportJob],
    messages: queue.Queue[WorkerMessage],
    cancel_event: threading.Event | None = None,
) -> None:
    cancel_flag = cancel_event or threading.Event()
    work_dirs: list[str] = []
    output_dirs: list[str] = []
    pending_publish: list[tuple[str, str]] = []
    published_dirs: list[str] = []
    try:
        total_actual = 0
        completed_expected = 0
        total_jobs = len(jobs)
        for index, job in enumerate(jobs, start=1):
            if cancel_flag.is_set():
                raise ExportCancelled
            output_dirs.append(job.output_dir)
            messages.put(("job", index, total_jobs, os.path.basename(job.video_path)))
            work_dir = _prepare_work_dir(job.output_dir)
            work_dirs.append(work_dir)
            image_command = _retarget_output_pattern(job.image_command, job.output_pattern, work_dir)
            run_ffmpeg_command(
                image_command,
                job.expected_count,
                completed_expected,
                index,
                total_jobs,
                messages,
                cancel_flag,
            )
            total_actual += count_exported_images(work_dir)
            if job.preview_command:
                if cancel_flag.is_set():
                    raise ExportCancelled
                messages.put(("preview", index, total_jobs))
                preview_command = _retarget_preview_command(job.preview_command, job.output_pattern, work_dir, job.preview_path)
                run_ffmpeg_command(preview_command, 0, completed_expected, index, total_jobs, messages, cancel_flag)
            pending_publish.append((work_dir, job.output_dir))
            completed_expected += job.expected_count
        for work_dir, output_dir in pending_publish:
            _publish_work_dir(work_dir, output_dir)
            work_dirs.remove(work_dir)
            published_dirs.append(output_dir)
        messages.put(("done", output_dirs, total_actual, total_jobs))
    except ExportCancelled:
        _cleanup_paths(work_dirs)
        _cleanup_paths(published_dirs)
        messages.put(("cancelled",))
    except (OSError, RuntimeError) as exc:
        _cleanup_paths(work_dirs)
        _cleanup_paths(published_dirs)
        messages.put(("error", str(exc)))


def run_ffmpeg_command(
    cmd: tuple[str, ...],
    expected_count: int,
    completed_count: int,
    job_index: int,
    total_jobs: int,
    messages: queue.Queue[WorkerMessage],
    cancel_event: threading.Event | None = None,
) -> None:
    cancel_flag = cancel_event or threading.Event()
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    _start_cancel_monitor(proc, cancel_flag)
    last_frame = 0
    last_emit = 0.0
    try:
        if proc.stderr:
            for line in proc.stderr:
                if cancel_flag.is_set():
                    _stop_process(proc)
                    raise ExportCancelled
                match = re.search(r"frame=\s*(\d+)", line)
                if not match:
                    continue
                frame = int(match.group(1))
                if frame <= last_frame or expected_count <= 0:
                    continue
                last_frame = frame
                now = time.monotonic()
                output_frame = min(frame, expected_count)
                if output_frame < expected_count and now - last_emit < PROGRESS_INTERVAL_SECONDS:
                    continue
                last_emit = now
                progress_value = completed_count + output_frame
                pct = min(output_frame * 100 // expected_count, 99)
                messages.put(
                    (
                        "progress",
                        progress_value,
                        pct,
                        f"视频 {job_index}/{total_jobs}: 已导出 {output_frame:,} / {expected_count:,} 张",
                    ),
                )
        if cancel_flag.is_set():
            _stop_process(proc)
            raise ExportCancelled
        proc.wait()
    finally:
        if proc.stdout:
            proc.stdout.close()
        if proc.stderr:
            proc.stderr.close()
    if proc.returncode != 0:
        if cancel_flag.is_set():
            raise ExportCancelled
        raise RuntimeError(f"FFmpeg 退出码 {proc.returncode}，请检查视频文件是否损坏")


def count_exported_images(out_dir: str) -> int:
    return len(
        [
            filename
            for filename in os.listdir(out_dir)
            if os.path.isfile(os.path.join(out_dir, filename))
            and os.path.splitext(filename)[1].lower() in (".png", ".jpg", ".jpeg")
        ],
    )


def _prepare_work_dir(output_dir: str) -> str:
    parent = os.path.dirname(output_dir)
    name = os.path.basename(output_dir)
    work_dir = os.path.join(parent, f".{name}.导出中")
    if os.path.isdir(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


def _publish_work_dir(work_dir: str, output_dir: str) -> None:
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    os.replace(work_dir, output_dir)


def _cleanup_paths(paths: list[str]) -> None:
    for path in paths:
        shutil.rmtree(path, ignore_errors=True)


def _retarget_output_pattern(command: tuple[str, ...], old_pattern: str, work_dir: str) -> tuple[str, ...]:
    new_pattern = os.path.join(work_dir, os.path.basename(old_pattern)).replace("\\", "/")
    return tuple(new_pattern if arg == old_pattern else arg for arg in command)


def _retarget_preview_command(
    command: tuple[str, ...],
    old_pattern: str,
    work_dir: str,
    old_preview_path: str,
) -> tuple[str, ...]:
    new_pattern = os.path.join(work_dir, os.path.basename(old_pattern)).replace("\\", "/")
    new_preview_path = os.path.join(work_dir, os.path.basename(old_preview_path))
    return tuple(
        new_pattern if arg == old_pattern else new_preview_path if arg == old_preview_path else arg
        for arg in command
    )


def _stop_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _start_cancel_monitor(proc: subprocess.Popen[str], cancel_event: threading.Event) -> None:
    def monitor() -> None:
        while proc.poll() is None:
            if cancel_event.wait(0.1):
                _stop_process(proc)
                return

    threading.Thread(target=monitor, daemon=True).start()
