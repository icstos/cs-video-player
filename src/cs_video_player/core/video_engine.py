"""视频播放引擎 —— 对原生播放器的异步安全封装。

边界：这一层只懂「播放器能做什么」（播放 / 跳转 / 音量 / 全屏 / 截图），
不懂界面上按钮长什么样、播放列表怎么排序。所有底层类型与控件配色都从
:mod:`components.media` 取，应用侧不直接 import ``flet_video``。

关键约定：``NativeVideo`` 的 volume / playback_rate / muted / fullscreen 是
**属性**，赋值后要 ``page.update()``；播放控制方法（play / pause / seek 等）
是 async。全部操作都经 :meth:`VideoEngine._run` 收敛异常，底层失效时记日志并
通知 UI，而不是让异步任务悄悄死掉。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

import ui
from cs_video_player.components.media import NativeVideo, PlaylistMode, VideoMedia, desktop_controls

from cs_video_player.configs.theme import PALETTE
from cs_video_player.core.models import PlayMode, PlaylistItem
from cs_video_player.utils.formatters import to_uri

logger = logging.getLogger(__name__)

ErrorCallback = Callable[[str, str], None]  # (label, error_message)


class VideoEngine:
    """对 :class:`components.media.NativeVideo` 的异步安全封装。"""

    def __init__(self) -> None:
        self._video_ref: ui.Ref[NativeVideo] = ui.Ref[NativeVideo]()
        self._is_seeking: bool = False
        self._seek_pos: int = 0
        self._pending_restore: Optional[tuple[int, bool]] = None
        self._page: Optional[ui.Page] = None
        self._error_callback: Optional[ErrorCallback] = None

    @property
    def ref(self) -> ui.Ref[NativeVideo]:
        return self._video_ref

    @property
    def video(self) -> Optional[NativeVideo]:
        return self._video_ref.current

    @property
    def is_seeking(self) -> bool:
        return self._is_seeking

    @is_seeking.setter
    def is_seeking(self, value: bool) -> None:
        self._is_seeking = value

    @property
    def seek_pos(self) -> int:
        return self._seek_pos

    @seek_pos.setter
    def seek_pos(self, value: int) -> None:
        self._seek_pos = value

    @property
    def pending_restore(self) -> Optional[tuple[int, bool]]:
        return self._pending_restore

    @pending_restore.setter
    def pending_restore(self, value: Optional[tuple[int, bool]]) -> None:
        self._pending_restore = value

    def bind_page(self, page: ui.Page) -> None:
        self._page = page

    @property
    def error_callback(self) -> Optional[ErrorCallback]:
        return self._error_callback

    @error_callback.setter
    def error_callback(self, value: Optional[ErrorCallback]) -> None:
        self._error_callback = value

    def _report_error(self, label: str, exc: BaseException) -> None:
        """记录日志并通知 UI 层错误。"""
        logger.error("视频引擎操作失败 %s: %s", label, exc, exc_info=exc)
        if self._error_callback:
            try:
                self._error_callback(label, str(exc))
            except Exception:
                logger.exception("错误回调执行失败")

    def _update_page(self) -> None:
        if self._page is not None:
            try:
                self._page.update()
            except Exception:
                pass

    @staticmethod
    def build_fullscreen_controls():
        """全屏控制条：配色取自 :func:`components.media.desktop_controls`。

        保留此方法名是为了让既有调用点不用改；颜色不再在这里手写，
        与控制栏自绘部分共用同一张 :class:`configs.theme.MediaPalette`。
        """
        return desktop_controls(PALETTE)

    @staticmethod
    def build_playlist(
        items: list[PlaylistItem],
        play_mode: PlayMode,
        current_index: int,
    ) -> list[VideoMedia]:
        """把业务播放列表翻译成原生播放列表。

        单曲循环时只投喂当前一项（原生 ``SINGLE`` 模式会自己重播），否则整列
        交给播放器，让上一曲 / 下一曲由底层轨道事件驱动。
        """
        if not items:
            return []
        if play_mode == PlayMode.REPEAT_ONE:
            if 0 <= current_index < len(items):
                return [VideoMedia(resource=to_uri(items[current_index].path))]
            return []
        return [VideoMedia(resource=to_uri(item.path)) for item in items]

    @staticmethod
    def get_playlist_mode(play_mode: PlayMode) -> PlaylistMode:
        """业务播放模式 → 原生播放列表模式（纯映射，可单测）。"""
        if play_mode == PlayMode.REPEAT_ONE:
            return PlaylistMode.SINGLE
        if play_mode == PlayMode.REPEAT_ALL:
            return PlaylistMode.LOOP
        return PlaylistMode.NONE

    async def _run(self, fn, *, label: str) -> None:
        try:
            await fn()
        except Exception as exc:
            self._report_error(label, exc)

    async def play(self) -> None:
        v = self.video
        if v is None:
            logger.warning("播放器未就绪，无法播放")
            return
        await self._run(v.play, label="play")

    async def pause(self) -> None:
        v = self.video
        if v is None:
            return
        await self._run(v.pause, label="pause")

    async def play_or_pause(self) -> None:
        v = self.video
        if v is None:
            return
        await self._run(v.play_or_pause, label="play_or_pause")

    async def stop(self) -> None:
        v = self.video
        if v is None:
            return
        await self._run(v.stop, label="stop")

    async def seek(self, position_ms: int) -> None:
        v = self.video
        if v is None:
            return
        position_ms = max(0, position_ms)
        await self._run(
            lambda: v.seek(ui.Duration(milliseconds=position_ms)),
            label=f"seek({position_ms})",
        )

    async def seek_relative(self, delta_ms: int) -> None:
        v = self.video
        if v is None:
            return
        try:
            current = await v.get_current_position()
            now_ms = current.in_milliseconds if current else 0
            await self.seek(max(0, now_ms + delta_ms))
        except Exception as exc:
            self._report_error("seek_relative", exc)

    async def jump_to(self, index: int) -> None:
        v = self.video
        if v is None:
            return
        await self._run(lambda: v.jump_to(index), label=f"jump_to({index})")

    async def next(self) -> None:
        v = self.video
        if v is None:
            return
        await self._run(v.next, label="next")

    async def previous(self) -> None:
        v = self.video
        if v is None:
            return
        await self._run(v.previous, label="previous")

    async def set_volume(self, volume: float) -> None:
        v = self.video
        if v is None:
            return
        v.volume = max(0.0, min(100.0, volume))
        self._update_page()

    async def set_playback_rate(self, rate: float) -> None:
        v = self.video
        if v is None:
            return
        v.playback_rate = rate
        self._update_page()

    async def set_muted(self, muted: bool) -> None:
        v = self.video
        if v is None:
            return
        v.muted = muted
        self._update_page()

    async def set_fullscreen(self, fullscreen: bool) -> None:
        v = self.video
        if v is None:
            return
        v.fullscreen = fullscreen
        self._update_page()

    async def play_at(self, index: int, play_mode: PlayMode) -> None:
        if play_mode == PlayMode.REPEAT_ONE:
            return
        await self.jump_to(index)
        await asyncio.sleep(0.05)
        await self.play()

    async def restore_after_mode_change(self, position_ms: int, was_playing: bool) -> None:
        await asyncio.sleep(0.15)
        if position_ms > 0:
            await self.seek(position_ms)
        if was_playing:
            await self.play()

    async def take_screenshot(self) -> Optional[bytes]:
        v = self.video
        if v is None:
            return None
        try:
            return await v.take_screenshot(format="image/png")
        except Exception as exc:
            self._report_error("take_screenshot", exc)
            return None
