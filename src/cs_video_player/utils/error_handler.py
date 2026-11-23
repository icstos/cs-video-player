"""全局异常处理 —— 把底层异常翻译成一句人话，并给出一次性回执。

三层职责分得很清楚：

* :func:`classify_error` 是纯函数（异常 → 中文提示），可单测；
* :func:`show_error` / :func:`show_info` 只负责展示，走 cs-ui 的 ``Message``
  （顶部居中、同款合并、自动消失）。不再用 SnackBar：弹层栈一次只挂一条，
  连续两次失败不该叠两条提示把画面压住；
* :func:`handle_error` 组合日志 + 展示 + 返回提示，是业务代码唯一该调的入口。
"""

from __future__ import annotations

import logging
from typing import Optional

import ui
from ui import Message, StyleType

logger = logging.getLogger(__name__)

# ─── 错误分类与友好提示（顺序即优先级） ───
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
    """根据异常信息推断面向用户的友好提示。"""
    msg = str(exc).lower()
    for keywords, friendly in _ERROR_PATTERNS:
        if any(kw in msg for kw in keywords):
            return friendly
    return f"播放出错：{exc}" if exc else "发生未知错误"


def show_error(page: ui.Page, message: str, *, duration: int = 4000) -> None:
    """错误回执：红色语气、四秒自走、同款合并。"""
    try:
        Message(message, style_type=StyleType.ERROR, duration=duration).show(page)
    except Exception:
        logger.exception("无法显示错误提示")


def show_info(page: ui.Page, message: str, *, duration: int = 3000) -> None:
    """信息回执：中性语气、三秒自走。"""
    try:
        Message(message, style_type=StyleType.INFO, duration=duration).show(page)
    except Exception:
        logger.exception("无法显示信息提示")


# 兼容旧调用点的别名（内部实现已换成 ui.Message）。
show_error_snackbar = show_error
show_info_snackbar = show_info


def handle_error(
    exc: BaseException,
    page: Optional[ui.Page] = None,
    *,
    context: str = "",
    show_user: bool = True,
) -> str:
    """统一异常处理：日志 + 可选回执，并返回分类后的提示文本。"""
    friendly = classify_error(exc)
    log_msg = f"{context}: {exc}" if context else str(exc)
    logger.error("%s", log_msg, exc_info=exc)

    if show_user and page is not None:
        show_error(page, friendly)
    return friendly


def safe_async(coro_func, *, context: str = "", page: Optional[ui.Page] = None):
    """包装异步函数，捕获所有异常并交给 :func:`handle_error`。

    用法::

        asyncio.ensure_future(safe_async(_load, context="加载视频", page=page)())
    """

    async def _wrapper(*args, **kwargs):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as exc:
            handle_error(exc, page=page, context=context)

    return _wrapper
