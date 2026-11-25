"""view / app —— 应用根视图：状态订阅、宿主事件适配、组件装配。

只做 UI 层该做的事：

* 订阅 ViewModel，状态变化触发一次重渲染（UI = f(AppState)）；
* 把窗口事件 / 键盘事件 / 文件对话框结果翻译成 ViewModel 调用；
* 根据状态展示一次性回执与会话恢复确认框。

没有任何业务判断：快捷键含义、文件导入规则、会话恢复逻辑都在 ViewModel /
Service 里。排序结果用 memo 缓存，位置轮询不会反复重排列表。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import ui

from cs_video_player.models.config import APP_NAME, VIDEO_EXTENSIONS
from cs_video_player.models.entities import KeyInfo
from cs_video_player.models.enums import FileRequestKind
from cs_video_player.view.kit import confirm_dialog, toast
from cs_video_player.view.player_area import PlayerArea
from cs_video_player.view.sidebar import Sidebar
from cs_video_player.viewmodel import AppViewModel

logger = logging.getLogger(__name__)

VIDEO_FILTER: tuple[str, ...] = tuple(
    sorted(ext.lstrip(".") for ext in VIDEO_EXTENSIONS)
)


@ui.component
def App(vm: AppViewModel) -> ui.Control:
    """根组件：从 ViewModel 取一帧状态，向下传给两个纯视图。"""
    tick: int
    set_tick: Any
    tick, set_tick = ui.use_state(0)

    def _on_state_change() -> None:
        set_tick(lambda value: value + 1)

    unsubscribe_ref = ui.use_ref(None)

    def _subscribe() -> None:
        unsubscribe_ref.current = vm.subscribe(_on_state_change)

    def _cleanup() -> None:
        if unsubscribe_ref.current is not None:
            unsubscribe_ref.current()
        vm.detach()

    ui.use_effect(_subscribe, dependencies=[])
    state = vm.state

    display = ui.use_memo(
        lambda: vm.sorted_playlist(), [tick, state.sort_key, state.playlist]
    )

    page = ui.context.page
    dialog = ui.use_ref(ui.FileDialog).current

    # ─── 文件对话框：状态里的请求驱动 ───
    def _handle_file_request() -> None:
        request = state.file_request
        if request is None:
            return

        async def _pick() -> None:
            if request.kind == FileRequestKind.FILES:
                paths = await dialog.pick_files(
                    title="选择视频文件", extensions=VIDEO_FILTER, multiple=True
                )
                if paths:
                    vm.on_files_selected(tuple(str(path) for path in paths))
                else:
                    vm.cancel_file_request()
            else:
                folder = await dialog.pick_directory(title="选择视频文件夹")
                vm.on_folder_selected(str(folder) if folder is not None else None)

        asyncio.ensure_future(_pick())

    ui.use_effect(_handle_file_request, dependencies=[state.file_request])

    # ─── 启动会话确认 ───
    def _check_session() -> None:
        session = state.session
        if session is None:
            return

        def _resume(e: Any) -> None:
            page.pop_dialog()
            vm.confirm_restore()

        def _dismiss(e: Any) -> None:
            page.pop_dialog()
            vm.dismiss_restore()

        page.show_dialog(
            confirm_dialog(
                heading="恢复上次播放",
                message=(
                    f"检测到上次未播放完的列表（{len(session.items)} 个视频）。\n"
                    "是否从上次位置继续播放？"
                ),
                cancel_label="不恢复",
                confirm_label="继续播放",
                on_cancel=_dismiss,
                on_confirm=_resume,
            )
        )

    ui.use_effect(_check_session, dependencies=[state.session])

    # ─── 键盘：平台事件 → 纯 KeyInfo ───
    def _on_keyboard(e: ui.KeyboardEvent) -> None:
        vm.handle_key(KeyInfo(e.key.lower(), bool(e.ctrl), bool(e.shift)))

    def _setup_keyboard() -> None:
        page.on_keyboard_event = _on_keyboard

    ui.use_effect(_setup_keyboard, dependencies=[])

    # ─── 窗口关闭：先落盘，再销毁 ───
    def _setup_window_close() -> None:
        page.window.prevent_close = True

        async def _destroy() -> None:
            try:
                await page.window.destroy()
            except RuntimeError as exc:
                # 关窗时会话可能先被回收，这类噪音不影响落盘与退出。
                if "session closed" not in str(exc).lower():
                    raise

        def _on_window_event(e: ui.WindowEvent) -> None:
            if e.type == ui.WindowEventType.CLOSE:
                vm.on_window_close()
                asyncio.ensure_future(_destroy())

        page.window.on_event = _on_window_event

    ui.use_effect(_setup_window_close, dependencies=[])

    # ─── 标题跟随片名 ───
    def _sync_title() -> None:
        page.title = f"{state.title} — {APP_NAME}" if state.title else APP_NAME
        page.update()

    ui.use_effect(_sync_title, dependencies=[state.title])

    # ─── 一次性回执 ───
    def _show_notice() -> None:
        if state.notice is None:
            return
        toast(page, state.notice.message, tone=state.notice.tone.value)
        vm.acknowledge_notice()

    ui.use_effect(_show_notice, dependencies=[state.notice])

    # ─── 卸载时退订（不在首帧误执行） ───
    ui.use_effect(lambda: None, dependencies=[], cleanup=_cleanup)

    # 侧栏只在自身输入变化时重建；位置轮询不重排 / 不重建列表行。
    sidebar = ui.use_memo(
        lambda: Sidebar(
            display=display,
            current_index=state.current_index,
            sort_key=state.sort_key,
            recents=tuple(state.recents),
            on_play=vm.play_at,
            on_remove=vm.remove_item,
            on_reorder=vm.reorder,
            on_sort=vm.set_sort,
            on_open_file=vm.request_open_files,
            on_open_folder=vm.request_open_folder,
            on_open_recent=vm.open_recent,
            on_clear_playlist=vm.clear_playlist,
            on_remove_recent=vm.remove_recent,
            on_toggle_visible=vm.toggle_sidebar,
            sidebar_visible=state.sidebar_visible,
            sidebar_width=state.sidebar_width,
        ),
        [
            display,
            state.current_index,
            state.sort_key,
            state.recents,
            state.sidebar_visible,
            state.sidebar_width,
        ],
    )

    return ui.Row(
        controls=[
            sidebar,
            PlayerArea(state=state, vm=vm),
        ],
        expand=True,
        spacing=0,
    )
