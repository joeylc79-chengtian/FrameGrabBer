from __future__ import annotations

import unittest
from datetime import datetime

from export_plan import ExportOptions, ExportPlanError, VideoInfo, build_export_plan, parse_timecode


class ExportPlanTest(unittest.TestCase):
    def test_target_fps_plan_when_source_is_30fps(self) -> None:
        video = VideoInfo(width=1920, height=1080, fps=30.0, total_frames=300, duration=10.0)
        options = ExportOptions("每帧", 5, True, 24.0, False, 0.0, 0.0)

        plan = build_export_plan(video, options, datetime(2026, 6, 14, 15, 30))

        self.assertEqual(plan.output_count, 240)
        self.assertEqual(plan.output_label, "24fps")
        self.assertEqual(plan.output_subdir_name, "24fps_20260614_1530_预计240张")
        self.assertEqual(plan.vf_filters, ("fps=24",))

    def test_target_fps_rejects_upsampling_when_target_exceeds_source(self) -> None:
        video = VideoInfo(width=1920, height=1080, fps=30.0, total_frames=300, duration=10.0)
        options = ExportOptions("每帧", 5, True, 60.0, False, 0.0, 0.0)

        with self.assertRaisesRegex(ExportPlanError, "不能高于原视频帧率"):
            build_export_plan(video, options)

    def test_target_fps_is_only_valid_for_every_frame_mode(self) -> None:
        video = VideoInfo(width=1920, height=1080, fps=30.0, total_frames=300, duration=10.0)
        options = ExportOptions("每秒1帧", 5, True, 24.0, False, 0.0, 0.0)

        with self.assertRaisesRegex(ExportPlanError, "只适用于逐帧"):
            build_export_plan(video, options)

    def test_time_range_limits_output_duration_when_enabled(self) -> None:
        video = VideoInfo(width=1920, height=1080, fps=24.0, total_frames=240, duration=10.0)
        options = ExportOptions("每帧", 5, False, 24.0, True, 2.0, 5.0)

        plan = build_export_plan(video, options, datetime(2026, 6, 14, 15, 30))

        self.assertEqual(plan.output_count, 72)
        self.assertEqual(plan.input_args, ("-ss", "2.000", "-t", "3.000"))

    def test_parse_timecode_accepts_seconds_mmss_and_hhmmss(self) -> None:
        self.assertEqual(parse_timecode("5"), 5.0)
        self.assertEqual(parse_timecode("01:05"), 65.0)
        self.assertEqual(parse_timecode("01:02:03.5"), 3723.5)


if __name__ == "__main__":
    unittest.main()
