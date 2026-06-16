from __future__ import annotations

import queue
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from export_plan import ExportJob
from export_runner import run_export_jobs


class ExportRunnerTest(unittest.TestCase):
    def test_sparse_export_progress_uses_expected_image_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            messages: queue.Queue[tuple] = queue.Queue()
            command = (
                sys.executable,
                "-c",
                "import sys; "
                "[sys.stderr.write(f'frame= {i}\\n') or sys.stderr.flush() for i in range(1, 4)]",
            )
            job = ExportJob(
                video_path=str(Path(temp_dir) / "demo.mp4"),
                output_dir=str(Path(temp_dir) / "out"),
                output_pattern=str(Path(temp_dir) / "out" / "demo.%05d.png"),
                image_command=command,
                preview_command=(),
                preview_path=str(Path(temp_dir) / "out" / "preview.mp4"),
                total_frames=300,
                expected_count=3,
            )

            run_export_jobs([job], messages)

            progress_messages = [msg for msg in list(messages.queue) if msg[0] == "progress"]
            self.assertTrue(progress_messages)
            self.assertEqual(progress_messages[-1][1], 3)
            self.assertEqual(progress_messages[-1][2], 99)
            self.assertIn("已导出 3 / 3 张", progress_messages[-1][3])

    def test_cancelled_export_removes_unfinished_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            messages: queue.Queue[tuple] = queue.Queue()
            cancel_event = threading.Event()
            output_dir = Path(temp_dir) / "demo_output"
            command = (
                sys.executable,
                "-c",
                "import sys, time\n"
                "for i in range(1, 20):\n"
                "    sys.stderr.write(f'frame= {i}\\n')\n"
                "    sys.stderr.flush()\n"
                "    time.sleep(0.2)\n",
            )
            job = ExportJob(
                video_path=str(Path(temp_dir) / "demo.mp4"),
                output_dir=str(output_dir),
                output_pattern=str(output_dir / "demo.%05d.png"),
                image_command=command,
                preview_command=(),
                preview_path=str(output_dir / "preview.mp4"),
                total_frames=2000,
                expected_count=20,
            )
            worker = threading.Thread(target=run_export_jobs, args=([job], messages, cancel_event))

            worker.start()
            time.sleep(0.4)
            cancel_event.set()
            worker.join(timeout=5)

            self.assertFalse(worker.is_alive())
            self.assertFalse(output_dir.exists())
            self.assertFalse((Path(temp_dir) / ".demo_output.导出中").exists())
            self.assertTrue(any(msg[0] == "cancelled" for msg in list(messages.queue)))


if __name__ == "__main__":
    unittest.main()
