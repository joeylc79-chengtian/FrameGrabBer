# -*- coding: utf-8 -*-
"""
视频逐帧抽图工具 — 重构版
- 内置 imageio-ffmpeg 静态 ffmpeg，完全离线可用
- 支持拖拽导入视频（tkinterdnd2）
- 现代化 UI 设计（白底深蓝主题）
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import sys
import threading
import queue
import re

# ── 检测可选依赖 ──────────────────────────
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

try:
    import imageio_ffmpeg
    HAS_IMAGEIO_FFMPEG = True
except ImportError:
    HAS_IMAGEIO_FFMPEG = False


# ── 颜色常量 ──────────────────────────────
CLR_BG           = '#ffffff'
CLR_PRIMARY      = '#1a56db'
CLR_PRIMARY_DARK = '#1e40af'
CLR_PRIMARY_LIGHT = '#dbeafe'
CLR_TEXT         = '#1e293b'
CLR_TEXT_SEC     = '#64748b'
CLR_TEXT_SUBTLE  = '#94a3b8'
CLR_BORDER       = '#e2e8f0'
CLR_CARD_BG      = '#f8fafc'
CLR_SUCCESS      = '#16a34a'
CLR_ERROR        = '#dc2626'
CLR_DROP_BORDER  = '#93c5fd'
CLR_DROP_BG      = '#eff6ff'

FONT = '微软雅黑'

# 支持的视频扩展名
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}


# ── 图标路径解析 ──────────────────────────

def _resolve_icon_path():
    """返回 app.ico 的绝对路径。
    优先级：PyInstaller _MEIPASS > 脚本同目录 > None"""
    # PyInstaller 打包环境
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')
        path = os.path.join(meipass, 'app.ico')
        if os.path.isfile(path):
            return path

    # 开发环境：脚本同目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, 'app.ico')
    if os.path.isfile(path):
        return path

    return None


# ── FFmpeg 路径解析 ────────────────────────

def _get_ffmpeg_exe():
    """获取内置 ffmpeg 可执行文件的绝对路径。
    优先级：imageio_ffmpeg.get_ffmpeg_exe() > PyInstaller 环境搜索 > site-packages 搜索"""
    if not HAS_IMAGEIO_FFMPEG:
        return None

    # 方式 1：使用 imageio_ffmpeg 的官方接口
    try:
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.isfile(path):
            return path
    except Exception:
        pass

    # 方式 2：PyInstaller 打包环境中手动搜索
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            for root, _dirs, files in os.walk(meipass):
                for f in files:
                    if f.startswith('ffmpeg') and f.endswith('.exe'):
                        return os.path.join(root, f)

    # 方式 3：在 site-packages 中搜索 imageio_ffmpeg 目录
    try:
        import site
        for site_dir in site.getsitepackages():
            bin_dir = os.path.join(site_dir, 'imageio_ffmpeg', 'binaries')
            if os.path.isdir(bin_dir):
                for f in os.listdir(bin_dir):
                    if f.startswith('ffmpeg') and f.endswith('.exe'):
                        return os.path.join(bin_dir, f)
    except Exception:
        pass

    return None


# ── 视频信息解析 ──────────────────────────

def _parse_video_info(video_path, ffmpeg_exe):
    """通过 ffmpeg -i 解析视频信息（stderr 输出）。
    返回 dict: {width, height, fps, total_frames, duration}，失败返回 None。"""
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        result = subprocess.run(
            [ffmpeg_exe, '-i', video_path],
            capture_output=True, text=True,
            encoding='utf-8', errors='replace',
            creationflags=creationflags,
        )
        stderr = result.stderr

        # Duration: 00:00:10.05
        duration = 0.0
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+)\.(\d+)', stderr)
        if m:
            h, mi, s, ms = map(int, m.groups())
            duration = h * 3600 + mi * 60 + s + ms / 100.0

        # Stream #0:0: Video: ..., 1920x1080, 30 fps
        width = height = 0
        fps = 30.0
        m = re.search(r'Stream #\d+:\d+.*Video:.*\s(\d+)x(\d+)', stderr)
        if m:
            width, height = int(m.group(1)), int(m.group(2))

        m_fps = re.search(r'(\d+\.?\d*)\s*fps', stderr)
        if m_fps:
            fps = float(m_fps.group(1))

        total_frames = int(duration * fps) if duration > 0 else 0

        return {
            'width': width,
            'height': height,
            'fps': round(fps, 2),
            'total_frames': total_frames,
            'duration': duration,
        }
    except Exception:
        return None


# ── 主窗口 ────────────────────────────────

if HAS_DND:
    class _BaseTk(TkinterDnD.Tk):
        """tkinterdnd2 基类"""
else:
    class _BaseTk(tk.Tk):
        """普通 tk.Tk 基类"""


class App(_BaseTk):
    """视频逐帧抽图工具主窗口"""

    def __init__(self):
        super().__init__()

        # ── 窗口基础属性 ──
        self.title('视频逐帧抽图工具')
        self.geometry('600x520')
        self.resizable(False, False)
        self.configure(bg=CLR_BG)

        # 设置窗口图标（优先用 app.ico，支持打包后 _MEIPASS 路径）
        icon_path = _resolve_icon_path()
        if icon_path:
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # ── 实例变量 ──
        self._ffmpeg_exe = None      # ffmpeg 可执行文件路径
        self._video_info = None      # 视频信息 dict / None
        self._video_path = None      # 当前视频路径
        self._output_dir = None      # 输出目录
        self._prefix = tk.StringVar(value='')
        self._format_var = tk.StringVar(value='png')
        self._interval_var = tk.StringVar(value='每帧')
        self._custom_n = tk.StringVar(value='5')

        self._queue = queue.Queue()
        self._running = False
        self._dropping = False       # 是否正在拖拽文件到窗口

        # ── 初始化 ──
        self._resolve_ffmpeg()
        self._build_ui()
        self._poll_queue()

        # 注册拖拽
        if HAS_DND:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_drop)
            self.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.dnd_bind('<<DragLeave>>', self._on_drag_leave)

    # ═══════════════════════════════════════
    #  FFmpeg 环境
    # ═══════════════════════════════════════

    def _resolve_ffmpeg(self):
        """解析 ffmpeg 路径，设置 self._ffmpeg_exe"""
        self._ffmpeg_exe = _get_ffmpeg_exe()
        if not self._ffmpeg_exe:
            self._set_status('⚠️ 未找到内置 FFmpeg，请安装 imageio-ffmpeg 包', CLR_ERROR)

    # ═══════════════════════════════════════
    #  UI 构建
    # ═══════════════════════════════════════

    def _build_ui(self):
        """分块构建全部界面"""
        self._build_header()
        self._build_drop_zone()
        self._build_file_label()
        self._build_video_info_card()
        self._build_export_settings()
        self._build_action_area()
        self._build_status_bar()

    def _build_header(self):
        """顶部：Logo + 标题"""
        header = tk.Frame(self, bg=CLR_BG)
        header.pack(fill='x', padx=24, pady=(18, 6))

        # Logo 图标（生成一个纯 tk 的小图标）
        self._logo_canvas = tk.Canvas(
            header, width=32, height=32,
            bg=CLR_BG, highlightthickness=0, bd=0,
        )
        self._logo_canvas.pack(side='left', padx=(0, 10))
        self._draw_logo_on_canvas(self._logo_canvas, 32)

        # 标题
        tk.Label(
            header, text='视频逐帧抽图工具',
            font=(FONT, 14, 'bold'),
            bg=CLR_BG, fg=CLR_TEXT,
        ).pack(side='left')

    def _draw_logo_on_canvas(self, canvas, size):
        """在 Canvas 上绘制简易 Logo（纯 tkinter，无外部依赖）"""
        margin = 1
        r = 5  # 圆角近似半径

        # 深蓝背景圆角矩形
        canvas.create_rectangle(
            margin + r, margin,
            size - margin - r, size - margin,
            fill=CLR_PRIMARY, outline='', tags='logo',
        )
        canvas.create_rectangle(
            margin, margin + r,
            size - margin, size - margin - r,
            fill=CLR_PRIMARY, outline='', tags='logo',
        )
        # 四个角落用弧形近似圆角
        for cx, cy in [(margin + r, margin + r),
                        (size - margin - r, margin + r),
                        (margin + r, size - margin - r),
                        (size - margin - r, size - margin - r)]:
            canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=CLR_PRIMARY, outline='', tags='logo',
            )

        # 内部白色菱形
        cx, cy = size // 2, size // 2
        d = 6
        canvas.create_polygon(
            cx, cy - d, cx + d, cy,
            cx, cy + d, cx - d, cy,
            fill='white', outline='', tags='logo',
        )

        # 左侧齿孔
        for hy in (7, 13, 19, 25):
            canvas.create_rectangle(
                2, hy - 1, 5, hy + 1,
                fill='white', outline='', tags='logo',
            )
            canvas.create_rectangle(
                size - 5, hy - 1, size - 2, hy + 1,
                fill='white', outline='', tags='logo',
            )

    def _build_drop_zone(self):
        """中间：拖拽区域（Canvas 画虚线框）"""
        self._drop_canvas = tk.Canvas(
            self, width=552, height=110,
            bg=CLR_BG, highlightthickness=0, bd=0,
            cursor='hand2',
        )
        self._drop_canvas.pack(padx=24, pady=(6, 2))
        self._drop_canvas.bind('<Button-1>', self._on_drop_zone_click)
        self._draw_drop_zone_normal()

    def _draw_drop_zone_normal(self):
        """绘制拖拽区域的默认状态"""
        c = self._drop_canvas
        c.delete('drop')
        w, h = 552, 110

        # 虚线矩形
        self._draw_dashed_rect(c, 0, 0, w, h, CLR_BORDER, CLR_BG, 'drop')

        # 图标文字
        c.create_text(
            w // 2, h // 2 - 10,
            text='📁  拖拽视频到此处，或点击选择',
            font=(FONT, 11), fill=CLR_TEXT_SEC,
            anchor='center', tags='drop',
        )
        c.create_text(
            w // 2, h // 2 + 14,
            text='支持 MP4 / AVI / MOV / MKV / FLV / WMV 等常见格式',
            font=(FONT, 8), fill=CLR_TEXT_SUBTLE,
            anchor='center', tags='drop',
        )

    def _draw_drop_zone_active(self):
        """绘制拖拽区域的激活状态（文件拖入时高亮）"""
        c = self._drop_canvas
        c.delete('drop')
        w, h = 552, 110

        self._draw_dashed_rect(c, 0, 0, w, h, CLR_PRIMARY, CLR_DROP_BG, 'drop')

        c.create_text(
            w // 2, h // 2,
            text='📁  松开鼠标导入视频',
            font=(FONT, 12, 'bold'), fill=CLR_PRIMARY,
            anchor='center', tags='drop',
        )

    @staticmethod
    def _draw_dashed_rect(canvas, x1, y1, x2, y2, color, fill_color, tag):
        """在 Canvas 上绘制虚线边框矩形"""
        # 背景填充（留 1px 给边框）
        canvas.create_rectangle(
            x1 + 1, y1 + 1, x2 - 1, y2 - 1,
            fill=fill_color, outline='', tags=tag,
        )
        # 四条虚线边框（利用 tkinter Canvas 自带的 dash 参数）
        dash_pattern = (6, 4)
        canvas.create_line(x1, y1, x2, y1, fill=color, width=1,
                           dash=dash_pattern, tags=tag)      # 上
        canvas.create_line(x1, y2, x2, y2, fill=color, width=1,
                           dash=dash_pattern, tags=tag)      # 下
        canvas.create_line(x1, y1, x1, y2, fill=color, width=1,
                           dash=dash_pattern, tags=tag)      # 左
        canvas.create_line(x2, y1, x2, y2, fill=color, width=1,
                           dash=dash_pattern, tags=tag)      # 右

    def _build_file_label(self):
        """已选文件标签"""
        self._lbl_file = tk.Label(
            self, text='未选择视频',
            font=(FONT, 9), bg=CLR_BG, fg=CLR_TEXT_SUBTLE,
            anchor='w',
        )
        self._lbl_file.pack(fill='x', padx=28, pady=(2, 6))

    def _build_video_info_card(self):
        """视频信息卡片：分辨率 / 帧率 / 总帧数 / 时长（纵向值+标签排列）"""
        self._card_frame = tk.Frame(self, bg=CLR_CARD_BG,
                                     highlightbackground=CLR_BORDER,
                                     highlightthickness=1)

        # 卡片标题
        tk.Label(
            self._card_frame, text='📊 视频信息',
            font=(FONT, 9, 'bold'), bg=CLR_CARD_BG, fg=CLR_TEXT,
        ).pack(anchor='w', padx=14, pady=(8, 4))

        # 4 个指标横向排列（每个指标 = 上值 + 下标签，纵向对齐）
        metrics_frame = tk.Frame(self._card_frame, bg=CLR_CARD_BG)
        metrics_frame.pack(fill='x', padx=14, pady=(0, 10))

        self._lbl_resolution = None
        self._lbl_fps = None
        self._lbl_frames = None
        self._lbl_duration = None

        for key, label_text in [
            ('resolution', '分辨率'),
            ('fps', '帧率'),
            ('frames', '总帧数'),
            ('duration', '时长'),
        ]:
            pair = tk.Frame(metrics_frame, bg=CLR_CARD_BG)
            pair.pack(side='left', expand=True)

            val = tk.Label(pair, text='—', font=(FONT, 13, 'bold'),
                           bg=CLR_CARD_BG, fg=CLR_PRIMARY)
            val.pack(anchor='w')
            tk.Label(pair, text=label_text, font=(FONT, 8),
                     bg=CLR_CARD_BG, fg=CLR_TEXT_SUBTLE).pack(anchor='w')

            setattr(self, f'_lbl_{key}', val)

        # 初始隐藏
        self._card_frame.pack_forget()

    def _build_export_settings(self):
        """导出设置区域：格式 + 帧间隔 + 前缀"""
        settings = tk.LabelFrame(
            self, text='导出设置', font=(FONT, 10, 'bold'),
            bg=CLR_BG, fg=CLR_TEXT,
            foreground=CLR_TEXT,
        )
        settings.pack(fill='x', padx=24, pady=(2, 4))

        # ── 图片格式 ──
        fmt_frame = tk.Frame(settings, bg=CLR_BG)
        fmt_frame.pack(fill='x', padx=14, pady=(6, 2))

        tk.Label(fmt_frame, text='图片格式：', font=(FONT, 9),
                 bg=CLR_BG, fg=CLR_TEXT).pack(side='left')

        # 自定义分段式 radio button 样式
        for text, value in [('PNG（无损）', 'png'), ('JPG（体积小）', 'jpg')]:
            rb = tk.Radiobutton(
                fmt_frame, text=text, variable=self._format_var,
                value=value, font=(FONT, 9),
                bg=CLR_BG, fg=CLR_TEXT,
                activebackground=CLR_BG,
                selectcolor=CLR_BG,
                indicatoron=True,
                padx=6,
            )
            rb.pack(side='left', padx=(12, 0))

        # ── 帧间隔 ──
        int_frame = tk.Frame(settings, bg=CLR_BG)
        int_frame.pack(fill='x', padx=14, pady=(4, 2))

        tk.Label(int_frame, text='帧率间隔：', font=(FONT, 9),
                 bg=CLR_BG, fg=CLR_TEXT).pack(side='left')

        for text, value in [
            ('逐帧', '每帧'),
            ('每秒 1 帧', '每秒1帧'),
        ]:
            rb = tk.Radiobutton(
                int_frame, text=text, variable=self._interval_var,
                value=value, font=(FONT, 9),
                bg=CLR_BG, fg=CLR_TEXT,
                activebackground=CLR_BG,
                selectcolor=CLR_BG,
                indicatoron=True,
                padx=6,
            )
            rb.pack(side='left', padx=(12, 0))

        # 自定义间隔
        rb_custom = tk.Radiobutton(
            int_frame, text='每', variable=self._interval_var,
            value='自定义', font=(FONT, 9),
            bg=CLR_BG, fg=CLR_TEXT,
            activebackground=CLR_BG,
            selectcolor=CLR_BG,
            indicatoron=True,
            padx=6,
        )
        rb_custom.pack(side='left', padx=(12, 0))

        self._spin_n = tk.Spinbox(
            int_frame, from_=1, to=9999, textvariable=self._custom_n,
            width=5, font=(FONT, 9),
            state='readonly', readonlybackground='white',
        )
        self._spin_n.pack(side='left', padx=(4, 0))

        tk.Label(int_frame, text='帧抽 1 帧', font=(FONT, 9),
                 bg=CLR_BG, fg=CLR_TEXT).pack(side='left', padx=(2, 0))

        # 联动
        self._interval_var.trace('w', self._on_interval_change)

        # ── 文件前缀 ──
        pre_frame = tk.Frame(settings, bg=CLR_BG)
        pre_frame.pack(fill='x', padx=14, pady=(4, 8))

        tk.Label(pre_frame, text='文件前缀：', font=(FONT, 9),
                 bg=CLR_BG, fg=CLR_TEXT).pack(side='left')

        self._entry_prefix = tk.Entry(
            pre_frame, textvariable=self._prefix,
            font=(FONT, 9), width=28,
            relief='solid', borderwidth=1,
        )
        self._entry_prefix.pack(side='left', padx=(8, 0))

        tk.Label(pre_frame, text='例：shot.00000.png', font=(FONT, 8),
                 bg=CLR_BG, fg=CLR_TEXT_SUBTLE).pack(side='left', padx=(8, 0))

        # 预估输出
        self._lbl_estimate = tk.Label(
            settings, text='', font=(FONT, 8),
            bg=CLR_BG, fg=CLR_TEXT_SEC,
        )
        self._lbl_estimate.pack(anchor='w', padx=14, pady=(0, 6))

    def _build_action_area(self):
        """底部操作区：开始按钮 + 进度条"""
        action = tk.Frame(self, bg=CLR_BG)
        action.pack(fill='x', padx=24, pady=(6, 2))

        # 开始按钮（自绘大按钮，更美观）
        self._btn_start_canvas = tk.Canvas(
            action, width=180, height=42,
            bg=CLR_BG, highlightthickness=0, bd=0,
            cursor='hand2',
        )
        self._btn_start_canvas.pack(pady=(2, 4))
        self._btn_start_canvas.bind('<Button-1>', self._start)
        self._draw_start_button_normal()

        # 进度条
        self._progress = ttk.Progressbar(
            action, mode='determinate', maximum=100,
            style='Custom.Horizontal.TProgressbar',
        )
        self._progress.pack(fill='x', pady=(2, 2))

        self._lbl_progress = tk.Label(
            action, text='', font=(FONT, 9),
            bg=CLR_BG, fg=CLR_TEXT_SEC,
        )
        self._lbl_progress.pack(fill='x')

        # 配置 ttk 样式
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'Custom.Horizontal.TProgressbar',
            troughcolor=CLR_BORDER,
            background=CLR_PRIMARY,
            lightcolor=CLR_PRIMARY,
            darkcolor=CLR_PRIMARY,
            bordercolor=CLR_BORDER,
        )

    def _draw_start_button_normal(self):
        """绘制开始按钮的默认/禁用状态"""
        c = self._btn_start_canvas
        c.delete('btn')
        w, h = 180, 42
        radius = 6

        # 背景
        _draw_rounded_rect_canvas(c, 0, 0, w, h, radius, CLR_PRIMARY, 'btn')
        c.create_text(
            w // 2, h // 2,
            text='▶  开始抽图',
            font=(FONT, 11, 'bold'), fill='white',
            anchor='center', tags='btn',
        )

    def _draw_start_button_disabled(self):
        """绘制开始按钮的禁用状态"""
        c = self._btn_start_canvas
        c.delete('btn')
        w, h = 180, 42
        radius = 6

        _draw_rounded_rect_canvas(c, 0, 0, w, h, radius, '#cbd5e1', 'btn')
        c.create_text(
            w // 2, h // 2,
            text='▶  开始抽图',
            font=(FONT, 11, 'bold'), fill='#94a3b8',
            anchor='center', tags='btn',
        )

    def _draw_start_button_hover(self, event=None):
        """鼠标悬停按钮"""
        if self._running:
            return
        c = self._btn_start_canvas
        c.delete('btn')
        w, h = 180, 42
        _draw_rounded_rect_canvas(c, 0, 0, w, h, 6, CLR_PRIMARY_DARK, 'btn')
        c.create_text(
            w // 2, h // 2,
            text='▶  开始抽图',
            font=(FONT, 11, 'bold'), fill='white',
            anchor='center', tags='btn',
        )

    def _draw_start_button_leave(self, event=None):
        """鼠标离开按钮"""
        if self._running:
            return
        self._draw_start_button_normal()

    def _build_status_bar(self):
        """底部状态栏"""
        self._lbl_status = tk.Label(
            self, text='就绪',
            font=(FONT, 9), bg=CLR_BG, fg=CLR_TEXT_SUBTLE,
            anchor='w',
        )
        self._lbl_status.pack(fill='x', padx=28, pady=(4, 8))

    # ═══════════════════════════════════════
    #  按钮交互
    # ═══════════════════════════════════════

    def _on_drop_zone_click(self, event=None):
        """点击拖拽区域 → 打开文件选择对话框"""
        self._select_video()

    def _select_video(self):
        """打开文件对话框选择视频"""
        path = filedialog.askopenfilename(
            title='选择视频文件',
            filetypes=[
                ('视频文件', '*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm *.m4v'),
                ('所有文件', '*.*'),
            ],
        )
        if not path:
            return
        self._load_video(path)

    # ═══════════════════════════════════════
    #  拖拽处理（tkinterdnd2）
    # ═══════════════════════════════════════

    def _on_drag_enter(self, event):
        """文件拖入窗口"""
        self._dropping = True
        self._draw_drop_zone_active()

    def _on_drag_leave(self, event):
        """文件拖出窗口"""
        self._dropping = False
        self._draw_drop_zone_normal()

    def _on_drop(self, event):
        """文件松开拖入"""
        self._dropping = False
        self._draw_drop_zone_normal()

        # 解析拖入的文件路径
        files = event.data
        if not files:
            return

        # tkinterdnd2 返回的路径可能是空格分隔的列表或花括号括起的路径
        # 先尝试用 tk.splitlist 解析
        try:
            file_list = self.tk.splitlist(files)
        except Exception:
            file_list = [files]

        # 取第一个视频文件
        for f in file_list:
            f = f.strip()
            # 去掉可能的花括号
            if f.startswith('{') and f.endswith('}'):
                f = f[1:-1]
            ext = os.path.splitext(f)[1].lower()
            if ext in VIDEO_EXTS:
                self._load_video(f)
                return

        # 没有匹配的视频文件
        messagebox.showinfo('提示', '请拖入视频文件（MP4 / AVI / MOV / MKV / FLV / WMV 等）')

    # ═══════════════════════════════════════
    #  视频加载
    # ═══════════════════════════════════════

    def _load_video(self, path):
        """加载视频文件：验证、读取信息、更新 UI"""
        if not os.path.isfile(path):
            messagebox.showerror('错误', '文件不存在')
            return

        ext = os.path.splitext(path)[1].lower()
        if ext not in VIDEO_EXTS:
            messagebox.showwarning('提示', f'可能不支持的视频格式（{ext}），建议使用 MP4 / AVI / MOV 等格式')

        self._video_path = path

        # 更新文件标签
        basename = os.path.basename(path)
        self._lbl_file.config(text=f'📹  {basename}', fg=CLR_TEXT)

        # 默认前缀 = 视频文件名（去掉扩展名）
        base = os.path.splitext(basename)[0]
        self._prefix.set(base)

        # 读取视频信息
        if not self._ffmpeg_exe:
            self._set_status('⚠️ FFmpeg 不可用，无法读取视频信息', CLR_ERROR)
            self._card_frame.pack_forget()
            return

        self._video_info = _parse_video_info(path, self._ffmpeg_exe)
        if not self._video_info:
            self._lbl_file.config(text=f'⚠️  无法读取视频信息: {basename}', fg=CLR_ERROR)
            self._card_frame.pack_forget()
            self._lbl_estimate.config(text='')
            return

        # 显示信息卡片
        info = self._video_info
        self._lbl_resolution.config(text=f'{info["width"]}×{info["height"]}')
        self._lbl_fps.config(text=f'{info["fps"]} fps')
        self._lbl_frames.config(text=f'{info["total_frames"]:,}')
        mins = int(info['duration']) // 60
        secs = int(info['duration']) % 60
        self._lbl_duration.config(text=f'{mins}:{secs:02d}')

        self._card_frame.pack(fill='x', padx=24, pady=(2, 8),
                              after=self._lbl_file)

        self._update_estimate()
        self._set_status(f'已加载视频: {basename}', CLR_SUCCESS)

    def _update_estimate(self, *_):
        """根据帧间隔选项更新预估输出帧数"""
        if not self._video_info:
            self._lbl_estimate.config(text='')
            return

        interval = self._interval_var.get()
        total = self._video_info['total_frames']
        duration = self._video_info['duration']

        if interval == '每帧':
            est = total
        elif interval == '每秒1帧':
            est = int(duration) if duration > 0 else 0
        else:  # 自定义
            try:
                n = int(self._custom_n.get())
            except ValueError:
                n = 1
            est = total // n if n > 0 else total

        if interval == '每帧':
            desc = f'预计输出: 约 {est:,} 张图片（逐帧）'
        elif interval == '每秒1帧':
            desc = f'预计输出: 约 {est:,} 张图片（每秒 1 帧）'
        else:
            desc = f'预计输出: 约 {est:,} 张图片（每 {self._custom_n.get()} 帧抽 1 帧）'

        self._lbl_estimate.config(text=desc)

    def _on_interval_change(self, *_):
        """帧间隔选项变化时的联动"""
        interval = self._interval_var.get()
        if interval == '自定义':
            self._spin_n.config(state='normal')
        else:
            self._spin_n.config(state='readonly')
        self._update_estimate()

    # ═══════════════════════════════════════
    #  开始抽图
    # ═══════════════════════════════════════

    def _start(self, event=None):
        """开始抽图流程"""
        if self._running:
            return

        if not self._video_path:
            messagebox.showwarning('提示', '请先选择或拖入视频文件')
            return
        if not self._ffmpeg_exe:
            messagebox.showerror('错误',
                                 '找不到 FFmpeg。\n'
                                 '请确保 imageio-ffmpeg 已安装：\n'
                                 'pip install imageio-ffmpeg')
            return
        if not self._video_info:
            messagebox.showerror('错误', '无法读取视频信息，请检查视频文件是否完整')
            return

        # 创建输出文件夹（视频同目录下，以视频文件名命名）
        src_dir = os.path.dirname(self._video_path)
        video_name = os.path.splitext(os.path.basename(self._video_path))[0]
        out_dir = os.path.join(src_dir, video_name)
        self._output_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)

        # 计算预估输出帧数
        info = self._video_info
        interval = self._interval_var.get()
        total_src = info['total_frames']

        if interval == '每帧':
            total_output = total_src
        elif interval == '每秒1帧':
            total_output = int(info['duration']) if info['duration'] > 0 else 0
        else:
            try:
                n = int(self._custom_n.get())
            except ValueError:
                n = 1
            total_output = total_src // n if n > 0 and total_src > 0 else 0

        # 文件名模板（ffmpeg 要求正斜杠）
        ext = self._format_var.get()
        prefix = self._prefix.get().strip() or video_name
        out_pattern = os.path.join(out_dir, f'{prefix}.%05d.{ext}').replace('\\', '/')

        # 构建 ffmpeg 命令
        cmd = [self._ffmpeg_exe, '-y', '-i', self._video_path]

        if interval == '每秒1帧':
            cmd += ['-vf', 'fps=1']
        elif interval == '自定义':
            try:
                n = int(self._custom_n.get())
            except ValueError:
                n = 1
            cmd += ['-vf', f"select='not(mod(n,{n}))'", '-vsync', 'vfr']

        if ext == 'jpg':
            cmd += ['-q:v', '1']     # JPG 最高质量
        # PNG 默认无损

        cmd.append(out_pattern)

        # 更新 UI 为运行状态
        self._running = True
        self._draw_start_button_disabled()
        self._btn_start_canvas.unbind('<Enter>')
        self._btn_start_canvas.unbind('<Leave>')

        has_frame_info = total_src > 0
        if has_frame_info:
            self._progress.configure(mode='determinate', maximum=total_src, value=0)
        else:
            self._progress.configure(mode='indeterminate', maximum=100, value=0)
            self._progress.start(15)

        self._lbl_progress.config(
            text=f'预计输出: 约 {total_output} 张  |  正在处理...')
        self._set_status('⏳ 正在抽图...', CLR_PRIMARY)

        # 后台线程执行
        t = threading.Thread(
            target=self._run_ffmpeg,
            args=(cmd, out_dir, total_src),
            daemon=True,
        )
        t.start()

    def _run_ffmpeg(self, cmd, out_dir, total_src):
        """后台线程：执行 ffmpeg 并解析进度"""
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8', errors='replace',
                creationflags=creationflags,
            )

            last_frame = 0
            has_total = total_src > 0
            for line in proc.stderr:
                m = re.search(r'frame=\s*(\d+)', line)
                if m:
                    frame = int(m.group(1))
                    if frame > last_frame:
                        last_frame = frame
                        if has_total:
                            pct = min(frame * 100 // total_src, 99)
                            self._queue.put(('progress', frame, pct,
                                             f'处理第 {frame:,} / {total_src:,} 帧 ({pct}%)'))
                        else:
                            self._queue.put(('progress', frame, 0,
                                             f'已处理 {frame:,} 帧 …'))

            proc.wait()
            if proc.returncode != 0:
                raise RuntimeError(f'FFmpeg 退出码 {proc.returncode}，请检查视频文件是否损坏')

            # 统计实际输出文件数
            actual = len([
                f for f in os.listdir(out_dir)
                if os.path.isfile(os.path.join(out_dir, f))
            ])
            self._queue.put(('done', out_dir, actual))

        except Exception as e:
            self._queue.put(('error', str(e)))

    # ═══════════════════════════════════════
    #  消息轮询
    # ═══════════════════════════════════════

    def _poll_queue(self):
        """定时轮询后台线程的消息队列"""
        try:
            while True:
                msg = self._queue.get_nowait()
                kind = msg[0]

                if kind == 'progress':
                    _, frame, pct, text = msg
                    if self._progress.cget('mode') == 'indeterminate':
                        self._progress.configure(mode='determinate',
                                                 maximum=frame + 100, value=frame)
                    else:
                        self._progress['value'] = frame
                    self._lbl_progress.config(text=text)

                elif kind == 'done':
                    _, out_dir, cnt = msg
                    self._progress.stop()
                    self._progress.configure(mode='determinate', value=100, maximum=100)
                    self._lbl_progress.config(text=f'✅ 完成！共导出 {cnt:,} 张图片')

                    self._running = False
                    self._draw_start_button_normal()
                    self._bind_button_hover()
                    self._set_status('✅ 抽图完成', CLR_SUCCESS)

                    if messagebox.askyesno(
                        '完成',
                        f'抽图完成！\n共导出 {cnt:,} 张图片\n'
                        f'输出目录: {out_dir}\n\n是否打开输出文件夹？'
                    ):
                        os.startfile(out_dir)

                elif kind == 'error':
                    _, err_text = msg
                    self._progress.stop()
                    self._progress.configure(mode='determinate', value=0, maximum=100)
                    self._lbl_progress.config(text='')

                    self._running = False
                    self._draw_start_button_normal()
                    self._bind_button_hover()
                    self._set_status('❌ 抽图失败', CLR_ERROR)

                    messagebox.showerror('错误', f'抽图过程出错：\n{err_text}')

        except queue.Empty:
            pass

        self.after(200, self._poll_queue)

    def _bind_button_hover(self):
        """绑定按钮悬停事件"""
        self._btn_start_canvas.bind('<Enter>', self._draw_start_button_hover)
        self._btn_start_canvas.bind('<Leave>', self._draw_start_button_leave)

    # ═══════════════════════════════════════
    #  辅助方法
    # ═══════════════════════════════════════

    def _set_status(self, text, color=CLR_TEXT_SUBTLE):
        """更新状态栏"""
        self._lbl_status.config(text=text, fg=color)

    # ═══════════════════════════════════════
    #  退出处理
    # ═══════════════════════════════════════

    def destroy(self):
        self._running = False
        super().destroy()


# ── Canvas 绘制工具函数 ────────────────────

def _draw_rounded_rect_canvas(canvas, x1, y1, x2, y2, radius, fill_color, tag):
    """在 Canvas 上绘制圆角矩形"""
    # 主体矩形区域
    canvas.create_rectangle(
        x1 + radius, y1, x2 - radius, y2,
        fill=fill_color, outline='', tags=tag,
    )
    canvas.create_rectangle(
        x1, y1 + radius, x2, y2 - radius,
        fill=fill_color, outline='', tags=tag,
    )
    # 四个角弧形
    d = radius * 2
    canvas.create_oval(x1, y1, x1 + d, y1 + d, fill=fill_color, outline='', tags=tag)
    canvas.create_oval(x2 - d, y1, x2, y1 + d, fill=fill_color, outline='', tags=tag)
    canvas.create_oval(x1, y2 - d, x1 + d, y2, fill=fill_color, outline='', tags=tag)
    canvas.create_oval(x2 - d, y2, x2, y2 - d, fill=fill_color, outline='', tags=tag)


# ── 入口 ──────────────────────────────────

if __name__ == '__main__':
    app = App()

    # 绑定按钮悬停效果（放在 app 创建之后，因为需要引用实例方法）
    app._bind_button_hover()

    app.mainloop()
