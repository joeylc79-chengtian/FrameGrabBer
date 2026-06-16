from __future__ import annotations

import tkinter as tk

from theme import Theme, configure_ttk_styles


def apply_theme_tree(root: tk.Misc, old_theme: Theme, new_theme: Theme) -> None:
    configure_ttk_styles(root, new_theme)
    _apply_widget_theme(root, old_theme, new_theme)


def bind_button_theme(widget: tk.Widget, theme: Theme, primary: bool) -> None:
    widget._theme_role = "primary_button" if primary else "button"
    _style_button(widget, theme, primary)


def bind_danger_icon_theme(widget: tk.Widget, theme: Theme, normal_bg: str | None = None) -> None:
    widget._theme_role = "danger_icon"
    widget._theme_normal_bg = normal_bg or theme.panel
    _style_danger_icon(widget, theme)


def _apply_widget_theme(widget: tk.Misc, old_theme: Theme, new_theme: Theme) -> None:
    role = getattr(widget, "_theme_role", "")
    if role == "button":
        _style_button(widget, new_theme, False)
    elif role == "primary_button":
        _style_button(widget, new_theme, True)
    elif role == "danger_icon":
        widget._theme_normal_bg = new_theme.panel
        _style_danger_icon(widget, new_theme)
    elif role in {"option_row", "scrollable_frame", "segmented_control", "time_slider"}:
        widget.refresh_theme(new_theme)
    else:
        _replace_token_colors(widget, old_theme, new_theme)

    for child in widget.winfo_children():
        _apply_widget_theme(child, old_theme, new_theme)


def _style_button(widget: tk.Widget, theme: Theme, primary: bool) -> None:
    bg = theme.accent if primary else theme.button_bg
    fg = theme.button_text if primary else theme.text
    hover = theme.accent_hover if primary else theme.button_hover
    pressed = theme.accent_hover if primary else theme.button_pressed
    active_fg = theme.button_text if primary else theme.text
    widget.configure(bg=bg, fg=fg, activebackground=pressed, activeforeground=active_fg)
    widget.bind("<Enter>", lambda _event, target=widget, color=hover: target.configure(bg=color))
    widget.bind("<Leave>", lambda _event, target=widget, color=bg: target.configure(bg=color))


def _style_danger_icon(widget: tk.Widget, theme: Theme) -> None:
    bg = getattr(widget, "_theme_normal_bg", theme.panel)
    widget.configure(bg=bg, fg=theme.text_muted)
    widget.bind("<Enter>", lambda _event, target=widget: target.configure(bg=theme.error, fg=theme.button_text))
    widget.bind("<Leave>", lambda _event, target=widget, color=bg: target.configure(bg=color, fg=theme.text_muted))


def _replace_token_colors(widget: tk.Misc, old_theme: Theme, new_theme: Theme) -> None:
    color_map = {
        old_theme.bg: new_theme.bg,
        old_theme.panel: new_theme.panel,
        old_theme.panel_alt: new_theme.panel_alt,
        old_theme.input_bg: new_theme.input_bg,
        old_theme.border: new_theme.border,
        old_theme.border_active: new_theme.border_active,
        old_theme.button_bg: new_theme.button_bg,
        old_theme.button_hover: new_theme.button_hover,
        old_theme.button_pressed: new_theme.button_pressed,
        old_theme.text: new_theme.text,
        old_theme.text_muted: new_theme.text_muted,
        old_theme.text_subtle: new_theme.text_subtle,
        old_theme.accent: new_theme.accent,
        old_theme.accent_hover: new_theme.accent_hover,
        old_theme.accent_soft: new_theme.accent_soft,
        old_theme.success: new_theme.success,
        old_theme.error: new_theme.error,
        old_theme.disabled: new_theme.disabled,
        old_theme.button_text: new_theme.button_text,
    }
    for aliases in (
        ("bg", "background"),
        ("fg", "foreground"),
        ("activebackground",),
        ("activeforeground",),
        ("highlightbackground",),
        ("highlightcolor",),
        ("insertbackground",),
        ("disabledbackground",),
        ("disabledforeground",),
    ):
        option = _first_supported_option(widget, aliases)
        if option is None:
            continue
        try:
            current = widget.cget(option)
        except tk.TclError:
            continue
        replacement = _replacement_for_option(option, current, widget, old_theme, new_theme, color_map)
        if replacement is None:
            continue
        try:
            widget.configure(**{option: replacement})
        except tk.TclError:
            continue


def _first_supported_option(widget: tk.Misc, aliases: tuple[str, ...]) -> str | None:
    for option in aliases:
        try:
            widget.cget(option)
        except tk.TclError:
            continue
        return option
    return None


def _replacement_for_option(
    option: str,
    current: str,
    widget: tk.Misc,
    old_theme: Theme,
    new_theme: Theme,
    color_map: dict[str, str],
) -> str | None:
    if option in {"bg", "background", "activebackground", "disabledbackground"}:
        if current == old_theme.bg:
            return new_theme.bg
        if current == old_theme.panel_alt:
            return new_theme.panel_alt
        if current in {old_theme.panel, old_theme.button_bg}:
            return new_theme.panel
        if current == old_theme.input_bg:
            return new_theme.input_bg if widget.winfo_class() == "Entry" else new_theme.panel
    if option in {"fg", "foreground", "activeforeground", "disabledforeground", "insertbackground"}:
        text_map = {
            old_theme.text: new_theme.text,
            old_theme.text_muted: new_theme.text_muted,
            old_theme.text_subtle: new_theme.text_subtle,
            old_theme.accent: new_theme.accent,
            old_theme.accent_hover: new_theme.accent_hover,
            old_theme.success: new_theme.success,
            old_theme.error: new_theme.error,
            old_theme.disabled: new_theme.disabled,
            old_theme.button_text: new_theme.button_text,
        }
        return text_map.get(current)
    return color_map.get(current)
