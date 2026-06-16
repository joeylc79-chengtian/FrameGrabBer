from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from theme import FONT_FAMILY, Theme


class OptionRow(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        text: str,
        variable: tk.BooleanVar | tk.StringVar,
        command: Callable[[], None],
        value: str | None = None,
        kind: str = "check",
        muted: bool = False,
    ) -> None:
        super().__init__(master, bg=theme.panel, cursor="hand2")
        self._theme = theme
        self._variable = variable
        self._command = command
        self._value = value
        self._kind = kind
        self._muted = muted
        self._hover = False
        self._theme_role = "option_row"
        self._trace_id = variable.trace_add("write", lambda *_args: self._draw())

        self._mark = tk.Canvas(self, width=18, height=18, bg=theme.panel, bd=0, highlightthickness=0, cursor="hand2")
        self._mark.pack(side="left", padx=(0, 8))
        self._label = tk.Label(
            self,
            text=text,
            font=(FONT_FAMILY, 10 if not muted else 9),
            bg=theme.panel,
            fg=theme.text_muted if muted else theme.text,
            cursor="hand2",
        )
        self._label.pack(side="left")
        for widget in (self, self._mark, self._label):
            widget.bind("<Button-1>", self._toggle)
            widget.bind("<Enter>", lambda _event: self._set_hover(True))
            widget.bind("<Leave>", lambda _event: self._set_hover(False))
        self._draw()

    def refresh_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.configure(bg=theme.panel)
        self._mark.configure(bg=theme.panel)
        self._label.configure(bg=theme.panel, fg=theme.text_muted if self._muted else theme.text)
        self._draw()

    def destroy(self) -> None:
        try:
            self._variable.trace_remove("write", self._trace_id)
        except tk.TclError:
            pass
        super().destroy()

    def _toggle(self, _event: tk.Event) -> str:
        if self._value is None:
            self._variable.set(not bool(self._variable.get()))
        else:
            self._variable.set(self._value)
        self._draw()
        self._command()
        return "break"

    def _set_hover(self, active: bool) -> None:
        self._hover = active
        self._draw()

    def _selected(self) -> bool:
        if self._value is None:
            return bool(self._variable.get())
        return self._variable.get() == self._value

    def _draw(self) -> None:
        self._mark.delete("all")
        selected = self._selected()
        outline = self._theme.border_active if self._hover or selected else self._theme.border
        fill = self._theme.accent if selected else self._theme.panel
        if self._kind == "radio":
            self._mark.create_oval(3, 3, 15, 15, outline=outline, width=2, fill=self._theme.panel)
            if selected:
                self._mark.create_oval(7, 7, 11, 11, outline=fill, fill=fill)
            return
        self._mark.create_rectangle(3, 3, 15, 15, outline=outline, width=2, fill=fill)
        if selected:
            self._mark.create_line(6, 9, 8, 12, 13, 6, fill=self._theme.button_text, width=2, capstyle="round")
