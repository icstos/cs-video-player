"""隐藏窗口冒烟 —— 真实渲染整棵 App 组件树，抓构建期异常。

``python scripts/verify_app.py`` 会开一个不可见的 Flet 窗口，把真正的
``PlayerController`` 与 ``App`` 挂上去，等一秒让 use_effect / 子组件全部执行完，
再关窗。纯逻辑由 ``test_logic.py`` 覆盖，这里只回答「界面能不能构建出来」。

测试替身：会话恢复 / 设置与会话落盘在验证期间是 no-op，既不弹窗干扰，
也不改动用户 ``~/.cs_video_player`` 里的真实数据。

输出里的 ``VERIFY_OK`` / ``VERIFY_FAIL`` 是给 CI 用的稳定标记。
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# src 布局：项目包在 src/ 下，脚本在仓库根的 scripts/ 下。
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

#: ``python scripts/verify_app.py --shot output/app.png`` 额外导出一张界面截图。
#: ``--demo`` 会注入几条假播放列表项，用来验收列表行、选中态与排序条。
SHOT: str = ""
DEMO: bool = False

import ui  # noqa: E402

from cs_video_player._paths import assets_dir, project_root  # noqa: E402
from cs_video_player.bootstrap import configure_page  # noqa: E402
from cs_video_player.components.app import App  # noqa: E402
from cs_video_player.core.player_controller import PlayerController  # noqa: E402

_PROBLEMS: list[str] = []


class _Collector(logging.Handler):
    """收集框架在构建期打出的 ERROR / CRITICAL，避免被 stderr 淹没。"""

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR:
            _PROBLEMS.append(f"{record.name}: {record.getMessage()}")


async def _run(page: ui.Page) -> None:
    # 不碰真实用户数据
    PlayerController.get_saved_session = lambda self: None
    PlayerController.save_settings = lambda self: None
    PlayerController.save_session = lambda self: None

    try:
        configure_page(page)
        controller = PlayerController()
        controller.load_settings()
        if DEMO:
            from datetime import datetime

            from cs_video_player.core.models import PlaylistItem

            controller.state.playlist = [
                PlaylistItem(
                    path=f"D:/media/{name}",
                    title=name,
                    size=size,
                    modified=datetime(2026, 11, 10 + i),
                )
                for i, (name, size) in enumerate(
                    (
                        ("星际穿越.2014.mkv", 8_932_000_000),
                        ("纪录短片 · 城市晨光.mp4", 246_000_000),
                        ("会议回放 2026-11-12.mov", 1_504_000_000),
                        ("演示片段.webm", 18_400_000),
                    )
                )
            ]
            controller.state.current_index = 0
        page.render(App, controller=controller)
        page.update()
        await asyncio.sleep(1.2)

        # page.controls 在 page.render 后是组件占位（不是列表），只看有没有挂上。
        has_root = getattr(page, "controls", None) is not None
        # Flet 1.1 的 Service 自动注册进 page._services 注册表，而不是旧的
        # page.services 列表；真正决定「能不能弹框」的是 service 是否挂到 page。
        registry = getattr(page, "_services", None)
        registered = [
            type(s).__name__ for s in (getattr(registry, "_services", []) or [])
        ]
        probe = ui.FileDialog()
        try:
            probe._attached()  # noqa: SLF001 —— 用库自己的附着检查做验证
            dialog_ok = True
        except Exception:
            dialog_ok = False
        print(
            f"VERIFY_INFO has_root={has_root} registered={registered} "
            f"dialog_ok={dialog_ok} theme={ui.current_mode()} flet={ui.FLET_VERSION}"
        )
        if not has_root:
            _PROBLEMS.append("根组件没有挂到页面上")
        if "FilePicker" not in registered:
            _PROBLEMS.append("文件对话框服务没有注册到页面")
        if not dialog_ok:
            _PROBLEMS.append("文件对话框服务没有绑定到 page，打开文件会失败")

        if SHOT:
            try:
                page.enable_screenshots = True
                await asyncio.sleep(0.4)
                png = await page.take_screenshot(delay=200)
                target = project_root() / SHOT
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(png)
                print(f"SHOT_OK {target} ({len(png)} bytes)")
            except Exception as exc:  # noqa: BLE001 —— 截图是可选能力
                print(f"SHOT_FAIL {type(exc).__name__}: {exc}")
    except Exception as exc:  # noqa: BLE001
        _PROBLEMS.append(f"渲染异常: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        print("VERIFY_OK" if not _PROBLEMS else "VERIFY_FAIL")
        for problem in _PROBLEMS:
            print("VERIFY_PROBLEM", problem)
        # 关窗后留一拍：flet 的 destroy 是异步下发的，紧接着回收 session 会
        # 撞上 "Session closed"，日志里多一段无意义的 traceback。
        try:
            await page.window.close()
            await asyncio.sleep(0.3)
        except Exception:
            pass


def main() -> None:
    global SHOT, DEMO
    args = sys.argv[1:]
    DEMO = "--demo" in args
    if "--shot" in args:
        index = args.index("--shot")
        SHOT = args[index + 1] if index + 1 < len(args) else "output/app.png"
    logging.getLogger().addHandler(_Collector())
    ui.run(_run, view=ui.AppView.FLET_APP_HIDDEN, assets_dir=str(assets_dir()))


if __name__ == "__main__":
    main()
