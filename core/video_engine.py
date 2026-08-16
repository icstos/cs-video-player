"""
视频播放引擎。
封装 flet-video 的底层 API，提供安全、可恢复的播放操作。

关键: Video 控件的 volume / playback_rate / muted / fullscreen 均为属性（property），
需要赋值后调用 page.update() 刷新；播放控制方法（play / pause / seek 等）为 async。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import flet as ft
from flet_video import (
    MaterialDesktopVideoControls,
    PlaylistMode,
    Video,
    VideoMedia,
)

from configs.theme import C_BORDER, C_HOVER, C_PRIMARY, C_TEXT
from core.models import PlayMode, PlaylistItem
from utils.formatters import to_uri

logger = logging.getLogger(__name__)


class VideoEngine:
    """对 flet_video.Video 的异步安全封装。"""

    def __init__(self) -> None:
        self._video_ref: ft.Ref[Video] = ft.Ref[Video]()
        self._is_seeking: bool = False
        self._seek_pos: int = 0
        self._pending_restore: Optional[tuple[int, bool]] = None
        self._page: Optional[ft.Page] = None

    @property
    def ref(self) -> ft.Ref[Video]:
        return self._video_ref

    @property
    def video(self) -> Optional[Video]:
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

    def bind_page(self, page: ft.Page) -> None:
        self._page = page

    def _update_page(self) -> None:
        if self._page is not None:
            try:
                self._page.update()
            except Exception:
                pass

    @staticmethod
    def build_fullscreen_controls() -> MaterialDesktopVideoControls:
        return MaterialDesktopVideoControls(
            seek_bar_position_color=C_PRIMARY,
            seek_bar_thumb_color=C_PRIMARY,
            seek_bar_color=C_BORDER,
            seek_bar_hover_color=C_HOVER,
            volume_bar_active_color=C_PRIMARY,
            volume_bar_thumb_color=C_PRIMARY,
            volume_bar_color=C_BORDER,
            button_bar_button_color=C_TEXT,
            play_and_pause_on_tap=False,
            toggle_fullscreen_on_double_press=True,
            visible_on_mount=False,
        )

    @staticmethod
    def build_playlist(
        items: list[PlaylistItem],
        play_mode: PlayMode,
        current_index: int,
    ) -> list[VideoMedia]:
        if not items:
            return []
        if play_mode == PlayMode.REPEAT_ONE:
            if 0 <= current_index < len(items):
                return [VideoMedia(resource=to_uri(items[current_index].path))]
            return []
        return [VideoMedia(resource=to_uri(item.path)) for item in items]

    @staticmethod
    def get_playlist_mode(play_mode: PlayMode) -> PlaylistMode:
        if play_mode == PlayMode.REPEAT_ONE:
            return PlaylistMode.SINGLE
        if play_mode == PlayMode.REPEAT_ALL:
            return PlaylistMode.LOOP
        return PlaylistMode.NONE

    async def _run(self, fn, *, label: str) -> None:
        try:
            await fn()
        except Exception as exc:
            logger.exception("视频引擎操作失败 %s: %s", label, exc)

    async def play(self) -> None:
        v = self.video
        if v is None:
            logger.warning("Video 控件未就绪，无法播放")
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
            lambda: v.seek(ft.Duration(milliseconds=position_ms)),
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
            logger.exception("相对跳转失败: %s", exc)

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
            logger.exception("截图失败: %s", exc)
            return None
