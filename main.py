"""
CS Video Player — 主入口

基于 Python 3.12 + Flet 0.86.5 + flet-video 的声明式本地视频播放器。
深度参考 PotPlayer 交互逻辑与 VLC 全格式能力。

架构:
    configs/     — 配置与主题常量
    core/        — 数据模型、播放引擎、播放控制器
    components/  — 声明式 UI 组件（侧边栏、播放区、根组件）
    utils/       — 工具函数（格式化、文件扫描、持久化存储）

运行:
    python main.py
"""

from __future__ import annotations

import logging
import sys

import flet as ft

from configs.app_config import (
    APP_NAME,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from configs.theme import C_BG_DARK
from components.app import App
from core.player_controller import PlayerController

# ─── 日志配置 ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)


async def main(page: ft.Page) -> None:
    """Flet 应用入口。"""
    # ─── 窗口配置 ───
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = C_BG_DARK

    page.window.width = WINDOW_DEFAULT_WIDTH
    page.window.height = WINDOW_DEFAULT_HEIGHT
    page.window.min_width = WINDOW_MIN_WIDTH
    page.window.min_height = WINDOW_MIN_HEIGHT
    page.window.resizable = True
    page.window.title = APP_NAME

    await page.window.center()

    # ─── 初始化播放控制器 ───
    controller = PlayerController()
    controller.load_settings()

    # ─── 渲染根组件 ───
    page.render(App, controller=controller)


if __name__ == "__main__":
    ft.run(main)
