"""隐藏窗口冒烟 —— 真实渲染 App 组件树，抓构建期异常。

``python scripts/verify_app.py`` 开一个不可见 Flet 窗口，装配真实的五层对象，
等组件 effect 全部执行完再关窗。纯逻辑由 ``test_logic.py`` 覆盖，分层约束由
``check_architecture.py`` 覆盖，这里只回答「界面能不能构建出来」。

测试替身通过组合根注入：设置 / 会话 / 近期记录落在临时目录，不碰用户数据。
``--demo`` 会创建几个临时视频占位文件并走完整的文件导入路径，用来验收列表行、
选中态与排序条。``--shot`` 可导出界面截图。

输出里的 ``VERIFY_OK`` / ``VERIFY_FAIL`` 是给 CI 用的稳定标记。
"""

from __future__ import annotations

import asyncio
import logging
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SHOT: str = ""
DEMO: bool = False

import ui  # noqa: E402

from cs_video_player._paths import assets_dir, project_root  # noqa: E402
from cs_video_player.bootstrap import build_viewmodel, configure_page  # noqa: E402
from cs_video_player.infra import FileSystemScanner, JsonPreferences  # noqa: E402
from cs_video_player.view import App  # noqa: E402

_PROBLEMS: list[str] = []


class _Collector(logging.Handler):
    """收集框架在构建期打出的 ERROR / CRITICAL，避免被 stderr 淹没。"""

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR:
            _PROBLEMS.append(f"{record.name}: {record.getMessage()}")


async def _run(page: ui.Page) -> None:
    try:
        root = Path(tempfile.mkdtemp(prefix="cvp-verify-"))
        preferences = JsonPreferences(root=root)
        vm = build_viewmodel(preferences=preferences, scanner=FileSystemScanner())

        configure_page(page)
        if DEMO:
            names = (
                "星际穿越.2014.mkv",
                "纪录短片 · 城市晨光.mp4",
                "会议回放 2026-11-12.mov",
                "演示片段.webm",
            )
            paths: tuple[str, ...] = tuple(
                str((root / name).touch() or (root / name)) for name in names
            )
            vm.on_files_selected(paths)
        page.render(App, vm=vm)
        page.update()
        await asyncio.sleep(1.2)

        has_root = getattr(page, "controls", None) is not None
        registry = getattr(page, "_services", None)
        registered = [
            type(service).__name__ for service in (getattr(registry, "_services", []) or [])
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
