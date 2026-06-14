from __future__ import annotations

import unittest
from datetime import datetime

from export_plan import ExportOptions, VideoInfo, build_export_job, build_export_plan


class ExportJobTest(unittest.TestCase):
    def test_build_export_job_when_video_has_its_own_folder(self) -> None:
        video = VideoInfo(width=1920, height=1080, fps=30.0, total_frames=300, duration=10.0)
        plan = build_export_plan(
            video,
            ExportOptions("每帧", 5, True, 24.0, False, 0.0, 0.0),
            datetime(2026, 6, 14, 15, 30),
        )

        job = build_export_job(
            "ffmpeg",
            r"E:\视频\a.mp4",
            video,
            plan,
            "png",
            "a",
            True,
        )

        self.assertEqual(job.output_dir, r"E:\视频\a_24fps_20260614_1530_预计240张")
        self.assertEqual(job.output_pattern, r"E:/视频/a_24fps_20260614_1530_预计240张/a.%05d.png")
        self.assertEqual(job.preview_path, r"E:\视频\a_24fps_20260614_1530_预计240张\低清预览.mp4")
        self.assertIn("-framerate", job.preview_command)
        self.assertIn("24", job.preview_command)

    def test_build_export_job_when_output_root_is_selected(self) -> None:
        video = VideoInfo(width=1920, height=1080, fps=30.0, total_frames=300, duration=10.0)
        plan = build_export_plan(
            video,
            ExportOptions("每帧", 5, True, 24.0, False, 0.0, 0.0),
            datetime(2026, 6, 14, 15, 30),
        )

        job = build_export_job(
            "ffmpeg",
            r"E:\视频\a.mp4",
            video,
            plan,
            "png",
            "a",
            False,
            r"D:\导出\抽帧结果",
        )

        self.assertEqual(job.output_dir, r"D:\导出\抽帧结果\a_24fps_20260614_1530_预计240张")
        self.assertEqual(job.output_pattern, r"D:/导出/抽帧结果/a_24fps_20260614_1530_预计240张/a.%05d.png")


if __name__ == "__main__":
    unittest.main()
