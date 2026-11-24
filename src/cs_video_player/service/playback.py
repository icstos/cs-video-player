"""service / playback —— 播放业务编排（本应用的领域层）。

职责边界：

* 维护 :class:`~models.state.PlaybackState` 这一份业务快照；
* 通过 ``MediaPort`` / ``PreferencesPort`` / ``ScannerPort`` 抽象完成副作用；
* 不认识 Flet、cs-ui、``flet_video``，也不决定任何控件怎么画。

所有公开命令都是「更新状态 + 必要时下发端口命令」，ViewModel 只调用这些方法，
拿到的是新一帧只读快照。异步命令由 ViewModel 调度，Service 自身不创建任务。
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import replace as _replace
from typing import cast

from cs_video_player.infra.ports import (
    ErrorHandler,
    MediaPort,
    PreferencesPort,
    ScannerPort,
    VideoControl,
)
from cs_video_player.models.config import (
    DEFAULT_SPEED,
    DEFAULT_VOLUME,
    MAX_PLAYLIST,
)
from cs_video_player.models.entities import Notice, PlaylistItem, SessionCandidate
from cs_video_player.models.enums import NoticeTone, PlayMode, SortKey
from cs_video_player.models.state import PlaybackState
from cs_video_player.service import rules

logger = logging.getLogger(__name__)

Listener = Callable[[], None]


class PlaybackService:
    """播放会话的业务边界：状态机 + 端口编排。"""

    def __init__(
        self,
        *,
        media: MediaPort,
        preferences: PreferencesPort,
        scanner: ScannerPort,
    ) -> None:
        self._media: MediaPort = media
        self._prefs: PreferencesPort = preferences
        self._scanner: ScannerPort = scanner
        self._state: PlaybackState = PlaybackState(
            volume=DEFAULT_VOLUME, playback_rate=DEFAULT_SPEED
        )
        self._listeners: list[Listener] = []
        self._play_nonce: int = 0
        self._notice_nonce: int = 0
        self._pending_restore: tuple[int, bool] | None = None
        handler: ErrorHandler = self._on_media_error
        self._media.set_error_handler(handler)

    # ─── 状态与订阅 ───

    def bind_media(self, control: object | None) -> None:
        """由 View 注入原生播放器句柄（Service 内部收敛为端口协议）。"""
        self._media.bind_control(
            cast(VideoControl, control) if control is not None else None
        )

    @property
    def state(self) -> PlaybackState:
        """当前业务快照（只读）。"""
        return self._state

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """订阅状态变化，返回退订函数。"""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def _notify(self) -> None:
        for callback in tuple(self._listeners):
            try:
                callback()
            except Exception as exc:
                logger.exception("业务状态回执失败: %s", exc)

    def _commit(self, *, reproject: bool = False, **changes: object) -> None:
        """生成新一帧业务快照；reproject=True 时同步重算原生播放列表。"""
        if reproject:
            playlist = changes.get("playlist", self._state.playlist)
            mode = changes.get("play_mode", self._state.play_mode)
            index = changes.get("current_index", self._state.current_index)
            assert isinstance(playlist, tuple)
            assert isinstance(mode, PlayMode)
            assert isinstance(index, int)
            changes["native_playlist"] = rules.project_playlist(
                playlist, mode, index, self._scanner.to_uri
            )
            changes["native_mode"] = rules.list_mode_for(mode)
        self._state = _replace(self._state, **changes)
        self._notify()

    def _bump_play(self) -> int:
        self._play_nonce += 1
        return self._play_nonce

    def notice(self, message: str, tone: NoticeTone = NoticeTone.INFO) -> None:
        """发一条一次性回执（nonce 变化即新消息）。"""
        self._notice_nonce += 1
        self._commit(
            notice=Notice(message, tone, self._notice_nonce),
            last_error=message if tone == NoticeTone.ERROR else self._state.last_error,
        )

    def clear_notice(self) -> None:
        """View 已消费回执后清空，避免重复弹出。"""
        if self._state.notice is not None:
            self._commit(notice=None, last_error="")

    def clear_error(self) -> None:
        """兼容旧调用点：清空错误文案。"""
        if self._state.last_error:
            self._commit(last_error="")

    def _on_media_error(self, label: str, raw_error: str) -> None:
        """底层错误回执：分类 + 通知，不让异常穿透到事件循环。"""
        friendly: str = rules.classify_error(raw_error)
        logger.error("播放器错误 [%s]: %s → %s", label, raw_error, friendly)
        self.notice(friendly, NoticeTone.ERROR)

    # ─── 启动与会话 ───

    def load_settings(self) -> None:
        """读取持久化设置（磁盘异常由端口降级）。"""
        volume = self._prefs.get_setting("volume", DEFAULT_VOLUME)
        rate = self._prefs.get_setting("playback_rate", DEFAULT_SPEED)
        mode_value = self._prefs.get_setting("play_mode", PlayMode.SEQUENCE.value)
        width = self._prefs.get_setting("sidebar_width", float(self._state.sidebar_width))
        remaining = self._prefs.get_setting(
            "show_remaining_time", self._state.show_remaining_time
        )
        try:
            mode = PlayMode(str(mode_value))
        except ValueError:
            mode = PlayMode.SEQUENCE
        self._commit(
            volume=rules.clamp_volume(float(volume)),
            playback_rate=float(rate),
            play_mode=mode,
            sidebar_width=float(width),
            show_remaining_time=bool(remaining),
            recents=self._prefs.load_recents(),
            reproject=True,
        )

    def peek_session(self) -> None:
        """启动时探测上次会话，交给 ViewModel 展示恢复确认。"""
        data = self._prefs.load_session()
        raw = data.get("playlist")
        if not isinstance(raw, list) or not raw:
            return
        items: list[PlaylistItem] = []
        for entry in raw:
            if isinstance(entry, dict):
                try:
                    items.append(PlaylistItem.from_dict(entry))
                except Exception:
                    continue
        if not items:
            return
        try:
            index = max(0, min(int(data.get("current_index", 0)), len(items) - 1))
            pos = max(0, int(data.get("position_ms", 0)))
        except (TypeError, ValueError):
            index, pos = 0, 0
        try:
            mode = PlayMode(str(data.get("play_mode", PlayMode.SEQUENCE.value)))
        except ValueError:
            mode = PlayMode.SEQUENCE
        self._commit(
            session=SessionCandidate(tuple(items), index, pos, mode),
        )

    def restore_session(self) -> None:
        """确认恢复：写入列表与进度，等待画面加载事件再 seek。"""
        session = self._state.session
        if session is None:
            return
        self._state = _replace(
            self._state,
            playlist=session.items,
            current_index=session.index,
            play_mode=session.mode,
            position_ms=0,
            duration_ms=0,
            is_playing=False,
            pending_restore_pos=session.position_ms,
            play_nonce=self._bump_play(),
            native_playlist=rules.project_playlist(
                session.items, session.mode, session.index, self._scanner.to_uri
            ),
            native_mode=rules.list_mode_for(session.mode),
            session=None,
        )
        if session.items:
            self._add_recent(session.items[session.index].path)
        self._notify()

    def dismiss_session(self) -> None:
        """用户选择不恢复：丢弃候选。"""
        if self._state.session is not None:
            self._commit(session=None)

    def save_settings(self) -> None:
        """落盘音量 / 倍速 / 模式 / 侧栏宽度 / 时间显示。"""
        self._prefs.set_setting("volume", self._state.volume)
        self._prefs.set_setting("playback_rate", self._state.playback_rate)
        self._prefs.set_setting("play_mode", self._state.play_mode.value)
        self._prefs.set_setting("sidebar_width", self._state.sidebar_width)
        self._prefs.set_setting("show_remaining_time", self._state.show_remaining_time)

    def save_session(self) -> None:
        """保存播放列表、索引、位置与模式；空列表清空会话。"""
        if not self._state.playlist:
            self._prefs.clear_session()
            return
        self._prefs.save_session(
            {
                "playlist": [item.to_dict() for item in self._state.playlist],
                "current_index": self._state.current_index,
                "position_ms": self._state.position_ms,
                "play_mode": self._state.play_mode.value,
            }
        )

    def shutdown(self) -> None:
        """退出前先落盘，再允许窗口销毁。"""
        self.save_settings()
        self.save_session()

    def _add_recent(self, path: str) -> None:
        recents = self._prefs.add_recent(path, self._state.recents)
        self._prefs.save_recents(recents)
        self._commit(recents=recents)

    # ─── 文件导入 ───

    def import_paths(
        self, paths: tuple[str, ...], *, replace: bool = True
    ) -> tuple[PlaylistItem, ...]:
        """路径列表 → 播放列表项 → 业务列表（只经 ScannerPort 接触磁盘）。"""
        items = self._scanner.make_playlist_items(paths)
        if items:
            self.add_files(items, replace=replace)
        return items

    def import_folder(self, folder: str) -> tuple[PlaylistItem, ...]:
        """文件夹扫描 → 整列替换。"""
        items = self._scanner.scan_videos(folder)
        if items:
            self.add_files(items, replace=True)
        return items

    # ─── 播放列表 ───

    def set_playlist(self, items: tuple[PlaylistItem, ...]) -> None:
        """整列替换并回到首项（打开文件 / 文件夹的主路径）。"""
        self.add_files(items, replace=True)

    def add_files(
        self, items: tuple[PlaylistItem, ...], *, replace: bool = False
    ) -> None:
        """批量加入列表；空列表不动作；去重且不超过 MAX_PLAYLIST。"""
        if not items:
            return
        if replace or not self._state.playlist:
            playlist = items[:MAX_PLAYLIST]
            index, pos, duration, playing = 0, 0, 0, False
        else:
            existing = {item.path for item in self._state.playlist}
            playlist = list(self._state.playlist)
            for item in items:
                if item.path not in existing and len(playlist) < MAX_PLAYLIST:
                    playlist.append(item)
                    existing.add(item.path)
            index = self._state.current_index
            pos, duration, playing = (
                self._state.position_ms,
                self._state.duration_ms,
                self._state.is_playing,
            )
        self._state = _replace(
            self._state,
            playlist=tuple(playlist),
            current_index=index,
            position_ms=pos,
            duration_ms=duration,
            is_playing=playing,
            play_nonce=self._bump_play(),
        )
        self._project_now()
        self._add_recent(items[0].path)

    def add_to_playlist(self, item: PlaylistItem) -> None:
        if len(self._state.playlist) >= MAX_PLAYLIST:
            return
        self._commit(playlist=(*self._state.playlist, item), reproject=True)
        self._add_recent(item.path)

    def insert_to_playlist(self, index: int, item: PlaylistItem) -> None:
        if not rules.is_valid_index(index, len(self._state.playlist) + 1):
            return
        items = list(self._state.playlist)
        items.insert(index, item)
        self._commit(playlist=tuple(items), reproject=True)
        self._add_recent(item.path)

    def remove_from_playlist(self, index: int) -> None:
        """移除一项，并保持当前索引指向合理位置。"""
        size = len(self._state.playlist)
        if not rules.is_valid_index(index, size):
            return
        items = list(self._state.playlist)
        items.pop(index)
        next_index = rules.index_after_remove(self._state.current_index, index, size)
        cleared = not items
        self._state = _replace(
            self._state,
            playlist=tuple(items),
            current_index=next_index,
            is_playing=False if cleared else self._state.is_playing,
            play_nonce=self._bump_play() if index == self._state.current_index and items else self._state.play_nonce,
        )
        self._project_now()
        self._notify()

    def clear_playlist(self) -> None:
        self._state = _replace(
            self._state,
            playlist=(),
            current_index=0,
            is_playing=False,
            position_ms=0,
            duration_ms=0,
            play_nonce=self._state.play_nonce,
        )
        self._project_now()
        self._notify()

    def reorder(self, from_idx: int, to_idx: int) -> None:
        """拖拽排序：移动一项并同步当前索引。"""
        size = len(self._state.playlist)
        if not rules.is_valid_index(from_idx, size) or not rules.is_valid_index(to_idx, size):
            return
        items = list(self._state.playlist)
        item = items.pop(from_idx)
        items.insert(to_idx, item)
        self._commit(
            playlist=tuple(items),
            current_index=rules.index_after_move(
                self._state.current_index, from_idx, to_idx
            ),
            reproject=True,
        )

    def move_item(self, from_idx: int, to_idx: int) -> None:
        """兼容旧名：与 :meth:`reorder` 等价。"""
        self.reorder(from_idx, to_idx)

    def remove_current(self) -> None:
        self.remove_from_playlist(self._state.current_index)

    def set_sort_key(self, key: SortKey) -> None:
        """只改展示顺序，不改底层索引。"""
        self._commit(sort_key=key)

    def sorted_playlist(self) -> tuple[tuple[int, PlaylistItem], ...]:
        """当前排序下的 ``(原始索引, 项)`` 序列。"""
        return rules.sorted_items(self._state.playlist, self._state.sort_key)

    def _project_now(self) -> None:
        """根据当前列表 / 模式 / 索引重算原生投影（不触发额外通知）。"""
        self._state = _replace(
            self._state,
            native_playlist=rules.project_playlist(
                self._state.playlist,
                self._state.play_mode,
                self._state.current_index,
                self._scanner.to_uri,
            ),
            native_mode=rules.list_mode_for(self._state.play_mode),
        )

    # ─── 播放控制 ───

    async def auto_play(self) -> None:
        """play_nonce 变化时由 ViewModel 调度：把当前项投给播放器起播。

        这样「什么时候该播」是业务状态（nonce）的事，「怎么播」是端口的事，
        View 不需要自己监听 nonce 也不需要认识播放器。
        """
        if self._state.has_media:
            await self._media.play_at(self._state.current_index)

    def play_at(self, index: int) -> None:
        """跳到指定项；状态与 nonce 更新后由 auto_play 统一起播。"""
        if not rules.is_valid_index(index, len(self._state.playlist)):
            return
        self._state = _replace(
            self._state,
            current_index=index,
            position_ms=0,
            duration_ms=0,
            is_playing=False,
            play_nonce=self._bump_play(),
        )
        self._project_now()
        self._add_recent(self._state.playlist[index].path)

    def play_next(self) -> None:
        if self._state.has_next:
            self.play_at(self._state.current_index + 1)
        elif (
            self._state.play_mode == PlayMode.REPEAT_ALL
            and self._state.playlist
        ):
            self.play_at(0)

    def play_prev(self) -> None:
        if self._state.has_prev:
            self.play_at(self._state.current_index - 1)

    def play_first(self) -> None:
        if self._state.playlist:
            self.play_at(0)

    def play_last(self) -> None:
        if self._state.playlist:
            self.play_at(len(self._state.playlist) - 1)

    def play_random(self) -> None:
        if self._state.playlist:
            self.play_at(
                random.randint(0, len(self._state.playlist) - 1)  # noqa: S311
            )

    async def stop(self) -> None:
        await self._media.stop()
        self._commit(is_playing=False, position_ms=0)

    async def toggle_play(self) -> None:
        """播放 / 暂停：底层命令与 UI 标志同步翻转。"""
        await self._media.play_or_pause()
        self._commit(is_playing=not self._state.is_playing)

    def set_playing(self, playing: bool) -> None:
        self._commit(is_playing=playing)

    async def seek(self, position_ms: int) -> None:
        target = max(0, position_ms)
        await self._media.seek(target)
        self._commit(position_ms=target)

    async def seek_relative(self, delta_ms: int) -> None:
        await self._media.seek_relative(delta_ms)

    def cycle_play_mode(self) -> None:
        modes = tuple(PlayMode)
        current = modes.index(self._state.play_mode)
        self.set_play_mode(modes[(current + 1) % len(modes)])

    def set_play_mode(self, mode: PlayMode) -> None:
        """切换模式后保留进度与播放状态（底层会重建播放列表）。"""
        if self._state.has_media:
            self._pending_restore = (
                self._state.position_ms,
                self._state.is_playing,
            )
        self._state = _replace(
            self._state,
            play_mode=mode,
            play_nonce=self._bump_play(),
        )
        self._project_now()
        self._notify()

    def set_volume(self, volume: float) -> None:
        value = rules.clamp_volume(volume)
        self._commit(volume=value, muted=False if value > 0 else self._state.muted)

    def set_playback_rate(self, rate: float) -> None:
        self._commit(playback_rate=rate)

    def step_speed(self, direction: int) -> None:
        """快捷键共用同一套档位步进规则。"""
        self.set_playback_rate(rules.step_speed(self._state.playback_rate, direction))

    def toggle_mute(self) -> None:
        self._commit(muted=not self._state.muted)

    def toggle_remaining_time(self) -> None:
        self._commit(show_remaining_time=not self._state.show_remaining_time)

    def set_fullscreen(self, fullscreen: bool) -> None:
        """全屏意图：状态驱动控件属性，不反向操作控件。"""
        self._commit(is_fullscreen=fullscreen)

    def on_fullscreen_event(self, fullscreen: bool) -> None:
        """底层全屏事件回传：仅在状态不同步时纠正。"""
        if self._state.is_fullscreen != fullscreen:
            self._commit(is_fullscreen=fullscreen)

    # ─── 播放器事件 ───

    def on_position(self, ms: int) -> None:
        """位置轮询：不推 nonce，只更新一帧进度。"""
        self._commit(position_ms=max(0, ms))

    def on_duration(self, ms: int) -> None:
        self._commit(duration_ms=max(0, ms))

    async def on_video_loaded(self) -> None:
        """画面加载完成：按优先级消费模式恢复 / 会话进度恢复。"""
        pending = self._pending_restore
        if pending is not None:
            self._pending_restore = None
            pos, was_playing = pending
            if pos > 0:
                await self._media.seek(pos)
            if was_playing:
                await self._media.play()
            self._commit(is_playing=was_playing)
            return
        pos = self._state.pending_restore_pos
        if pos > 0:
            self._commit(pending_restore_pos=0, is_playing=False)
            await self._media.seek_after_load(pos)
            return
        self._commit(is_playing=True)

    def on_track_change(self, index: int) -> None:
        """原生轨道切换事件；单曲循环时忽略。"""
        if self._state.play_mode == PlayMode.REPEAT_ONE:
            return
        if rules.is_valid_index(index, len(self._state.playlist)):
            self._commit(current_index=index, position_ms=0, reproject=True)

    def on_complete(self) -> None:
        """播放完成：按业务模式决定重播、跳转或停止。"""
        mode = self._state.play_mode
        if mode == PlayMode.REPEAT_ONE:
            self._commit(is_playing=True, play_nonce=self._bump_play())
            return
        if mode == PlayMode.SHUFFLE and len(self._state.playlist) > 1:
            self.play_random()
            return
        if self._state.has_next:
            self.play_next()
            return
        if mode == PlayMode.REPEAT_ALL and self._state.playlist:
            self.play_at(0)
            return
        self._commit(is_playing=False)

    # ─── 近期记录 ───

    def play_recent(self, path: str) -> None:
        """打开近期文件：扫描 → 整列替换 → 由 nonce 触发起播。"""
        try:
            item = self._scanner.make_playlist_item(path)
        except Exception as exc:
            self.notice(rules.classify_error(exc), NoticeTone.ERROR)
            return
        self.add_files((item,), replace=True)

    def remove_recent(self, path: str) -> None:
        recents = tuple(item for item in self._state.recents if item != path)
        self._prefs.save_recents(recents)
        self._commit(recents=recents)

    def clear_recents(self) -> None:
        self._prefs.save_recents(())
        self._commit(recents=())
