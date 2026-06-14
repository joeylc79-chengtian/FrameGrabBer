from __future__ import annotations

import os
import queue
import re
import subprocess
import sys

from export_plan import ExportJob


WorkerMessage = tuple


def run_export_jobs(jobs: list[ExportJob], messages: queue.Queue[WorkerMessage]) -> None:
    try:
        total_actual = 0
        output_dirs: list[str] = []
        total_jobs = len(jobs)
        for index, job in enumerate(jobs, start=1):
            output_dirs.append(job.output_dir)
            messages.put(("job", index, total_jobs, os.path.basename(job.video_path)))
            os.makedirs(job.output_dir, exist_ok=True)
            run_ffmpeg_command(job.image_command, job.total_frames, index, total_jobs, messages)
            total_actual += count_exported_images(job.output_dir)
            if job.preview_command:
                messages.put(("preview", index, total_jobs))
                run_ffmpeg_command(job.preview_command, 0, index, total_jobs, messages)
        messages.put(("done", output_dirs, total_actual, total_jobs))
    except (OSError, RuntimeError) as exc:
        messages.put(("error", str(exc)))


def run_ffmpeg_command(
    cmd: tuple[str, ...],
    total_src: int,
    job_index: int,
    total_jobs: int,
    messages: queue.Queue[WorkerMessage],
) -> None:
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
    last_frame = 0
    if proc.stderr:
        for line in proc.stderr:
            match = re.search(r"frame=\s*(\d+)", line)
            if not match:
                continue
            frame = int(match.group(1))
            if frame <= last_frame:
                continue
            last_frame = frame
            if total_src > 0:
                pct = min(frame * 100 // total_src, 99)
                messages.put(("progress", frame, pct, f"视频 {job_index}/{total_jobs}: 第 {frame:,} / {total_src:,} 帧"))
            else:
                messages.put(("progress", frame, 0, f"视频 {job_index}/{total_jobs}: 已处理 {frame:,} 帧"))
    proc.wait()
    if proc.returncode != 0:
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
