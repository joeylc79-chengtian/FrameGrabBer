from __future__ import annotations

import os
import site
import sys
import tkinter as tk
from types import MethodType

DND_FILES = "DND_Files"


class BaseTk(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.dnd_available = False


def enable_drag_and_drop(window: tk.Tk) -> bool:
    try:
        from tkinterdnd2 import TkinterDnD
    except ImportError:
        return False
    try:
        TkinterDnD.require(window)
    except RuntimeError:
        return False
    window._subst_format_dnd = TkinterDnD.DnDWrapper._subst_format_dnd
    window._subst_format_str_dnd = TkinterDnD.DnDWrapper._subst_format_str_dnd
    for name in (
        "_substitute_dnd",
        "_dnd_bind",
        "dnd_bind",
        "drop_target_register",
        "drop_target_unregister",
    ):
        if not hasattr(window, name):
            setattr(window, name, MethodType(getattr(TkinterDnD.DnDWrapper, name), window))
    window.dnd_available = True
    return True


def resolve_icon_path() -> str | None:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        path = os.path.join(meipass, "app.ico")
        if os.path.isfile(path):
            return path

    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "app.ico")
    if os.path.isfile(path):
        return path
    return None


def apply_window_icon(window: tk.Tk) -> None:
    icon_path = resolve_icon_path()
    if not icon_path:
        return
    try:
        window.iconbitmap(icon_path)
    except tk.TclError:
        pass


def pause_redraw(window: tk.Tk) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.SendMessageW(int(window.winfo_id()), 0x000B, 0, 0)
    except (OSError, tk.TclError, ValueError):
        return


def resume_redraw(window: tk.Tk) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(window.winfo_id())
        ctypes.windll.user32.SendMessageW(hwnd, 0x000B, 1, 0)
        ctypes.windll.user32.RedrawWindow(hwnd, None, None, 0x0001 | 0x0080 | 0x0100)
    except (OSError, tk.TclError, ValueError):
        return


def get_ffmpeg_exe() -> str | None:
    try:
        import imageio_ffmpeg
    except ImportError:
        return None

    try:
        path = imageio_ffmpeg.get_ffmpeg_exe()
    except RuntimeError:
        path = None
    if path and os.path.isfile(path):
        return path

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            found = _find_ffmpeg_under(meipass)
            if found:
                return found

    for site_dir in site.getsitepackages():
        bin_dir = os.path.join(site_dir, "imageio_ffmpeg", "binaries")
        found = _find_ffmpeg_under(bin_dir)
        if found:
            return found
    return None


def _find_ffmpeg_under(folder: str) -> str | None:
    if not os.path.isdir(folder):
        return None
    for root, _dirs, files in os.walk(folder):
        for filename in files:
            if filename.startswith("ffmpeg") and filename.endswith(".exe"):
                return os.path.join(root, filename)
    return None
