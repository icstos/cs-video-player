"""
CS Video Player — 主入口

基于 Python 3.12 + cs-ui（底层 Flet）+ ui.display.media 的声明式本地视频播放器。
深度参考 PotPlayer 交互逻辑与 VLC 全格式能力。

架构::

    configs/     — 应用常量 + 设计层（cs-ui 令牌的语义投影）
    core/        — 数据模型、播放引擎、播放控制器（纯逻辑，不碰界面）
    components/  — 声明式 UI：kit（UI 词汇）/ sidebar / control_bar / player_area / app
    utils/       — 格式化、文件扫描、持久化、错误处理（纯函数优先）

主题只有 cs-ui 一个事实源：这里告诉它「品牌色 + 固定深色」，
:func:`ui.apply_theme` 一次性下发明暗两套主题，组件里的角色色由 Flutter 解析。
自绘部分读同一个 :data:`configs.theme.PALETTE`，因此不会出现两种蓝。

运行::

    python main.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import traceback

import ui

from components.app import App
from configs.app_config import (
    APP_NAME,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from configs.theme import BRAND_PRIMARY, THEME_MODE
from core.player_controller import PlayerController
from utils.error_handler import handle_error

# ─── 日志：必须在 ui.run 之前装好，框架日志才会一起进 handler ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


def _global_excepthook(exc_type, exc_value, exc_tb) -> None:
    """全局未捕获异常：记录日志，不崩溃。"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.exit(0)
    logger.critical(
        "未捕获的异常: %s: %s",
        exc_type.__name__,
        exc_value,
        exc_info=(exc_type, exc_value, exc_tb),
    )


def _async_exception_handler(loop, context) -> None:
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


def configure_page(page: ui.Page) -> None:
    """窗口、主题、标题一次性配好；组件不直接改 page 属性。"""
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
    """应用入口：装配 → 配置 → 渲染。"""
    # 异常钩子要装在事件循环内，才管得到 asyncio 任务的未捕获异常。
    asyncio.get_running_loop().set_exception_handler(_async_exception_handler)

    configure_page(page)
    await page.window.center()

    try:
        controller = PlayerController()
        controller.load_settings()
    except Exception as exc:
        handle_error(exc, page=page, context="初始化播放控制器")
        raise

    page.render(App, controller=controller)
    logger.info(
        "窗口已就绪（%dx%d，flet %s）",
        WINDOW_DEFAULT_WIDTH,
        WINDOW_DEFAULT_HEIGHT,
        ui.FLET_VERSION,
    )


def main_entry() -> None:
    """Console script 入口。"""
    ui.run(main)


if __name__ == "__main__":
    ui.run(main)
