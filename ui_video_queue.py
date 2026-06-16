from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence

from theme import FONT_FAMILY, Theme
from ui_models import VideoItem
from ui_theme_apply import bind_danger_icon_theme
from ui_widgets import ScrollableFrame, button, muted_label, panel, section_title


class VideoQueueView(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        on_add: Callable[[], None],
        on_clear: Callable[[], None],
        on_remove: Callable[[int], None],
    ) -> None:
        super().__init__(master, bg=theme.bg)
        self._theme = theme
        self._on_add = on_add
        self._on_clear = on_clear
        self._on_remove = on_remove
        self._items: Sequence[VideoItem] = ()
        self._thumbnail_images: list[tk.PhotoImage] = []

        self._container = panel(self, theme)
        self._container.pack(fill="both", expand=True)
        self._build_header()
        self._build_drop_area()
        self._list = ScrollableFrame(self._container, theme)
        self._list.pack(fill="both", expand=True, padx=14, pady=(10, 14))

    def _build_header(self) -> None:
        header = tk.Frame(self._container, bg=self._theme.panel)
        header.pack(fill="x", padx=18, pady=(18, 8))
        self._title = section_title(header, self._theme, "视频队列（0）")
        self._title.pack(side="left")
        button(header, self._theme, "添加视频", self._on_add).pack(side="right")
        button(header, self._theme, "清空列表", self._on_clear).pack(side="right", padx=(0, 8))

    def _build_drop_area(self) -> None:
        self._drop = tk.Frame(
            self._container,
            bg=self._theme.panel_alt,
            highlightthickness=1,
            highlightbackground=self._theme.border,
            height=82,
        )
        self._drop.pack(fill="x", padx=18, pady=(6, 10))
        self._drop.pack_propagate(False)
        center = tk.Frame(self._drop, bg=self._theme.panel_alt)
        center.place(relx=0.5, rely=0.5, anchor="center")
        headline = tk.Label(
            center,
            text="拖拽视频文件到此处，或点击 添加视频",
            font=(FONT_FAMILY, 10, "bold"),
            bg=self._theme.panel_alt,
            fg=self._theme.text_muted,
        )
        headline.pack()
        hint = tk.Label(
            center,
            text="支持 mp4、mov、mkv、avi、m4v 等常见格式",
            font=(FONT_FAMILY, 8),
            bg=self._theme.panel_alt,
            fg=self._theme.text_subtle,
        )
        hint.pack(pady=(6, 0))
        for widget in (self._drop, center, headline, hint):
            widget.bind("<Enter>", lambda _event: self._set_drop_hover(True))
            widget.bind("<Leave>", lambda _event: self._set_drop_hover(False))

    def render(self, items: Sequence[VideoItem]) -> None:
        self._items = items
        self._thumbnail_images.clear()
        self._title.configure(text=f"视频队列（{len(items)}）")
        for child in self._list.content.winfo_children():
            child.destroy()
        if not items:
            muted_label(self._list.content, self._theme, "还没有导入视频").pack(anchor="w", padx=8, pady=12)
            return
        for index, item in enumerate(items):
            self._build_item_card(index, item)

    def refresh_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.configure(bg=theme.bg)
        self._container.configure(bg=theme.panel, highlightbackground=theme.border)
        self._drop.configure(bg=theme.panel_alt, highlightbackground=theme.border)
        self._list._theme = theme
        self._list.configure(bg=theme.panel)
        self._list.canvas.configure(bg=theme.panel)
        self._list.content.configure(bg=theme.panel)
        self._list.scrollbar.configure(bg=theme.panel)

    def _build_item_card(self, index: int, item: VideoItem) -> None:
        card_bg = self._theme.panel
        card = tk.Frame(
            self._list.content,
            bg=card_bg,
            highlightthickness=1,
            highlightbackground=self._theme.border,
        )
        card.pack(fill="x", pady=(0, 10), padx=2)

        top = tk.Frame(card, bg=card_bg)
        top.pack(fill="x", padx=12, pady=(10, 4))
        thumbnail = self._thumbnail_widget(top, item, card_bg)
        thumbnail.pack(side="left", padx=(0, 10))
        number = tk.Label(
            top,
            text=str(index + 1),
            font=(FONT_FAMILY, 11, "bold"),
            bg=card_bg,
            fg=self._theme.accent,
        )
        number.pack(side="left", padx=(0, 10))
        name = tk.Label(
            top,
            text=item.info.name,
            font=(FONT_FAMILY, 10, "bold"),
            bg=card_bg,
            fg=self._theme.text,
            anchor="w",
        )
        name.pack(side="left", fill="x", expand=True)
        close = tk.Label(
            top,
            text="×",
            font=(FONT_FAMILY, 12, "bold"),
            bg=card_bg,
            fg=self._theme.text_muted,
            cursor="hand2",
            padx=7,
            pady=1,
        )
        bind_danger_icon_theme(close, self._theme, card_bg)
        close.pack(side="right")
        close.bind("<Button-1>", lambda event, remove_index=index: self._remove_clicked(event, remove_index))

        meta = tk.Frame(card, bg=card_bg)
        meta.pack(fill="x", padx=12, pady=(4, 12))
        children: list[tk.Widget] = [top, number, name, meta]
        for label, value in self._meta_pairs(item):
            group = tk.Frame(meta, bg=card_bg)
            group.pack(side="left", padx=(0, 20))
            label_widget = tk.Label(group, text=label, font=(FONT_FAMILY, 8), bg=card_bg, fg=self._theme.text_subtle)
            value_widget = tk.Label(group, text=value, font=(FONT_FAMILY, 9), bg=card_bg, fg=self._theme.text_muted)
            label_widget.pack(anchor="w")
            value_widget.pack(anchor="w")

    def _set_drop_hover(self, active: bool) -> None:
        border = self._theme.border_active if active else self._theme.border
        self._drop.configure(highlightbackground=border)

    def _remove_clicked(self, event: tk.Event, index: int) -> None:
        self._on_remove(index)
        return "break"

    def _thumbnail_widget(self, master: tk.Misc, item: VideoItem, bg: str) -> tk.Label:
        if item.thumbnail_path:
            try:
                image = tk.PhotoImage(file=item.thumbnail_path)
            except tk.TclError:
                image = None
            if image:
                self._thumbnail_images.append(image)
                return tk.Label(master, image=image, bg=bg, width=96, height=54)
        text = "封面生成中" if item.thumbnail_status == "pending" else "无封面"
        return tk.Label(
            master,
            text=text,
            font=(FONT_FAMILY, 8),
            bg=self._theme.panel_alt,
            fg=self._theme.text_subtle,
            width=12,
            height=3,
        )

    def _meta_pairs(self, item: VideoItem) -> tuple[tuple[str, str], ...]:
        info = item.info
        return (
            ("分辨率", f"{info.width}×{info.height}"),
            ("帧率", f"{info.fps:.2f} fps"),
            ("时长", self._format_duration(info.duration)),
            ("帧数", f"{info.total_frames:,}"),
        )

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total = max(0, int(round(seconds)))
        hours = total // 3600
        minutes = (total % 3600) // 60
        secs = total % 60
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
