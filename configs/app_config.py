"""
应用配置中心 — 集中管理所有常量与配置参数。
所有模块从此处导入配置值，确保一致性。
"""

from __future__ import annotations

from pathlib import Path


# ─── 应用信息 ───
APP_NAME = "CS Video Player"
APP_VERSION = "2.0.0"

# ─── 窗口默认值 ───
WINDOW_DEFAULT_WIDTH = 1280
WINDOW_DEFAULT_HEIGHT = 800
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 600

# ─── 数据文件路径 ───
APP_DATA_DIR = Path.home() / ".cs_video_player"
RECENTS_FILE = APP_DATA_DIR / "recents.json"
SETTINGS_FILE = APP_DATA_DIR / "settings.json"
PLAYBACK_STATE_FILE = APP_DATA_DIR / "playback_state.json"
SESSION_FILE = APP_DATA_DIR / "session.json"

# ─── 播放列表 ───
MAX_RECENTS = 30
MAX_PLAYLIST = 500

# ─── 支持的视频格式 ───
VIDEO_EXTENSIONS = frozenset({
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
    ".webm", ".m4v", ".mpg", ".mpeg", ".ts", ".3gp",
    ".m2ts", ".vob", ".ogv", ".rm", ".rmvb", ".mts",
    ".divx", ".asf", ".f4v", ".svq3", ".amv",
})

# ─── 倍速档位 ───
PLAYBACK_SPEEDS = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 3.0, 4.0, 8.0, 16.0)
SPEED_MIN = 0.25
SPEED_MAX = 16.0
DEFAULT_SPEED = 1.0
DEFAULT_VOLUME = 100.0

# ─── 快进/快退步长（毫秒）───
SEEK_STEP_SHORT = 10_000      # ←/→  10秒（Shift 加倍为 20秒）

# ─── 音量步长 ───
VOLUME_STEP = 5.0
VOLUME_WHEEL_STEP = 5.0

# ─── 排序选项 ───
SORT_KEYS = ("default", "name", "size", "date")
SORT_LABELS = {
    "default": "默认",
    "name": "名称",
    "size": "大小",
    "date": "日期",
}

# ─── 侧边栏 ───
SIDEBAR_DEFAULT_WIDTH = 280
SIDEBAR_MIN_WIDTH = 200
SIDEBAR_MAX_WIDTH = 440
SIDEBAR_WIDTH = SIDEBAR_DEFAULT_WIDTH
SIDEBAR_COLLAPSED_WIDTH = 0
SIDEBAR_DEFAULT_VISIBLE = True

# ─── 鼠标自动隐藏控制栏（毫秒）───
CONTROLS_AUTO_HIDE_MS = 3000

# ─── 位置轮询间隔（毫秒）───
POSITION_POLL_INTERVAL_MS = 500

# ─── 键盘快捷键映射（无修饰键的单键）───
KEYBOARD_SHORTCUTS = {
    "space": "play_pause",
    " ": "play_pause",
    "left": "seek_backward",
    "right": "seek_forward",
    "up": "volume_up",
    "down": "volume_down",
    "[": "speed_down",
    "]": "speed_up",
    "m": "toggle_mute",
    "f": "toggle_fullscreen",
    "f11": "toggle_fullscreen",
    "n": "next_track",
    "p": "prev_track",
    "s": "stop",
    "t": "toggle_remaining_time",
    "escape": "exit_fullscreen",
    "delete": "remove_current",
}
