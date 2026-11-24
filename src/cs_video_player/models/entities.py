"""models / entities —— 不可变数据实体与跨层消息。

实体只有数据与序列化，不含行为编排：Service 负责组装，ViewModel 负责投影，
View 负责渲染。所有类型都可在没有 UI 环境的情况下构造与断言。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from cs_video_player.models.enums import FileRequestKind, NoticeTone, PlayMode


@dataclass(frozen=True, slots=True)
class PlaylistItem:
    """播放列表中的一项本地视频。"""

    path: str
    title: str
    size: int = 0
    modified: datetime | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """会话落盘格式（datetime 转 ISO 字符串）。"""
        return {
            "path": self.path,
            "title": self.title,
            "size": self.size,
            "modified": self.modified.isoformat() if self.modified else None,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """从落盘格式还原；脏字段一律降级为默认值，不让会话恢复崩掉。"""
        modified: str | None = data.get("modified")
        return cls(
            path=str(data.get("path", "")),
            title=str(data.get("title", "")),
            size=int(data.get("size", 0) or 0),
            modified=datetime.fromisoformat(modified) if modified else None,
            duration_ms=int(data.get("duration_ms", 0) or 0),
        )


@dataclass(frozen=True, slots=True)
class MediaTrack:
    """投喂给原生播放器的轨道（URI 已由基础设施层转换）。"""

    uri: str


@dataclass(frozen=True, slots=True)
class SessionCandidate:
    """启动时的会话恢复候选（ViewModel 展示确认框后决定是否恢复）。"""

    items: tuple[PlaylistItem, ...]
    index: int
    position_ms: int
    mode: PlayMode


@dataclass(frozen=True, slots=True)
class Notice:
    """一次性用户回执。nonce 变化即视为「新消息」，避免同一条被重复弹出。"""

    message: str
    tone: NoticeTone = NoticeTone.INFO
    nonce: int = 0
    duration_ms: int = 4000


@dataclass(frozen=True, slots=True)
class KeyInfo:
    """View 从平台按键事件抽出的纯数据，ViewModel 不需要认识 Flet。"""

    key: str
    ctrl: bool = False
    shift: bool = False


@dataclass(frozen=True, slots=True)
class FileRequest:
    """ViewModel 请求 View 弹出文件对话框；nonce 区分两次相同请求。"""

    kind: FileRequestKind
    nonce: int = 0
