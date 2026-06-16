from __future__ import annotations

import unittest
from unittest.mock import patch

from ui_app import App
from video_queue_controller import create_video_item
from video_info import ParsedVideoInfo


class UiRefreshTest(unittest.TestCase):
    def test_delayed_startup_callbacks_enable_drag_drop(self) -> None:
        app = App()
        try:
            app._register_drop()
            self.assertTrue(getattr(app, "dnd_available", False))
        finally:
            app.destroy()

    def test_theme_change_does_not_rebuild_shell(self) -> None:
        app = App()
        try:
            with patch.object(app, "_build_shell", side_effect=AssertionError("rebuilt shell")):
                app._theme_mode.set("亮色")
                app._change_theme()
                app._theme_mode.set("暗色")
                app._change_theme()
        finally:
            app.destroy()

    def test_output_mode_change_keeps_scroll_position(self) -> None:
        app = App()
        try:
            app._settings_view._scroll.canvas.yview_moveto(0.5)
            before = app._settings_view.scroll_position()
            app._settings.output_mode.set("custom")
            app._settings_view._output_mode_changed()
            after = app._settings_view.scroll_position()
            self.assertEqual(before, after)
        finally:
            app.destroy()

    def test_format_and_preview_changes_do_not_render_settings(self) -> None:
        app = App()
        try:
            with patch.object(app._settings_view, "render", side_effect=AssertionError("rendered")):
                app._settings.make_preview.set(True)
                app._settings_view._on_value_change()
                app._settings.image_format.set("jpg")
                app._settings_view._on_value_change()
        finally:
            app.destroy()

    def test_image_format_segment_refreshes_immediately(self) -> None:
        app = App()
        try:
            control = app._settings_view._output_options._format_control
            control._select("jpg")
            jpg_button = control._buttons[1]
            self.assertEqual(app._settings.image_format.get(), "jpg")
            self.assertEqual(jpg_button.cget("bg"), app._theme.accent)
        finally:
            app.destroy()

    def test_numeric_entries_restore_previous_valid_value(self) -> None:
        app = App()
        try:
            app._settings.target_fps.set("22")
            app._settings_view._commit_target_fps()
            app._settings.target_fps.set("0")
            app._settings_view._commit_target_fps()
            self.assertEqual(app._settings.target_fps.get(), "22")

            app._settings.custom_step.set("4.6")
            app._settings_view._commit_custom_step()
            self.assertEqual(app._settings.custom_step.get(), "5")
            app._settings.custom_step.set("0")
            app._settings_view._commit_custom_step()
            self.assertEqual(app._settings.custom_step.get(), "5")
        finally:
            app.destroy()

    def test_time_slider_change_does_not_render_settings(self) -> None:
        app = App()
        try:
            info = ParsedVideoInfo("demo.mp4", "demo.mp4", 1920, 1080, 24.0, 240, 10.0)
            item = create_video_item(app, info, "24", app._sync_item_from_text, app._schedule_estimate_refresh)
            app._items.append(item)
            app._settings.use_time_range.set(True)
            app._refresh_settings()
            with patch.object(app._settings_view, "render", side_effect=AssertionError("rendered")):
                item.start_seconds.set(2.0)
                app._settings_view._range_body._sync_item_from_slider(item)
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
