from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from datetime import datetime


class ExportPlanError(ValueError):
    pass


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float


@dataclass(frozen=True)
class ExportOptions:
    interval: str
    custom_step: int
    use_target_fps: bool
    target_fps: float
    use_time_range: bool
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class ExportPlan:
    output_count: int
    output_label: str
    output_subdir_name: str
    vf_filters: tuple[str, ...]
    input_args: tuple[str, ...]


def parse_timecode(value: str) -> float:
    text = value.strip()
    if not text:
        return 0.0
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    match = re.fullmatch(r"(\d+):([0-5]?\d)(?::([0-5]?\d(?:\.\d+)?))?", text)
    if not match:
        raise ExportPlanError("时间格式请使用秒数、MM:SS 或 HH:MM:SS")
    first = float(match.group(1))
    second = float(match.group(2))
    third_raw = match.group(3)
    if third_raw is None:
        return (first * 60.0) + second
    return (first * 3600.0) + (second * 60.0) + float(third_raw)


def build_export_plan(video: VideoInfo, options: ExportOptions, now: datetime | None = None) -> ExportPlan:
    current_time = now or datetime.now()
    if options.use_target_fps and options.interval != "每帧":
        raise ExportPlanError("指定帧率导出只适用于逐帧模式")
    start = options.start_seconds if options.use_time_range else 0.0
    end = options.end_seconds if options.use_time_range else video.duration
    duration = _checked_duration(start, end, video.duration)
    target_fps = _checked_target_fps(video.fps, options.target_fps, options.use_target_fps)
    vf_filters = _build_filters(options, target_fps)
    input_args = _build_input_args(options.use_time_range, start, duration)
    count = _estimate_output_count(video, options, duration, target_fps)
    label = _label_for(options, target_fps)
    stamp = current_time.strftime("%Y%m%d_%H%M")
    return ExportPlan(
        output_count=count,
        output_label=label,
        output_subdir_name="%s_%s_预计%d张" % (label, stamp, count),
        vf_filters=tuple(vf_filters),
        input_args=tuple(input_args),
    )


def _checked_duration(start: float, end: float, source_duration: float) -> float:
    if source_duration <= 0:
        raise ExportPlanError("无法读取视频时长")
    if start < 0:
        raise ExportPlanError("开始时间不能小于 0")
    if end <= start:
        raise ExportPlanError("结束时间必须大于开始时间")
    if start >= source_duration:
        raise ExportPlanError("开始时间不能超过视频时长")
    return min(end, source_duration) - start


def _checked_target_fps(source_fps: float, target_fps: float, enabled: bool) -> float:
    if not enabled:
        return source_fps
    if target_fps <= 0:
        raise ExportPlanError("目标帧率必须大于 0")
    if source_fps > 0 and target_fps > source_fps + 0.001:
        raise ExportPlanError("目标帧率不能高于原视频帧率 %.2f fps" % source_fps)
    return target_fps


def _build_filters(options: ExportOptions, target_fps: float) -> list[str]:
    filters: list[str] = []
    if options.use_target_fps:
        filters.append("fps=%.6g" % target_fps)
    elif options.interval == "每秒1帧":
        filters.append("fps=1")
    elif options.interval == "自定义":
        step = max(1, options.custom_step)
        filters.append("select='not(mod(n,%d))'" % step)
    return filters


def _build_input_args(use_time_range: bool, start: float, duration: float) -> list[str]:
    if not use_time_range:
        return []
    return ["-ss", "%.3f" % start, "-t", "%.3f" % duration]


def _estimate_output_count(video: VideoInfo, options: ExportOptions, duration: float, target_fps: float) -> int:
    if options.use_target_fps:
        return max(1, int(math.ceil(duration * target_fps)))
    if options.interval == "每秒1帧":
        return max(1, int(math.ceil(duration)))
    if options.interval == "自定义":
        frames = max(1, int(math.ceil(duration * video.fps)))
        return max(1, int(math.ceil(frames / max(1, options.custom_step))))
    return max(1, int(math.ceil(duration * video.fps)))


def _label_for(options: ExportOptions, target_fps: float) -> str:
    if options.use_target_fps:
        return "%sfps" % _format_number(target_fps)
    if options.interval == "每秒1帧":
        return "1fps"
    if options.interval == "自定义":
        return "每%d帧抽1帧" % max(1, options.custom_step)
    return "原始帧率"


def _format_number(value: float) -> str:
    if abs(value - round(value)) < 0.001:
        return str(int(round(value)))
    return ("%.3f" % value).rstrip("0").rstrip(".")


@dataclass(frozen=True)
class ExportJob:
    video_path: str
    output_dir: str
    output_pattern: str
    image_command: tuple[str, ...]
    preview_command: tuple[str, ...]
    preview_path: str
    total_frames: int
    expected_count: int


def build_export_job(
    ffmpeg_exe: str,
    video_path: str,
    video_info: VideoInfo,
    plan: ExportPlan,
    image_format: str,
    prefix: str,
    include_preview: bool,
    output_root: str | None = None,
) -> ExportJob:
    src_dir = os.path.dirname(video_path)
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    base_dir = output_root if output_root else src_dir
    output_dir = os.path.join(base_dir, f"{video_name}_{plan.output_subdir_name}")
    file_prefix = prefix.strip() or video_name
    output_pattern = os.path.join(output_dir, f"{file_prefix}.%05d.{image_format}").replace("\\", "/")
    image_command = _build_image_command(ffmpeg_exe, video_path, plan, image_format, output_pattern)
    preview_path = os.path.join(output_dir, "低清预览.mp4")
    preview_command = _build_preview_command(ffmpeg_exe, output_pattern, preview_path, plan.output_label, include_preview)
    return ExportJob(
        video_path=video_path,
        output_dir=output_dir,
        output_pattern=output_pattern,
        image_command=tuple(image_command),
        preview_command=tuple(preview_command),
        preview_path=preview_path,
        total_frames=video_info.total_frames,
        expected_count=plan.output_count,
    )


def _build_image_command(
    ffmpeg_exe: str,
    video_path: str,
    plan: ExportPlan,
    image_format: str,
    output_pattern: str,
) -> list[str]:
    command = [ffmpeg_exe, "-y", "-nostdin"]
    command += list(plan.input_args)
    command += ["-i", video_path]
    command += ["-an"]
    if plan.vf_filters:
        filters = ",".join(plan.vf_filters)
        command += ["-vf", filters]
        if "select=" in filters:
            command += ["-vsync", "vfr"]
    if image_format == "jpg":
        command += ["-q:v", "1"]
    command.append(output_pattern)
    return command


def _build_preview_command(
    ffmpeg_exe: str,
    output_pattern: str,
    preview_path: str,
    output_label: str,
    include_preview: bool,
) -> list[str]:
    if not include_preview:
        return []
    frame_rate = _preview_frame_rate(output_label)
    return [
        ffmpeg_exe,
        "-y",
        "-nostdin",
        "-framerate",
        frame_rate,
        "-i",
        output_pattern,
        "-vf",
        "scale='min(1280,iw)':-2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "28",
        preview_path,
    ]


def _preview_frame_rate(output_label: str) -> str:
    if output_label.endswith("fps"):
        return output_label[:-3]
    return "24"
