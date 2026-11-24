"""模型层 —— 数据结构、枚举、常量。无业务逻辑，所有层均可依赖。

唯一依赖方向：``models`` 不 import 本项目的任何其他包。
"""

from cs_video_player.models.config import (
    APP_DATA_DIR,
    APP_NAME,
    APP_VERSION,
    CONTROLS_AUTO_HIDE_MS,
    DEFAULT_SPEED,
    DEFAULT_VOLUME,
    KEYBOARD_SHORTCUTS,
    MAX_PLAYLIST,
    MAX_RECENTS,
    PLAYBACK_SPEEDS,
    SEEK_STEP_SHORT,
    SIDEBAR_DEFAULT_VISIBLE,
    SIDEBAR_DEFAULT_WIDTH,
    SPEED_MAX,
    SPEED_MIN,
    VIDEO_EXTENSIONS,
    VOLUME_STEP,
    VOLUME_WHEEL_STEP,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from cs_video_player.models.entities import (
    FileRequest,
    KeyInfo,
    MediaTrack,
    Notice,
    PlaylistItem,
    SessionCandidate,
)
from cs_video_player.models.enums import (
    FileRequestKind,
    ListMode,
    NoticeTone,
    PlayMode,
    SortKey,
)
from cs_video_player.models.state import AppState, PlaybackState

__all__ = [
    "APP_DATA_DIR", "APP_NAME", "APP_VERSION", "CONTROLS_AUTO_HIDE_MS",
    "DEFAULT_SPEED", "DEFAULT_VOLUME", "KEYBOARD_SHORTCUTS", "MAX_PLAYLIST",
    "MAX_RECENTS", "PLAYBACK_SPEEDS", "SEEK_STEP_SHORT", "SIDEBAR_DEFAULT_VISIBLE",
    "SIDEBAR_DEFAULT_WIDTH", "SPEED_MAX", "SPEED_MIN", "VIDEO_EXTENSIONS",
    "VOLUME_STEP", "VOLUME_WHEEL_STEP", "WINDOW_DEFAULT_HEIGHT",
    "WINDOW_DEFAULT_WIDTH", "WINDOW_MIN_HEIGHT", "WINDOW_MIN_WIDTH",
    "AppState", "FileRequest", "FileRequestKind", "KeyInfo", "ListMode",
    "MediaTrack", "Notice", "NoticeTone", "PlaybackState", "PlaylistItem",
    "PlayMode", "SessionCandidate", "SortKey",
]
