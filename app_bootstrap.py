from __future__ import annotations

import os
import site
import sys
import tkinter as tk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND = True
except ImportError:
    DND_FILES = ""
    HAS_DND = False

try:
    import imageio_ffmpeg

    HAS_IMAGEIO_FFMPEG = True
except ImportError:
    HAS_IMAGEIO_FFMPEG = False


if HAS_DND:

    class BaseTk(TkinterDnD.Tk):
        def __init__(self) -> None:
            try:
                super().__init__()
                self.dnd_available = True
            except RuntimeError:
                tk.Tk.__init__(self)
                self.dnd_available = False


else:

    class BaseTk(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.dnd_available = False


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


def get_ffmpeg_exe() -> str | None:
    if not HAS_IMAGEIO_FFMPEG:
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
