"""启动入口 —— 组合根（Composition Root）+ 窗口装配。

依赖只在这里装配：Infra 实现 → Service → ViewModel → View。除本文件外，
任何层都不 new 下层具体实现，因此替换存储 / 播放器 / 扫描器只需改这一处，
验证脚本也能注入测试替身而不碰用户数据。

文件名固定为 ``bootstrap``：console script 与根目录 ``main.py`` 都指向
:func:`run`，仓库里只有一条启动路径。
"""

from __future__ import annotations

import asyncio
import logging
import sys
import traceback
from typing import Any

import ui

from cs_video_player._paths import assets_dir
from cs_video_player.infra import MediaController, PreferencesPort, ScannerPort
from cs_video_player.infra import JsonPreferences, FileSystemScanner
from cs_video_player.models.config import (
    APP_NAME,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from cs_video_player.service import PlaybackService
from cs_video_player.view import App
from cs_video_player.view.theme import BRAND_PRIMARY, THEME_MODE
from cs_video_player.viewmodel import AppViewModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


def _global_excepthook(
    exc_type: type[BaseException], exc_value: BaseException, exc_tb: Any
) -> None:
    """全局未捕获异常：记录日志，不崩溃。"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.exit(0)
    logger.critical(
        "未捕获的异常: %s: %s",
        exc_type.__name__,
        exc_value,
        exc_info=(exc_type, exc_value, exc_tb),
    )


def _async_exception_handler(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
    """asyncio 未处理异常：记录日志，不崩溃。"""
    exc = context.get("exception")
    msg = context.get("message", "异步任务异常")
    if exc:
        logger.error(
            "%s: %s\n%s",
            msg,
            exc,
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        )
    else:
        logger.error("%s", msg)


sys.excepthook = _global_excepthook


def build_viewmodel(
    *,
    preferences: PreferencesPort | None = None,
    scanner: ScannerPort | None = None,
    media: MediaController | None = None,
) -> AppViewModel:
    """依赖注入唯一出口：端口实现 → 业务服务 → 视图模型。"""
    service = PlaybackService(
        media=media or MediaController(),
        preferences=preferences or JsonPreferences(),
        scanner=scanner or FileSystemScanner(),
    )
    return AppViewModel(service)


def configure_page(page: ui.Page) -> None:
    """窗口、主题、标题一次性配好；组件不直接改窗口属性。"""
    page.title = APP_NAME
    page.padding = 0

    theme = ui.theme_state()
    theme.set_primary(BRAND_PRIMARY)
    theme.set_mode(THEME_MODE)
    ui.apply_theme(page, theme)

    window = page.window
    window.width = WINDOW_DEFAULT_WIDTH
    window.height = WINDOW_DEFAULT_HEIGHT
    window.min_width = WINDOW_MIN_WIDTH
    window.min_height = WINDOW_MIN_HEIGHT
    window.resizable = True
    window.title = APP_NAME


async def main(page: ui.Page) -> None:
    """应用入口：异常钩子 → 配置 → 装配 → 渲染。"""
    asyncio.get_running_loop().set_exception_handler(_async_exception_handler)
    configure_page(page)
    await page.window.center()

    try:
        vm = build_viewmodel()
    except Exception as exc:
        logger.exception("装配应用失败: %s", exc)
        raise

    page.render(App, vm=vm)
    logger.info(
        "窗口已就绪（%dx%d，flet %s）",
        WINDOW_DEFAULT_WIDTH,
        WINDOW_DEFAULT_HEIGHT,
        ui.FLET_VERSION,
    )


def run() -> None:
    """启动应用（根目录 main.py 与 console script 共用）。"""
    ui.run(main, assets_dir=str(assets_dir()))


__all__ = ["build_viewmodel", "configure_page", "main", "run"]
