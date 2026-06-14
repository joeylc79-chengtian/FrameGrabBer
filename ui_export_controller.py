from __future__ import annotations

import os

from export_plan import ExportJob, ExportOptions, ExportPlanError, VideoInfo, build_export_job, build_export_plan, parse_timecode
from ui_models import ExportSettingsState, VideoItem


def build_estimate_text(items: list[VideoItem], settings: ExportSettingsState) -> str:
    if not items:
        return "导入视频后会显示预计输出张数"
    try:
        plans = [build_export_plan(video_info_from_item(item), options_for_item(item, items, settings)) for item in items]
    except ExportPlanError as exc:
        return f"设置提示：{exc}"
    count = sum(plan.output_count for plan in plans)
    if len(plans) == 1:
        return f"预计输出约 {count:,} 张图片（{plans[0].output_label}）"
    return f"预计输出 {len(plans)} 个视频，共约 {count:,} 张图片"


def build_jobs(ffmpeg_exe: str, items: list[VideoItem], settings: ExportSettingsState) -> list[ExportJob]:
    output_root = selected_output_root(settings)
    jobs: list[ExportJob] = []
    for item in items:
        video_info = video_info_from_item(item)
        try:
            plan = build_export_plan(video_info, options_for_item(item, items, settings))
        except ExportPlanError as exc:
            if settings.use_target_fps.get() and not settings.use_per_video_fps.get() and len(items) > 1:
                message = f"{item.info.name}: {exc}。可以降低统一帧率，或开启“不同视频分别设置帧率”。"
                raise ExportPlanError(message) from exc
            raise
        video_name = os.path.splitext(os.path.basename(item.info.path))[0]
        jobs.append(
            build_export_job(
                ffmpeg_exe,
                item.info.path,
                video_info,
                plan,
                settings.image_format.get(),
                video_name,
                bool(settings.make_preview.get()),
                output_root,
            ),
        )
    return jobs


def selected_output_root(settings: ExportSettingsState) -> str | None:
    if settings.output_mode.get() != "custom":
        return None
    folder = settings.output_dir.get().strip()
    if not folder:
        raise ExportPlanError("请选择指定导出文件夹")
    return folder


def options_for_item(item: VideoItem, items: list[VideoItem], settings: ExportSettingsState) -> ExportOptions:
    custom_step = _parse_positive_int(settings.custom_step.get(), "每几帧抽一帧必须是整数")
    target_fps = _parse_positive_float(settings.target_fps.get(), "指定帧率必须是数字")
    if settings.use_target_fps.get() and settings.use_per_video_fps.get() and len(items) > 1:
        target_fps = _parse_positive_float(item.target_fps.get(), f"{item.info.name} 的指定帧率必须是数字")
    use_range = bool(item.use_range.get()) if len(items) > 1 else bool(settings.use_time_range.get())
    start_seconds = parse_timecode(item.start_text.get()) if use_range else 0.0
    end_text = item.end_text.get().strip()
    end_seconds = parse_timecode(end_text) if use_range and end_text else float(item.info.duration)
    return ExportOptions(
        interval=settings.interval.get(),
        custom_step=custom_step,
        use_target_fps=bool(settings.use_target_fps.get()),
        target_fps=target_fps,
        use_time_range=use_range,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )


def video_info_from_item(item: VideoItem) -> VideoInfo:
    return VideoInfo(
        width=int(item.info.width),
        height=int(item.info.height),
        fps=float(item.info.fps),
        total_frames=int(item.info.total_frames),
        duration=float(item.info.duration),
    )


def _parse_positive_int(value: str, error_message: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ExportPlanError(error_message) from exc
    return max(1, parsed)


def _parse_positive_float(value: str, error_message: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ExportPlanError(error_message) from exc
    if parsed <= 0:
        raise ExportPlanError(error_message)
    return parsed
