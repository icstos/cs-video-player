"""models / config —— 全应用唯一的常量事实源。

纯数据：只依赖标准库，任何层都可引用。把常量放在模型层而不是各业务模块里，
是为了让「窗口尺寸」「快捷键」「支持格式」这类既有产品决策既能被 View 渲染，
也能被 Service 编排，却不引入对 UI 框架的依赖。
"""

from __future__ import annotations

from pathlib import Path

# ─── 应用信息 ───
APP_NAME: str = "CS Video Player"
APP_VERSION: str = "2.0.0"

# ─── 窗口默认值 ───
WINDOW_DEFAULT_WIDTH: int = 1280
WINDOW_DEFAULT_HEIGHT: int = 800
WINDOW_MIN_WIDTH: int = 960
WINDOW_MIN_HEIGHT: int = 600

# ─── 数据文件路径 ───
APP_DATA_DIR: Path = Path.home() / ".cs_video_player"
RECENTS_FILE: Path = APP_DATA_DIR / "recents.json"
SETTINGS_FILE: Path = APP_DATA_DIR / "settings.json"
PLAYBACK_STATE_FILE: Path = APP_DATA_DIR / "playback_state.json"
SESSION_FILE: Path = APP_DATA_DIR / "session.json"

# ─── 播放列表 ───
MAX_RECENTS: int = 30
MAX_PLAYLIST: int = 500

# ─── 支持的视频格式 ───
VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
        ".webm", ".m4v", ".mpg", ".mpeg", ".ts", ".3gp",
        ".m2ts", ".vob", ".ogv", ".rm", ".rmvb", ".mts",
        ".divx", ".asf", ".f4v", ".svq3", ".amv",
    }
)

# ─── 倍速与音量 ───
PLAYBACK_SPEEDS: tuple[float, ...] = (
    0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 3.0, 4.0, 8.0, 16.0,
)
SPEED_MIN: float = 0.25
SPEED_MAX: float = 16.0
DEFAULT_SPEED: float = 1.0
DEFAULT_VOLUME: float = 100.0
VOLUME_STEP: float = 5.0
VOLUME_WHEEL_STEP: float = 5.0

# ─── 跳转步长（毫秒） ───
SEEK_STEP_SHORT: int = 10_000

# ─── 侧栏 ───
SIDEBAR_DEFAULT_WIDTH: int = 280
SIDEBAR_MIN_WIDTH: int = 200
SIDEBAR_MAX_WIDTH: int = 440
SIDEBAR_DEFAULT_VISIBLE: bool = True

# ─── 交互时序（毫秒） ───
CONTROLS_AUTO_HIDE_MS: int = 3000
POSITION_POLL_INTERVAL_MS: int = 500

# ─── 快捷键：单键 → 语义动作 ───
KEYBOARD_SHORTCUTS: dict[str, str] = {
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
