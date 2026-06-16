from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never


class ThemeMode(StrEnum):
    SYSTEM = "跟随系统"
    LIGHT = "亮色"
    DARK = "暗色"


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    bg: str
    panel: str
    panel_alt: str
    input_bg: str
    border: str
    border_active: str
    button_bg: str
    button_hover: str
    button_pressed: str
    text: str
    text_muted: str
    text_subtle: str
    accent: str
    accent_hover: str
    accent_soft: str
    success: str
    error: str
    disabled: str
    button_text: str


DARK_THEME = Theme(
    name="dark",
    bg="#0f141b",
    panel="#151b24",
    panel_alt="#1a212b",
    input_bg="#1d2530",
    border="#2c3642",
    border_active="#3a8dff",
    button_bg="#1d2530",
    button_hover="#263141",
    button_pressed="#303b4c",
    text="#e8edf4",
    text_muted="#a8b2c0",
    text_subtle="#7e8998",
    accent="#3a8dff",
    accent_hover="#2876df",
    accent_soft="#17365f",
    success="#36c275",
    error="#ff5d5d",
    disabled="#4b5563",
    button_text="#ffffff",
)

LIGHT_THEME = Theme(
    name="light",
    bg="#f5f7fb",
    panel="#ffffff",
    panel_alt="#f2f5f9",
    input_bg="#ffffff",
    border="#d9e0ea",
    border_active="#246bfe",
    button_bg="#ffffff",
    button_hover="#eef2f7",
    button_pressed="#e2e8f0",
    text="#18202b",
    text_muted="#526071",
    text_subtle="#8993a1",
    accent="#246bfe",
    accent_hover="#1d58d4",
    accent_soft="#e8f0ff",
    success="#168a4a",
    error="#d63939",
    disabled="#cbd5e1",
    button_text="#ffffff",
)

FONT_FAMILY = "微软雅黑"


def resolve_theme(mode: ThemeMode) -> Theme:
    match mode:
        case ThemeMode.SYSTEM:
            return LIGHT_THEME if _windows_apps_use_light_theme() else DARK_THEME
        case ThemeMode.LIGHT:
            return LIGHT_THEME
        case ThemeMode.DARK:
            return DARK_THEME
        case unreachable:
            assert_never(unreachable)


def _windows_apps_use_light_theme() -> bool:
    if sys.platform != "win32":
        return True
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _kind = winreg.QueryValueEx(key, "AppsUseLightTheme")
    except OSError:
        return True
    return int(value) == 1


def configure_ttk_styles(root: tk.Misc, theme: Theme) -> None:
    from tkinter import ttk

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "App.Horizontal.TProgressbar",
        troughcolor=theme.input_bg,
        background=theme.accent,
        lightcolor=theme.accent,
        darkcolor=theme.accent,
        bordercolor=theme.border,
    )
    style.configure(
        "App.Vertical.TScrollbar",
        troughcolor=theme.panel,
        background=theme.panel_alt,
        bordercolor=theme.panel,
        arrowcolor=theme.text_muted,
    )
