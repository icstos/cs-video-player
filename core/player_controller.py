"""
播放控制器 — 连接 VideoEngine 与 UI 状态的桥梁层。
维护播放器状态，通过回调通知 UI 层状态变更。
"""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Callable, List

from configs.app_config import DEFAULT_SPEED, DEFAULT_VOLUME, MAX_PLAYLIST
from core.models import PlayMode, PlaylistItem, PlayerState, SortKey
from core.video_engine import VideoEngine
from utils.storage import StorageManager

logger = logging.getLogger(__name__)

StateCallback = Callable[[PlayerState], None]


class PlayerController:
    """
    播放控制器。
    维护播放器状态（播放列表、索引、播放模式等），
    通过回调通知 UI 层状态变更。
    """

    def __init__(self) -> None:
        self._state = PlayerState(
            volume=DEFAULT_VOLUME,
            playback_rate=DEFAULT_SPEED,
        )
        self._engine = VideoEngine()
        self._recents: List[str] = StorageManager.load_recents()
        self._sort_key: SortKey = SortKey.DEFAULT
        self._listeners: List[StateCallback] = []
        self._play_nonce = 0

    # ─── 属性 ───

    @property
    def state(self) -> PlayerState:
        return self._state

    @property
    def engine(self) -> VideoEngine:
        return self._engine

    @property
    def recents(self) -> List[str]:
        return self._recents

    @property
    def sort_key(self) -> SortKey:
        return self._sort_key

    @property
    def play_nonce(self) -> int:
        return self._play_nonce

    # ─── 事件订阅 ───

    def add_listener(self, callback: StateCallback) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for cb in self._listeners:
            try:
                cb(self._state)
            except Exception as exc:
                logger.exception("状态回调异常: %s", exc)

    # ─── 播放列表管理 ───

    def set_playlist(self, items: List[PlaylistItem]) -> None:
        self._state.playlist = items
        self._state.current_index = 0
        self._state.position_ms = 0
        self._state.duration_ms = 0
        self._state.is_playing = False
        self._play_nonce += 1
        if items:
            self._add_recent(items[0].path)
        self._notify()

    def add_files(self, items: List[PlaylistItem], replace: bool = False) -> None:
        """批量添加文件到播放列表。replace=True 时替换整个列表。"""
        if not items:
            return
        if replace or not self._state.playlist:
            self._state.playlist = list(items)
            self._state.current_index = 0
            self._state.position_ms = 0
            self._state.duration_ms = 0
            self._state.is_playing = False
            self._add_recent(items[0].path)
        else:
            existing_paths = {item.path for item in self._state.playlist}
            for item in items:
                if item.path not in existing_paths and len(self._state.playlist) < MAX_PLAYLIST:
                    self._state.playlist.append(item)
                    existing_paths.add(item.path)
            self._add_recent(items[0].path)
        self._play_nonce += 1
        self._notify()

    def add_to_playlist(self, item: PlaylistItem) -> None:
        self._state.playlist.append(item)
        self._add_recent(item.path)
        self._notify()

    def insert_to_playlist(self, index: int, item: PlaylistItem) -> None:
        self._state.playlist.insert(index, item)
        self._add_recent(item.path)
        self._notify()

    def remove_from_playlist(self, index: int) -> None:
        if not self._state.playlist or index < 0 or index >= len(self._state.playlist):
            return
        self._state.playlist.pop(index)
        if index < self._state.current_index:
            self._state.current_index -= 1
        elif index == self._state.current_index:
            if self._state.playlist:
                self._state.current_index = min(
                    self._state.current_index,
                    len(self._state.playlist) - 1,
                )
                self._play_nonce += 1
            else:
                self._state.current_index = 0
                self._state.is_playing = False
        self._notify()

    def clear_playlist(self) -> None:
        self._state.playlist = []
        self._state.current_index = 0
        self._state.is_playing = False
        self._state.position_ms = 0
        self._state.duration_ms = 0
        self._notify()

    def move_item(self, from_idx: int, to_idx: int) -> None:
        if (
            not self._state.playlist
            or from_idx < 0
            or from_idx >= len(self._state.playlist)
            or to_idx < 0
            or to_idx >= len(self._state.playlist)
        ):
            return
        item = self._state.playlist.pop(from_idx)
        self._state.playlist.insert(to_idx, item)
        if self._state.current_index == from_idx:
            self._state.current_index = to_idx
        elif from_idx < self._state.current_index <= to_idx:
            self._state.current_index -= 1
        elif to_idx <= self._state.current_index < from_idx:
            self._state.current_index += 1
        self._notify()

    def reorder(self, from_idx: int, to_idx: int) -> None:
        """拖拽排序：将 from_idx 项移动到 to_idx 位置（排序后的目标索引）。"""
        self.move_item(from_idx, to_idx)

    def remove_current(self) -> None:
        """移除当前正在播放的项。"""
        self.remove_from_playlist(self._state.current_index)

    # ─── 播放控制 ───

    def play_at(self, index: int) -> None:
        if not self._state.playlist or index < 0 or index >= len(self._state.playlist):
            return
        self._state.current_index = index
        self._state.position_ms = 0
        self._state.duration_ms = 0
        self._state.is_playing = False
        self._play_nonce += 1
        self._add_recent(self._state.playlist[index].path)
        self._notify()

    def play_next(self) -> None:
        if not self._state.has_next:
            if self._state.play_mode == PlayMode.REPEAT_ALL and self._state.playlist:
                self.play_at(0)
            return
        self.play_at(self._state.current_index + 1)

    def play_prev(self) -> None:
        if not self._state.has_prev:
            return
        self.play_at(self._state.current_index - 1)

    def play_first(self) -> None:
        if self._state.playlist:
            self.play_at(0)

    def stop(self) -> None:
        """停止播放并重置位置。"""
        self._state.is_playing = False
        self._state.position_ms = 0
        self._notify()

    def play_last(self) -> None:
        if self._state.playlist:
            self.play_at(len(self._state.playlist) - 1)

    def play_random(self) -> None:
        if self._state.playlist:
            idx = random.randint(0, len(self._state.playlist) - 1)
            self.play_at(idx)

    # ─── 播放模式 ───

    def cycle_play_mode(self) -> None:
        modes = list(PlayMode)
        current_idx = modes.index(self._state.play_mode)
        self._state.play_mode = modes[(current_idx + 1) % len(modes)]
        if self._state.has_media:
            self._engine.pending_restore = (
                self._state.position_ms,
                self._state.is_playing,
            )
        self._play_nonce += 1
        self._notify()

    def set_play_mode(self, mode: PlayMode) -> None:
        self._state.play_mode = mode
        if self._state.has_media:
            self._engine.pending_restore = (
                self._state.position_ms,
                self._state.is_playing,
            )
        self._play_nonce += 1
        self._notify()

    # ─── 状态更新（由 Video 事件回调触发）───

    def update_position(self, ms: int) -> None:
        if self._engine.is_seeking:
            return
        self._state.position_ms = ms

    def update_duration(self, ms: int) -> None:
        self._state.duration_ms = ms

    def set_playing(self, playing: bool) -> None:
        self._state.is_playing = playing
        self._notify()

    def toggle_playing(self) -> None:
        self._state.is_playing = not self._state.is_playing
        self._notify()

    def set_volume(self, volume: float) -> None:
        self._state.volume = max(0.0, min(100.0, volume))
        if self._state.volume > 0:
            self._state.muted = False
        self._notify()

    def set_playback_rate(self, rate: float) -> None:
        self._state.playback_rate = rate
        self._notify()

    def toggle_mute(self) -> None:
        self._state.muted = not self._state.muted
        self._notify()

    def toggle_remaining_time(self) -> None:
        """切换时间显示模式：当前时间 / 剩余时间。"""
        self._state.show_remaining_time = not self._state.show_remaining_time
        self._notify()

    def set_fullscreen(self, fullscreen: bool) -> None:
        self._state.is_fullscreen = fullscreen
        self._notify()

    def toggle_fullscreen(self) -> None:
        self.set_fullscreen(not self._state.is_fullscreen)

    def set_show_controls(self, visible: bool) -> None:
        self._state.show_controls = visible
        self._notify()

    def toggle_controls(self) -> None:
        self._state.show_controls = not self._state.show_controls
        self._notify()

    def set_sidebar_width(self, width: float) -> None:
        self._state.sidebar_width = width
        self._notify()

    def set_error(self, error: str) -> None:
        self._state.last_error = error
        self._notify()

    def clear_error(self) -> None:
        self._state.last_error = ""
        self._notify()

    def on_track_change(self, index: int) -> None:
        if self._state.play_mode == PlayMode.REPEAT_ONE:
            return
        if 0 <= index < len(self._state.playlist):
            self._state.current_index = index
            self._state.position_ms = 0
            self._notify()

    def on_complete(self) -> None:
        mode = self._state.play_mode
        if mode == PlayMode.REPEAT_ONE:
            self._play_nonce += 1
            self._state.is_playing = True
            self._notify()
        elif mode == PlayMode.SHUFFLE:
            if len(self._state.playlist) > 1:
                idx = random.randint(0, len(self._state.playlist) - 1)
                self.play_at(idx)
        elif self._state.has_next:
            self.play_next()
        elif mode == PlayMode.REPEAT_ALL and self._state.playlist:
            self.play_at(0)
        else:
            self._state.is_playing = False
            self._notify()

    # ─── 排序 ───

    def set_sort_key(self, key: SortKey) -> None:
        self._sort_key = key
        self._notify()

    def get_sorted_playlist(self) -> List[tuple[int, PlaylistItem]]:
        items = list(enumerate(self._state.playlist))
        if self._sort_key == SortKey.NAME:
            items.sort(key=lambda x: x[1].title.lower())
        elif self._sort_key == SortKey.SIZE:
            items.sort(key=lambda x: x[1].size, reverse=True)
        elif self._sort_key == SortKey.DATE:
            items.sort(
                key=lambda x: x[1].modified or datetime.min,
                reverse=True,
            )
        return items

    # ─── 近期记录 ───

    def _add_recent(self, path: str) -> None:
        self._recents = StorageManager.add_recent(path, self._recents)
        StorageManager.save_recents(self._recents)

    def play_recent(self, path: str) -> None:
        from utils.file_scanner import make_playlist_item

        item = make_playlist_item(path)
        self.set_playlist([item])

    def remove_recent(self, path: str) -> None:
        self._recents = [r for r in self._recents if r != path]
        StorageManager.save_recents(self._recents)

    def clear_recents(self) -> None:
        self._recents.clear()
        StorageManager.save_recents([])

    # ─── 设置持久化 ───

    def save_settings(self) -> None:
        StorageManager.set_setting("volume", self._state.volume)
        StorageManager.set_setting("playback_rate", self._state.playback_rate)
        StorageManager.set_setting("play_mode", self._state.play_mode.value)
        StorageManager.set_setting("sidebar_width", self._state.sidebar_width)
        StorageManager.set_setting("show_remaining_time", self._state.show_remaining_time)

    def load_settings(self) -> None:
        volume = StorageManager.get_setting("volume")
        if isinstance(volume, (int, float)):
            self._state.volume = float(volume)

        rate = StorageManager.get_setting("playback_rate")
        if isinstance(rate, (int, float)):
            self._state.playback_rate = float(rate)

        mode_val = StorageManager.get_setting("play_mode")
        if isinstance(mode_val, str):
            try:
                self._state.play_mode = PlayMode(mode_val)
            except ValueError:
                pass

        width = StorageManager.get_setting("sidebar_width")
        if isinstance(width, (int, float)):
            self._state.sidebar_width = float(width)

        show_remaining = StorageManager.get_setting("show_remaining_time")
        if isinstance(show_remaining, bool):
            self._state.show_remaining_time = show_remaining

        self._notify()

    # ─── 会话恢复 ───

    def get_saved_session(self) -> tuple[list[PlaylistItem], int, int, PlayMode] | None:
        """读取上次关闭时保存的播放列表与进度。返回 (playlist, index, pos, mode) 或 None。"""
        data = StorageManager.load_session()
        raw = data.get("playlist")
        if not isinstance(raw, list) or not raw:
            return None
        items: list[PlaylistItem] = []
        for entry in raw:
            if isinstance(entry, dict):
                try:
                    items.append(PlaylistItem.from_dict(entry))
                except Exception:
                    pass
        if not items:
            return None
        idx = max(0, min(int(data.get("current_index", 0)), len(items) - 1))
        pos = max(0, int(data.get("position_ms", 0)))
        mode_val = data.get("play_mode", "sequence")
        try:
            mode = PlayMode(mode_val)
        except ValueError:
            mode = PlayMode.SEQUENCE
        return items, idx, pos, mode

    def restore_session(
        self, items: list[PlaylistItem], index: int, pos: int, mode: PlayMode
    ) -> None:
        """恢复上次会话的播放列表，设置播放位置但不自动播放。"""
        self._state.playlist = items
        self._state.current_index = index
        self._state.play_mode = mode
        self._state.position_ms = 0
        self._state.duration_ms = 0
        self._state.is_playing = False
        self._state.pending_restore_pos = pos
        self._play_nonce += 1
        if items:
            self._add_recent(items[index].path)
        self._notify()

    def save_session(self) -> None:
        """保存当前播放列表与进度，供下次启动恢复。"""
        if not self._state.playlist:
            StorageManager.clear_session()
            return
        playlist_data = [item.to_dict() for item in self._state.playlist]
        StorageManager.save_session(
            playlist=playlist_data,
            current_index=self._state.current_index,
            position_ms=self._state.position_ms,
            play_mode=self._state.play_mode.value,
        )
