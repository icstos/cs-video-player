"""infra / media —— 播放控制端口的实现。

只做三件事：把 Service 的意图转发给 View 注入的 :class:`VideoControl`、
在未挂载时安全降级、把底层异常翻译成一次错误回执。这里没有播放列表规则、
没有状态机，也不认识 Flet 控件类。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from cs_video_player.infra.ports import ErrorHandler, MediaPort, VideoControl

logger = logging.getLogger(__name__)

#: 窗口关闭时 Flet 会话先于异步任务结束，这类异常是生命周期噪音而非功能失败。
_SHUTDOWN_MARKERS: tuple[str, ...] = (
    "session closed",
    "destroyed session",
    "session was garbage collected",
)


def is_shutdown_noise(exc: BaseException) -> bool:
    """判断异常是否发生在会话销毁阶段（供各层一致过滤）。"""
    message: str = str(exc).lower()
    return any(marker in message for marker in _SHUTDOWN_MARKERS)


class MediaController(MediaPort):
    """面向 :class:`VideoControl` 的异步安全播放器适配器。"""

    def __init__(self) -> None:
        self._control: VideoControl | None = None
        self._error_handler: ErrorHandler | None = None

    @property
    def bound(self) -> bool:
        """播放器句柄是否已注入。"""
        return self._control is not None

    def bind_control(self, control: VideoControl | None) -> None:
        """注入 / 解除 View 提供的播放器句柄。"""
        self._control = control

    def set_error_handler(self, handler: ErrorHandler | None) -> None:
        """注册底层错误回执（由 Service 提供）。"""
        self._error_handler = handler

    def _report(self, label: str, exc: BaseException) -> None:
        """记录日志并通知业务层；回执本身失败不影响播放。

        窗口关闭时 Flet 会话会先于异步任务结束，这类 ``Session closed`` 是
        生命周期噪音：既不表示功能失败，也不该给用户弹错误回执。
        """
        if is_shutdown_noise(exc):
            logger.debug("会话已关闭，忽略 %s", label)
            return
        logger.error("播放器操作失败 %s: %s", label, exc, exc_info=exc)
        if self._error_handler is not None:
            try:
                self._error_handler(label, str(exc))
            except Exception:
                logger.exception("播放器错误回执失败")

    async def _run(self, label: str, action: Callable[[VideoControl], Awaitable[Any]]) -> None:
        """统一收敛 await 类操作，未挂载时静默跳过。"""
        if self._control is None:
            logger.debug("播放器未就绪，跳过 %s", label)
            return
        try:
            await action(self._control)
        except Exception as exc:
            self._report(label, exc)

    def _run_sync(self, label: str, action: Callable[[VideoControl], Any]) -> None:
        """统一收敛属性类操作，未挂载时静默跳过。"""
        if self._control is None:
            return
        try:
            action(self._control)
        except Exception as exc:
            self._report(label, exc)

    async def play(self) -> None:
        await self._run("play", lambda c: c.play())

    async def pause(self) -> None:
        await self._run("pause", lambda c: c.pause())

    async def play_or_pause(self) -> None:
        await self._run("play_or_pause", lambda c: c.play_or_pause())

    async def stop(self) -> None:
        await self._run("stop", lambda c: c.stop())

    async def seek(self, position_ms: int) -> None:
        await self._run("seek", lambda c: c.seek(max(0, position_ms)))

    async def seek_relative(self, delta_ms: int) -> None:
        await self._run("seek_relative", lambda c: c.seek_relative(delta_ms))

    async def jump_to(self, index: int) -> None:
        await self._run("jump_to", lambda c: c.jump_to(index))

    async def next(self) -> None:
        await self._run("next", lambda c: c.next())

    async def previous(self) -> None:
        await self._run("previous", lambda c: c.previous())

    async def play_at(self, index: int) -> None:
        await self._run("play_at", lambda c: c.play_at(index))

    async def restore_after_mode_change(
        self, position_ms: int, was_playing: bool
    ) -> None:
        await self._run(
            "restore_after_mode_change",
            lambda c: c.restore_after_mode_change(position_ms, was_playing),
        )

    async def seek_after_load(self, position_ms: int) -> None:
        await self._run("seek_after_load", lambda c: c.seek_after_load(position_ms))

    async def take_screenshot(self) -> bytes | None:
        if self._control is None:
            return None
        try:
            return await self._control.take_screenshot()
        except Exception as exc:
            self._report("take_screenshot", exc)
            return None

    def set_volume(self, volume: float) -> None:
        self._run_sync("set_volume", lambda c: c.set_volume(max(0.0, min(100.0, volume))))

    def set_playback_rate(self, rate: float) -> None:
        self._run_sync("set_playback_rate", lambda c: c.set_playback_rate(rate))

    def set_muted(self, muted: bool) -> None:
        self._run_sync("set_muted", lambda c: c.set_muted(muted))

    def set_fullscreen(self, fullscreen: bool) -> None:
        self._run_sync("set_fullscreen", lambda c: c.set_fullscreen(fullscreen))
