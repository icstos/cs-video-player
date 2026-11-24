"""viewmodel / app_vm —— View 与 Service 之间的状态适配器（纯 Python）。

本类是**唯一持有 UI 交互态**的地方：侧栏显隐、控制栏自动隐藏、拖动中、
文件对话框请求、会话确认。它不 import ``ui`` / flet / flet_video，也不知道
控件长什么样；View 从 :attr:`state` 读一帧 :class:`AppState` 直接渲染，
所有用户意图都通过下面的方法回灌。

异步命令由 :meth:`_spawn` 调度，Service 自身不创建任务；因此逻辑测试可以在
无事件循环的环境里直接调用同步命令，也可以 ``asyncio.run`` 驱动异步命令。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from cs_video_player.models.config import (
    CONTROLS_AUTO_HIDE_MS,
    KEYBOARD_SHORTCUTS,
    SEEK_STEP_SHORT,
    VOLUME_STEP,
    VOLUME_WHEEL_STEP,
)
from cs_video_player.models.entities import FileRequest, KeyInfo, PlaylistItem
from cs_video_player.models.enums import FileRequestKind, NoticeTone, SortKey
from cs_video_player.models.state import AppState
from cs_video_player.service import PlaybackService

logger = logging.getLogger(__name__)

Listener = Callable[[], None]


class AppViewModel:
    """应用视图模型：状态 → View，意图 → Service。"""

    def __init__(self, service: PlaybackService) -> None:
        self._service: PlaybackService = service
        self._ui: dict[str, Any] = {
            "sidebar_visible": True,
            "controls_visible": True,
            "is_seeking": False,
            "seek_preview_ms": 0,
            "file_request": None,
        }
        self._state: AppState = AppState.from_playback(service.state)
        self._listeners: list[Listener] = []
        self._unsubscribe: Callable[[], None] | None = service.subscribe(
            self._on_service_changed
        )
        self._hide_timer: asyncio.TimerHandle | None = None
        self._hide_seq: int = 0
        self._file_nonce: int = 0
        self._last_play_nonce: int = service.state.play_nonce
        service.peek_session()
        self._refresh()

    # ─── 状态与订阅 ───

    @property
    def state(self) -> AppState:
        """当前 UI 快照；View 渲染函数只读它。"""
        return self._state

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """订阅重渲染信号，返回退订函数。"""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def detach(self) -> None:
        """组件卸载：停止计时器与业务订阅。"""
        self._cancel_hide_timer()
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _notify(self) -> None:
        for callback in tuple(self._listeners):
            try:
                callback()
            except Exception as exc:
                message: str = str(exc).lower()
                if "session closed" in message or "destroyed session" in message:
                    continue
                logger.exception("视图状态回执失败: %s", exc)

    def _refresh(self) -> None:
        self._state = AppState.from_playback(self._service.state, **self._ui)
        self._notify()

    def _on_service_changed(self) -> None:
        nonce = self._service.state.play_nonce
        if nonce != self._last_play_nonce:
            self._last_play_nonce = nonce
            self._spawn(self._service.auto_play())
        self._refresh()

    def _patch_ui(self, **changes: Any) -> None:
        self._ui.update(changes)
        self._refresh()

    @staticmethod
    def _spawn(coro: Coroutine[Any, Any, None]) -> None:
        """有循环就挂到循环，没有就同步跑完（便于单测）。"""
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    # ─── 生命周期 ───

    def attach_media_control(self, control: object | None) -> None:
        """View 注入播放器句柄；Service 经端口协议使用它。"""
        self._service.bind_media(control)

    def on_window_close(self) -> None:
        """关窗前落盘设置与会话。"""
        self._service.shutdown()

    def acknowledge_notice(self) -> None:
        """View 已弹出回执，清空以免重复展示。"""
        self._service.clear_notice()

    def confirm_restore(self) -> None:
        """用户确认恢复上次会话。"""
        self._service.restore_session()

    def dismiss_restore(self) -> None:
        """用户放弃恢复上次会话。"""
        self._service.dismiss_session()

    # ─── 文件对话框：状态驱动 ───

    def request_open_files(self) -> None:
        self._file_nonce += 1
        self._patch_ui(file_request=FileRequest(FileRequestKind.FILES, self._file_nonce))

    def request_open_folder(self) -> None:
        self._file_nonce += 1
        self._patch_ui(file_request=FileRequest(FileRequestKind.FOLDER, self._file_nonce))

    def cancel_file_request(self) -> None:
        self._patch_ui(file_request=None)

    def on_files_selected(self, paths: tuple[str, ...]) -> None:
        items = self._service.import_paths(paths, replace=True)
        if not items:
            self._service.notice("所选文件均不受支持", NoticeTone.WARNING)
        self._patch_ui(file_request=None)

    def on_folder_selected(self, folder: str | None) -> None:
        if folder is None:
            self._patch_ui(file_request=None)
            return
        items = self._service.import_folder(folder)
        if not items:
            self._service.notice("该文件夹下未找到视频文件", NoticeTone.WARNING)
        self._patch_ui(file_request=None)

    # ─── 播放列表意图 ───

    def play_at(self, index: int) -> None:
        self._service.play_at(index)

    def remove_item(self, index: int) -> None:
        self._service.remove_from_playlist(index)

    def remove_current(self) -> None:
        self._service.remove_current()

    def reorder(self, src: int, dst: int) -> None:
        self._service.reorder(src, dst)

    def set_sort(self, key: SortKey) -> None:
        self._service.set_sort_key(key)

    def clear_playlist(self) -> None:
        self._service.clear_playlist()

    def sorted_playlist(self) -> tuple[tuple[int, PlaylistItem], ...]:
        """给 View 的展示序列查询（排序规则留在 Service）。"""
        return self._service.sorted_playlist()

    def open_recent(self, path: str) -> None:
        self._service.play_recent(path)

    def remove_recent(self, path: str) -> None:
        """path 为空串表示清空全部近期记录。"""
        if path == "":
            self._service.clear_recents()
        else:
            self._service.remove_recent(path)

    # ─── 播放控制意图 ───

    def toggle_play(self) -> None:
        self._spawn(self._service.toggle_play())

    def stop(self) -> None:
        self._spawn(self._service.stop())

    def play_next(self) -> None:
        self._service.play_next()

    def play_prev(self) -> None:
        self._service.play_prev()

    def toggle_play_mode(self) -> None:
        self._service.cycle_play_mode()

    def seek_relative(self, delta_ms: int) -> None:
        self._spawn(self._service.seek_relative(delta_ms))

    def set_volume(self, volume: float) -> None:
        self._service.set_volume(volume)

    def wheel_volume(self, delta_y: float) -> None:
        """滚轮方向与步长在一致的地方计算，VM 不认识事件对象。"""
        from cs_video_player.service.rules import volume_after_wheel

        current = self._service.state.volume
        target = volume_after_wheel(current, delta_y, VOLUME_WHEEL_STEP)
        if target != current:
            self._service.set_volume(target)

    def toggle_mute(self) -> None:
        self._service.toggle_mute()

    def set_rate(self, rate: float) -> None:
        self._service.set_playback_rate(rate)

    def step_speed(self, direction: int) -> None:
        self._service.step_speed(direction)

    def toggle_remaining_time(self) -> None:
        self._service.toggle_remaining_time()

    def toggle_fullscreen(self) -> None:
        target = not self._state.is_fullscreen
        self._service.set_fullscreen(target)
        if target:
            self.on_video_hover()
        else:
            self._cancel_hide_timer()
            self._patch_ui(controls_visible=True)

    def exit_fullscreen(self) -> None:
        if self._state.is_fullscreen:
            self.toggle_fullscreen()

    def on_fullscreen_event(self, fullscreen: bool) -> None:
        """底层全屏状态回传：纠正状态并同步控制栏自动隐藏。"""
        self._service.on_fullscreen_event(fullscreen)
        if fullscreen:
            self.on_video_hover()
        else:
            self._cancel_hide_timer()
            self._patch_ui(controls_visible=True)

    # ─── 控制栏自动隐藏 ───

    def _cancel_hide_timer(self) -> None:
        if self._hide_timer is not None:
            self._hide_timer.cancel()
            self._hide_timer = None

    def on_video_hover(self) -> None:
        """全屏时唤醒控制栏，并重新开始自动隐藏倒计时。"""
        if not self._state.is_fullscreen:
            return
        self._hide_seq += 1
        seq = self._hide_seq
        self._patch_ui(controls_visible=True)
        self._cancel_hide_timer()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._hide_timer = loop.call_later(
            CONTROLS_AUTO_HIDE_MS / 1000.0,
            lambda: self._auto_hide(seq),
        )

    def _auto_hide(self, seq: int) -> None:
        self._hide_timer = None
        if seq == self._hide_seq and self._state.is_fullscreen:
            self._patch_ui(controls_visible=False)

    # ─── 侧栏 ───

    def toggle_sidebar(self) -> None:
        self._patch_ui(sidebar_visible=not self._state.sidebar_visible)

    # ─── 拖动进度 ───

    def begin_seek(self) -> None:
        self._patch_ui(is_seeking=True)

    def preview_seek(self, position_ms: int) -> None:
        self._patch_ui(seek_preview_ms=max(0, position_ms))

    def end_seek(self, position_ms: int) -> None:
        target = max(0, position_ms)
        self._patch_ui(is_seeking=False, seek_preview_ms=0)
        self._spawn(self._service.seek(target))

    # ─── 播放器事件 ───

    def on_position(self, ms: int) -> None:
        """拖动期间忽略底层位置回写，避免画面往回跳。"""
        if self._state.is_seeking:
            return
        self._service.on_position(ms)

    def on_duration(self, ms: int) -> None:
        self._service.on_duration(ms)

    def on_video_loaded(self) -> None:
        self._spawn(self._service.on_video_loaded())

    def on_track_change(self, index: int) -> None:
        self._service.on_track_change(index)

    def on_complete(self) -> None:
        self._service.on_complete()

    # ─── 快捷键 ───

    def handle_key(self, info: KeyInfo) -> None:
        """View 只把平台事件翻译成 KeyInfo，动作解释留在这里。"""
        key = info.key.lower()
        if info.ctrl:
            if key == "o":
                if info.shift:
                    self.request_open_folder()
                else:
                    self.request_open_files()
            return

        action = KEYBOARD_SHORTCUTS.get(key)
        if action is None:
            return
        match action:
            case "play_pause":
                self.toggle_play()
            case "seek_backward":
                self.seek_relative(-SEEK_STEP_SHORT * (2 if info.shift else 1))
            case "seek_forward":
                self.seek_relative(SEEK_STEP_SHORT * (2 if info.shift else 1))
            case "volume_up":
                self.set_volume(self._state.volume + VOLUME_STEP)
            case "volume_down":
                self.set_volume(self._state.volume - VOLUME_STEP)
            case "speed_up":
                self.step_speed(+1)
            case "speed_down":
                self.step_speed(-1)
            case "toggle_mute":
                self.toggle_mute()
            case "toggle_fullscreen":
                self.toggle_fullscreen()
            case "next_track":
                self.play_next()
            case "prev_track":
                self.play_prev()
            case "stop":
                self.stop()
            case "toggle_remaining_time":
                self.toggle_remaining_time()
            case "exit_fullscreen":
                self.exit_fullscreen()
            case "remove_current":
                self.remove_current()
            case _:
                logger.debug("未处理的快捷键动作: %s", action)
