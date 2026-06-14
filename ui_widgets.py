from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from theme import FONT_FAMILY, Theme


class ScrollableFrame(tk.Frame):
    def __init__(self, master: tk.Misc, theme: Theme, height: int | None = None, autohide: bool = True) -> None:
        super().__init__(master, bg=theme.panel)
        self._theme = theme
        self._autohide = autohide
        self._scrollbar_visible = False
        self.canvas = tk.Canvas(self, bg=theme.panel, highlightthickness=0, bd=0, height=height)
        self.content = tk.Frame(self.canvas, bg=theme.panel)
        self.scrollbar = tk.Canvas(self, width=10, bg=theme.panel, bd=0, highlightthickness=0, cursor="hand2")
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_canvas_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        if not autohide:
            self.scrollbar.pack(side="right", fill="y")
            self._scrollbar_visible = True
        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._fit_content_width)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.content.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.scrollbar.bind("<Button-1>", self._jump_scroll)
        self.scrollbar.bind("<B1-Motion>", self._jump_scroll)

    def bind_mousewheel_recursive(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_mousewheel_recursive(child)

    def _update_scroll_region(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.bind_mousewheel_recursive(self.content)
        self._sync_scrollbar()

    def _fit_content_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)
        self._sync_scrollbar()

    def _on_mousewheel(self, event: tk.Event) -> str | None:
        if not self.winfo_ismapped() or not self._can_scroll():
            return None
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_canvas_scroll(self, first: str, last: str) -> None:
        self._draw_scrollbar(float(first), float(last))

    def _sync_scrollbar(self) -> None:
        self._draw_scrollbar(*self.canvas.yview())
        if not self._autohide:
            return
        should_show = self.content.winfo_reqheight() > self.canvas.winfo_height() + 2
        if should_show and not self._scrollbar_visible:
            self.scrollbar.pack(side="right", fill="y")
            self._scrollbar_visible = True
        if not should_show and self._scrollbar_visible:
            self.scrollbar.pack_forget()
            self._scrollbar_visible = False

    def _draw_scrollbar(self, first: float, last: float) -> None:
        self.scrollbar.delete("all")
        height = max(1, self.scrollbar.winfo_height())
        if last - first >= 0.999:
            return
        self.scrollbar.create_line(5, 4, 5, height - 4, fill=self._theme.input_bg, width=4, capstyle="round")
        top = 4 + first * max(1, height - 8)
        bottom = 4 + last * max(1, height - 8)
        self.scrollbar.create_line(5, top, 5, max(top + 24, bottom), fill=self._theme.text_subtle, width=5, capstyle="round")

    def _jump_scroll(self, event: tk.Event) -> str:
        height = max(1, self.scrollbar.winfo_height())
        ratio = min(1.0, max(0.0, float(event.y) / float(height)))
        self.canvas.yview_moveto(ratio)
        return "break"

    def _can_scroll(self) -> bool:
        first, last = self.canvas.yview()
        return last - first < 0.999


class SegmentedControl(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        variable: tk.StringVar,
        values: tuple[str, ...],
        command: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=theme.input_bg, highlightthickness=1, highlightbackground=theme.border)
        self._theme = theme
        self._variable = variable
        self._values = values
        self._command = command
        self._buttons: list[tk.Label] = []
        for value in values:
            label = tk.Label(
                self,
                text=value,
                font=(FONT_FAMILY, 9),
                bg=theme.input_bg,
                fg=theme.text_muted,
                padx=18,
                pady=6,
                cursor="hand2",
            )
            label.pack(side="left", padx=1, pady=1)
            label.bind("<Button-1>", lambda _event, selected=value: self._select(selected))
            label.bind("<Enter>", lambda _event, hovered=label: self._hover(hovered, True))
            label.bind("<Leave>", lambda _event, hovered=label: self._hover(hovered, False))
            self._buttons.append(label)
        self.refresh(theme)

    def _select(self, value: str) -> None:
        self._variable.set(value)
        self._command()

    def refresh(self, theme: Theme) -> None:
        self._theme = theme
        self.configure(bg=theme.input_bg, highlightbackground=theme.border)
        for button in self._buttons:
            selected = button.cget("text") == self._variable.get()
            button.configure(
                bg=theme.accent if selected else theme.input_bg,
                fg=theme.button_text if selected else theme.text_muted,
            )

    def _hover(self, label: tk.Label, active: bool) -> None:
        if label.cget("text") == self._variable.get():
            return
        label.configure(bg=self._theme.panel_alt if active else self._theme.input_bg)


class TimeSlider(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        variable: tk.DoubleVar,
        from_: float,
        to: float,
        command: Callable[[], None],
        bg: str | None = None,
    ) -> None:
        super().__init__(master, height=28, bg=bg or theme.panel, bd=0, highlightthickness=0, cursor="hand2")
        self._theme = theme
        self._variable = variable
        self._from = from_
        self._to = max(from_ + 0.1, to)
        self._command = command
        self._enabled = True
        self._trace_id = variable.trace_add("write", lambda *_args: self._draw())
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Button-1>", self._set_from_event)
        self.bind("<B1-Motion>", self._set_from_event)
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def destroy(self) -> None:
        try:
            self._variable.trace_remove("write", self._trace_id)
        except tk.TclError:
            pass
        super().destroy()

    def _set_from_event(self, event: tk.Event) -> None:
        if not self._enabled:
            return
        width = max(1, self.winfo_width() - 24)
        ratio = min(1.0, max(0.0, (float(event.x) - 12.0) / float(width)))
        value = self._from + (self._to - self._from) * ratio
        self._variable.set(round(value, 1))
        self._command()

    def _draw(self) -> None:
        self.delete("all")
        width = max(1, self.winfo_width())
        center_y = 14
        start_x = 12
        end_x = max(start_x + 1, width - 12)
        ratio = (float(self._variable.get()) - self._from) / (self._to - self._from)
        ratio = min(1.0, max(0.0, ratio))
        handle_x = start_x + (end_x - start_x) * ratio
        track = self._theme.input_bg if self._enabled else self._theme.panel_alt
        fill = self._theme.accent if self._enabled else self._theme.disabled
        handle = self._theme.text if self._enabled else self._theme.text_subtle
        self.create_line(start_x, center_y, end_x, center_y, fill=track, width=6, capstyle="round")
        self.create_line(start_x, center_y, handle_x, center_y, fill=fill, width=6, capstyle="round")
        self.create_oval(handle_x - 7, center_y - 7, handle_x + 7, center_y + 7, fill=handle, outline=fill)


def panel(master: tk.Misc, theme: Theme) -> tk.Frame:
    return tk.Frame(master, bg=theme.panel, highlightthickness=1, highlightbackground=theme.border)


def section_title(master: tk.Misc, theme: Theme, text: str) -> tk.Label:
    return tk.Label(master, text=text, font=(FONT_FAMILY, 12, "bold"), bg=theme.panel, fg=theme.text)


def muted_label(master: tk.Misc, theme: Theme, text: str, size: int = 9) -> tk.Label:
    return tk.Label(master, text=text, font=(FONT_FAMILY, size), bg=theme.panel, fg=theme.text_subtle)


def button(
    master: tk.Misc,
    theme: Theme,
    text: str,
    command: Callable[[], None],
    primary: bool = False,
) -> tk.Button:
    bg = theme.accent if primary else theme.input_bg
    fg = theme.button_text if primary else theme.text
    active_bg = theme.accent_hover if primary else theme.panel_alt
    widget = tk.Button(
        master,
        text=text,
        command=command,
        font=(FONT_FAMILY, 10, "bold" if primary else "normal"),
        bg=bg,
        fg=fg,
        activebackground=theme.accent_hover if primary else theme.panel_alt,
        activeforeground=theme.button_text if primary else theme.text,
        relief="flat",
        bd=0,
        padx=16,
        pady=8,
        cursor="hand2",
    )
    widget.bind("<Enter>", lambda _event: widget.configure(bg=active_bg))
    widget.bind("<Leave>", lambda _event: widget.configure(bg=bg))
    return widget


def input_entry(master: tk.Misc, theme: Theme, textvariable: tk.StringVar, width: int = 10) -> tk.Entry:
    return tk.Entry(
        master,
        textvariable=textvariable,
        width=width,
        font=(FONT_FAMILY, 10),
        bg=theme.input_bg,
        fg=theme.text,
        insertbackground=theme.text,
        disabledbackground=theme.panel_alt,
        disabledforeground=theme.text_subtle,
        relief="flat",
        highlightthickness=1,
        highlightbackground=theme.border,
        highlightcolor=theme.border_active,
    )
