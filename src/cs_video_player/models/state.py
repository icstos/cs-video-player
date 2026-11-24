"""models / state —— UI 的唯一事实源（声明式 UI = f(AppState)）。

分两段：

* :class:`PlaybackState` 是 Service 的业务快照，不含任何 UI 交互态；
* :class:`AppState` 由 ViewModel 在业务快照上叠加 UI 交互态（侧栏可见、
  拖动中、对话框请求……），两段的字段合并后仍是**扁平**的只读快照。

所有字段都是 ``frozen + slots``：事件回调拿到的是某一帧的不可变快照，
不会被后续状态更新偷偷改写；重渲染只需比较字段值，不需要深拷贝。
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from cs_video_player.models.config import (
    DEFAULT_SPEED,
    DEFAULT_VOLUME,
    SIDEBAR_DEFAULT_VISIBLE,
    SIDEBAR_DEFAULT_WIDTH,
)
from cs_video_player.models.entities import (
    FileRequest,
    MediaTrack,
    Notice,
    PlaylistItem,
    SessionCandidate,
)
from cs_video_player.models.enums import ListMode, PlayMode, SortKey


@dataclass(frozen=True, slots=True)
class PlaybackState:
    """业务状态快照：Service 维护，ViewModel 按帧取用。"""

    playlist: tuple[PlaylistItem, ...] = ()
    current_index: int = 0
    is_playing: bool = False
    position_ms: int = 0
    duration_ms: int = 0
    volume: float = DEFAULT_VOLUME
    playback_rate: float = DEFAULT_SPEED
    muted: bool = False
    is_fullscreen: bool = False
    play_mode: PlayMode = PlayMode.SEQUENCE
    sidebar_width: float = SIDEBAR_DEFAULT_WIDTH
    show_remaining_time: bool = False
    # 兼容旧状态字段：仍保留在数据契约中，当前业务未消费。
    subtitle_track: str = ""
    recent_folder: str = ""
    loop_selection: bool = False
    last_error: str = ""
    pending_restore_pos: int = 0
    recents: tuple[str, ...] = ()
    sort_key: SortKey = SortKey.DEFAULT
    play_nonce: int = 0
    #: 业务规则投影出的原生播放列表；View 只把它翻译成控件数据。
    native_playlist: tuple[MediaTrack, ...] = ()
    native_mode: ListMode = ListMode.NONE
    #: 一次性回执与启动会话候选（都由 View 声明式消费）。
    notice: Notice | None = None
    session: SessionCandidate | None = None

    @property
    def has_media(self) -> bool:
        """索引是否落在有效轨道上。"""
        return 0 <= self.current_index < len(self.playlist)

    @property
    def has_video(self) -> bool:
        """画面区是否有视频可显示。"""
        return self.has_media

    @property
    def current_item(self) -> PlaylistItem | None:
        """当前轨道；空列表返回 None。"""
        return self.playlist[self.current_index] if self.has_media else None

    @property
    def has_next(self) -> bool:
        """是否还有下一条（顺序模式到末尾不回卷）。"""
        return self.current_index < len(self.playlist) - 1

    @property
    def has_prev(self) -> bool:
        """是否还有上一条。"""
        return self.current_index > 0

    @property
    def progress(self) -> float:
        """0.0 ~ 1.0 的播放进度；时长未知时为 0。"""
        if self.duration_ms <= 0:
            return 0.0
        return min(1.0, max(0.0, self.position_ms / self.duration_ms))

    @property
    def title(self) -> str:
        """窗口标题用的片名（无媒体时回落到应用名）。"""
        return self.current_item.title if self.has_video else ""


@dataclass(frozen=True, slots=True)
class AppState(PlaybackState):
    """ViewModel 的完整快照：业务数据 + UI 交互态。"""

    sidebar_visible: bool = SIDEBAR_DEFAULT_VISIBLE
    controls_visible: bool = True
    is_seeking: bool = False
    seek_preview_ms: int = 0
    file_request: FileRequest | None = None

    @classmethod
    def from_playback(cls, playback: PlaybackState, **ui_fields: object) -> AppState:
        """在业务快照上叠加 UI 字段，生成新一帧。"""
        values: dict[str, object] = {
            field.name: getattr(playback, field.name)
            for field in fields(PlaybackState)
        }
        values.update(ui_fields)
        return cls(**values)
