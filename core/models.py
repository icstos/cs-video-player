"""
数据模型定义。
使用 dataclass 保存播放列表项、播放器状态和视图相关枚举。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PlayMode(Enum):
    """播放模式。"""

    SEQUENCE = "sequence"
    REPEAT_ALL = "repeat_all"
    REPEAT_ONE = "repeat_one"
    SHUFFLE = "shuffle"

    @property
    def label(self) -> str:
        return {
            PlayMode.SEQUENCE: "顺序播放",
            PlayMode.REPEAT_ALL: "列表循环",
            PlayMode.REPEAT_ONE: "单曲循环",
            PlayMode.SHUFFLE: "随机播放",
        }[self]


class SortKey(Enum):
    """播放列表排序方式。"""

    DEFAULT = "default"
    NAME = "name"
    SIZE = "size"
    DATE = "date"

    @property
    def label(self) -> str:
        return {
            SortKey.DEFAULT: "默认",
            SortKey.NAME: "名称",
            SortKey.SIZE: "大小",
            SortKey.DATE: "日期",
        }[self]


@dataclass(slots=True)
class PlaylistItem:
    """播放列表中的单个视频项。"""

    path: str
    title: str
    size: int = 0
    modified: Optional[datetime] = None
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "title": self.title,
            "size": self.size,
            "modified": self.modified.isoformat() if self.modified else None,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlaylistItem":
        modified = data.get("modified")
        return cls(
            path=str(data.get("path", "")),
            title=str(data.get("title", "")),
            size=int(data.get("size", 0) or 0),
            modified=datetime.fromisoformat(modified) if modified else None,
            duration_ms=int(data.get("duration_ms", 0) or 0),
        )


@dataclass(slots=True)
class PlayerState:
    """播放器状态快照，作为 UI 的单一数据源。"""

    playlist: list[PlaylistItem] = field(default_factory=list)
    current_index: int = 0
    is_playing: bool = False
    position_ms: int = 0
    duration_ms: int = 0
    volume: float = 100.0
    playback_rate: float = 1.0
    muted: bool = False
    is_fullscreen: bool = False
    play_mode: PlayMode = PlayMode.SEQUENCE
    sidebar_width: float = 320.0
    show_controls: bool = True
    last_error: str = ""
    subtitle_track: str = ""
    recent_folder: str = ""
    loop_selection: bool = False
    pending_restore_pos: int = 0

    @property
    def has_media(self) -> bool:
        return 0 <= self.current_index < len(self.playlist)

    @property
    def has_video(self) -> bool:
        return self.has_media

    @property
    def current_item(self) -> Optional[PlaylistItem]:
        return self.playlist[self.current_index] if self.has_media else None

    @property
    def has_next(self) -> bool:
        return self.current_index < len(self.playlist) - 1

    @property
    def has_prev(self) -> bool:
        return self.current_index > 0

    @property
    def progress(self) -> float:
        if self.duration_ms <= 0:
            return 0.0
        return min(1.0, max(0.0, self.position_ms / self.duration_ms))
