"""
全局异常处理 — 友好的用户提示与日志记录。

将底层异常分类映射为用户可理解的提示信息，
通过 SnackBar 弹出通知，同时记录到日志。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import flet as ft

from configs.theme import C_BG_PANEL, C_RED, C_TEXT

if TYPE_CHECKING:
    from flet import Page

logger = logging.getLogger(__name__)

# ─── 错误分类与友好提示 ───

_ERROR_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    (
        ("codec", "decoder", "demuxer", "no video", "unsupported codec"),
        "视频编码格式不受支持，无法解码播放",
    ),
    (
        ("format", "container", "mime", "invalid format", "not a valid"),
        "视频文件格式不受支持或已损坏",
    ),
    (
        ("corrupt", "damaged", "truncated", "broken", "incomplete"),
        "视频文件可能已损坏或不完整",
    ),
    (
        ("subtitle", "sub", "caption", "track"),
        "字幕加载失败，已忽略字幕轨道",
    ),
    (
        ("permission", "access denied", "forbidden", "locked"),
        "没有访问该文件的权限",
    ),
    (
        ("not found", "no such file", "does not exist", "missing"),
        "文件不存在或已被移动",
    ),
    (
        ("network", "connection", "timeout", "unreachable"),
        "网络连接异常，无法加载资源",
    ),
    (
        ("out of memory", "oom", "allocation"),
        "内存不足，请关闭其他程序后重试",
    ),
    (
        ("hardware", "gpu", "acceleration", "dxva", "vaapi", "vdpau"),
        "硬件加速初始化失败，已切换为软件解码",
    ),
    (
        ("eof", "end of file", "premature"),
        "视频数据不完整，可能已损坏",
    ),
]


def classify_error(exc: BaseException | str) -> str:
    """
    根据异常信息推断友好的错误提示。

    Args:
        exc: 异常对象或错误消息字符串。

    Returns:
        面向用户的友好提示文本。
    """
    msg = str(exc).lower()
    for keywords, friendly in _ERROR_PATTERNS:
        if any(kw in msg for kw in keywords):
            return friendly
    return f"播放出错：{exc}" if exc else "发生未知错误"


def show_error_snackbar(
    page: ft.Page,
    message: str,
    *,
    duration: int = 4000,
) -> None:
    """
    在页面底部弹出错误提示 SnackBar。

    Args:
        page: Flet Page 实例。
        message: 要显示的错误提示文本。
        duration: 显示时长（毫秒）。
    """
    try:
        page.show_dialog(
            ft.SnackBar(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=C_RED, size=18),
                        ft.Text(message, color=C_TEXT, size=13, expand=True),
                    ],
                    spacing=8,
                ),
                bgcolor=C_BG_PANEL,
                duration=duration,
            )
        )
    except Exception:
        logger.exception("无法显示错误提示 SnackBar")


def show_info_snackbar(
    page: ft.Page,
    message: str,
    *,
    duration: int = 3000,
) -> None:
    """在页面底部弹出信息提示 SnackBar。"""
    try:
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=C_TEXT, size=13),
                bgcolor=C_BG_PANEL,
                duration=duration,
            )
        )
    except Exception:
        logger.exception("无法显示信息提示 SnackBar")


def handle_error(
    exc: BaseException,
    page: Optional[ft.Page] = None,
    *,
    context: str = "",
    show_user: bool = True,
) -> str:
    """
    统一异常处理：记录日志 + 可选弹出用户提示。

    Args:
        exc: 捕获到的异常。
        page: Flet Page 实例（传入则弹出 SnackBar）。
        context: 异常发生的上下文描述（用于日志）。
        show_user: 是否向用户弹出提示。

    Returns:
        分类后的友好提示文本。
    """
    friendly = classify_error(exc)
    log_msg = f"{context}: {exc}" if context else str(exc)
    logger.error("%s", log_msg, exc_info=exc)

    if show_user and page is not None:
        show_error_snackbar(page, friendly)

    return friendly


def safe_async(coro_func, *, context: str = "", page: Optional[ft.Page] = None):
    """
    包装一个异步协程函数，捕获所有异常并处理。

    用法::

        asyncio.ensure_future(safe_async(_load, context="加载视频", page=page)())
    """

    async def _wrapper(*args, **kwargs):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as exc:
            handle_error(exc, page=page, context=context)

    return _wrapper
