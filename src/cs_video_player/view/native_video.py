"""view / native_video —— 原生播放器的 UI 适配（全项目唯一 import flet_video 处）。

View 负责构造控件，Infra 负责操作控件：两者通过 :class:`VideoHandle` 这个
结构化句柄连接。句柄暴露的能力与 ``infra.ports.VideoControl`` 一致，因此
Service 只需依赖抽象端口，永远不会反向依赖本文件。

这里只处理「控件怎么挂、属性怎么赋、挂载未完成时怎么重试」这类技术细节，
不含播放列表规则、不含状态机。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import flet_video as fv
import ui

from cs_video_player.models.entities import MediaTrack
from cs_video_player.models.enums import ListMode
from cs_video_player.view.theme import PALETTE

logger = logging.getLogger(__name__)

Event = object


@dataclass(frozen=True, slots=True)
class VideoCallbacks:
    """原生播放器事件 → View 的纯分发入口。"""

    on_load: Callable[[Event], None]
    on_track_change: Callable[[Event], None]
    on_complete: Callable[[Event], None]
    on_position: Callable[[Event], None]
    on_duration: Callable[[Event], None]
    on_enter_fullscreen: Callable[[Event], None]
    on_exit_fullscreen: Callable[[Event], None]


def native_mode(mode: ListMode) -> fv.PlaylistMode:
    """业务投影模式 → flet_video 的播放列表模式。"""
    return {
        ListMode.NONE: fv.PlaylistMode.NONE,
        ListMode.SINGLE: fv.PlaylistMode.SINGLE,
        ListMode.LOOP: fv.PlaylistMode.LOOP,
    }[mode]


def fullscreen_controls() -> fv.MaterialDesktopVideoControls:
    """按设计层色表构造原生全屏控制条（颜色值由 Flutter 侧消费）。"""
    return fv.MaterialDesktopVideoControls(
        seek_bar_position_color=PALETTE.primary,
        seek_bar_thumb_color=PALETTE.primary,
        seek_bar_color=PALETTE.track,
        seek_bar_hover_color=PALETTE.hover,
        volume_bar_active_color=PALETTE.primary,
        volume_bar_thumb_color=PALETTE.primary,
        volume_bar_color=PALETTE.track,
        button_bar_button_color=PALETTE.text,
        play_and_pause_on_tap=False,
        toggle_fullscreen_on_double_press=True,
        visible_on_mount=False,
    )


class VideoHandle:
    """由 View 构造、注入 Service 的播放器句柄（满足 VideoControl 协议）。"""

    def __init__(self) -> None:
        self.ref: ui.Ref[fv.Video] = ui.Ref[fv.Video]()

    def build(
        self,
        *,
        tracks: tuple[MediaTrack, ...],
        mode: ListMode,
        callbacks: VideoCallbacks,
        fullscreen: bool,
        volume: float,
        playback_rate: float,
        muted: bool,
        fill_color: str,
    ) -> fv.Video:
        """构造一帧原生播放器描述；ref 跨帧由 Flet 指向已挂载实例。

        View 每帧都调用本方法，由 Flet 按控件 ID 就地差分，播放器不会重载。
        切勿把返回的控件对象缓存进 ``use_memo``：重渲染丢弃缓存实例后 ref
        会指向未挂载控件，播放器命令将全部失效。
        """
        return fv.Video(
            ref=self.ref,
            playlist=[fv.VideoMedia(resource=track.uri) for track in tracks],
            playlist_mode=native_mode(mode),
            controls={
                fv.VideoControlsMode.NORMAL: None,
                fv.VideoControlsMode.FULLSCREEN: fullscreen_controls(),
            },
            fullscreen=fullscreen,
            volume=volume,
            playback_rate=playback_rate,
            muted=muted,
            fill_color=fill_color,
            on_load=callbacks.on_load,
            on_track_change=callbacks.on_track_change,
            on_complete=callbacks.on_complete,
            on_position_change=callbacks.on_position,
            on_duration_change=callbacks.on_duration,
            on_enter_fullscreen=callbacks.on_enter_fullscreen,
            on_exit_fullscreen=callbacks.on_exit_fullscreen,
            expand=True,
        )

    # ─── 属性：赋值后刷新控件 ───

    def _apply(self, mutate: Callable[[fv.Video], None], *, refresh: bool = True) -> None:
        video = self.ref.current
        if video is None:
            return
        try:
            mutate(video)
            if refresh:
                video.update()
        except Exception as exc:
            logger.debug("播放器属性更新失败: %s", exc)

    def set_volume(self, volume: float) -> None:
        self._apply(lambda v: setattr(v, "volume", volume))

    def set_playback_rate(self, rate: float) -> None:
        self._apply(lambda v: setattr(v, "playback_rate", rate))

    def set_muted(self, muted: bool) -> None:
        self._apply(lambda v: setattr(v, "muted", muted))

    def set_fullscreen(self, fullscreen: bool) -> None:
        self._apply(lambda v: setattr(v, "fullscreen", fullscreen))

    def refresh(self) -> None:
        self._apply(lambda _v: None)

    # ─── 命令：异步、带挂载重试 ───

    async def play(self) -> None:
        video = self.ref.current
        if video is not None:
            await video.play()

    async def pause(self) -> None:
        video = self.ref.current
        if video is not None:
            await video.pause()

    async def play_or_pause(self) -> None:
        video = self.ref.current
        if video is not None:
            await video.play_or_pause()

    async def stop(self) -> None:
        video = self.ref.current
        if video is not None:
            await video.stop()

    async def seek(self, position_ms: int) -> None:
        video = self.ref.current
        if video is not None:
            await video.seek(max(0, position_ms))

    async def seek_relative(self, delta_ms: int) -> None:
        video = self.ref.current
        if video is None:
            return
        current = await video.get_current_position()
        now_ms = current.in_milliseconds if current else 0
        await self.seek(max(0, now_ms + delta_ms))

    async def jump_to(self, index: int) -> None:
        video = self.ref.current
        expected = tuple(
            getattr(media, "resource", "") for media in (video.playlist or ())
        ) if video is not None else ()
        await self._wait_and(index, expected, lambda v: v.jump_to(index), "jump_to")

    async def next(self) -> None:
        video = self.ref.current
        if video is not None:
            await video.next()

    async def previous(self) -> None:
        video = self.ref.current
        if video is not None:
            await video.previous()

    async def _wait_and(
        self,
        index: int,
        expected: tuple[str, ...],
        action: Callable[[fv.Video], Awaitable[None]],
        label: str,
    ) -> None:
        """等控件挂载且播放列表同步到 index 后再执行命令。

        声明式重渲染与异步起播是两个任务：列表刚替换时控件里可能还是旧轨道，
        直接 ``jump_to`` 会抛 ``media_index is out of range``。这里只做技术性等待，
        不做任何业务判断（目标下标由 Service 投影后给定）。
        """
        for attempt in range(20):
            video = self.ref.current
            if video is None:
                await asyncio.sleep(0.1)
                continue
            current = tuple(
                getattr(media, "resource", "") for media in (video.playlist or ())
            )
            if current != expected or not 0 <= index < len(current):
                await asyncio.sleep(0.1)
                continue
            try:
                await action(video)
                return
            except RuntimeError as exc:
                message = str(exc).lower()
                if "session closed" in message or "destroyed session" in message:
                    return
                # 控件已构造但尚未挂到页面时，等下一帧再试。
                if "added to the page" in message and attempt < 19:
                    await asyncio.sleep(0.1)
                    continue
                raise
        logger.warning("播放器未能在 2 秒内就绪（%s index=%s）", label, index)

    async def play_at(self, index: int, tracks: tuple[MediaTrack, ...]) -> None:
        """起播携带目标轨道集，等控件投影一致后再跳转，避免越界 / 播错轨道。"""

        async def _jump_then_play(video: fv.Video) -> None:
            await video.jump_to(index)
            await asyncio.sleep(0.05)
            await video.play()

        await self._wait_and(
            index, tuple(track.uri for track in tracks), _jump_then_play, "play_at"
        )

    async def restore_after_mode_change(
        self, position_ms: int, was_playing: bool
    ) -> None:
        await asyncio.sleep(0.15)
        if position_ms > 0:
            await self.seek(position_ms)
        if was_playing:
            await self.play()

    async def seek_after_load(self, position_ms: int) -> None:
        await asyncio.sleep(0.1)
        await self.seek(position_ms)

    async def take_screenshot(self) -> bytes | None:
        video = self.ref.current
        if video is None:
            return None
        return await video.take_screenshot(format="image/png")
