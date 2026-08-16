"""
CS Video Player — 主入口

基于 Python 3.12 + Flet 0.86.5 + flet-video 的声明式本地视频播放器。
深度参考 PotPlayer 交互逻辑与 VLC 全格式能力。

架构:
    configs/     — 配置与主题常量
    core/        — 数据模型、播放引擎、播放控制器
    components/  — 声明式 UI 组件（侧边栏、播放区、根组件）
    utils/       — 工具函数（格式化、文件扫描、持久化存储、错误处理）

运行:
    python main.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import traceback

import flet as ft

from configs.app_config import (
    APP_NAME,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from configs.theme import C_BG_DARK, C_PRIMARY, C_TEXT
from components.app import App
from core.player_controller import PlayerController
from utils.error_handler import handle_error

# ─── 日志配置 ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


def _global_excepthook(exc_type, exc_value, exc_tb) -> None:
    """全局未捕获异常钩子：记录日志，不崩溃。"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.exit(0)
    logger.critical(
        "未捕获的异常: %s: %s",
        exc_type.__name__,
        exc_value,
        exc_info=(exc_type, exc_value, exc_tb),
    )


def _async_exception_handler(loop, context) -> None:
    """asyncio 未处理异常回调：记录日志，不崩溃。"""
    exc = context.get("exception")
    msg = context.get("message", "异步任务异常")
    if exc:
        logger.error("%s: %s\n%s", msg, exc, "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    else:
        logger.error("%s", msg)


sys.excepthook = _global_excepthook


async def main(page: ft.Page) -> None:
    """Flet 应用入口。"""
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_async_exception_handler)

    # ─── 窗口配置 ───
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = C_BG_DARK

    # 蓝色科技风主题
    page.theme = ft.Theme(
        color_scheme_seed=C_PRIMARY,
        color_scheme=ft.ColorScheme(
            primary=C_PRIMARY,
            on_primary="#FFFFFF",
            surface=C_BG_DARK,
            on_surface=C_TEXT,
        ),
    )

    page.window.width = WINDOW_DEFAULT_WIDTH
    page.window.height = WINDOW_DEFAULT_HEIGHT
    page.window.min_width = WINDOW_MIN_WIDTH
    page.window.min_height = WINDOW_MIN_HEIGHT
    page.window.resizable = True
    page.window.title = APP_NAME

    await page.window.center()

    # ─── 初始化播放控制器 ───
    try:
        controller = PlayerController()
        controller.load_settings()
    except Exception as exc:
        handle_error(exc, page=page, context="初始化播放控制器")
        raise

    # ─── 渲染根组件 ───
    page.render(App, controller=controller)


def main_entry():
    """Console script entry point."""
    ft.run(main)


if __name__ == "__main__":
    ft.run(main)
