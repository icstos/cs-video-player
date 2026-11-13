"""应用根组件 —— 把控制器、页面服务与两个视图接起来。

职责限于「编排」：订阅控制器、注册全局副作用（快捷键 / 窗口关闭 / 会话恢复 /
标题同步 / 错误回执）、把意图翻译成控制器调用。渲染本身交给 ``Sidebar`` 与
``PlayerArea``，这里不画任何控件样式。

几个刻意的选择：

* **文件对话框用 cs-ui 的 ``FileDialog``**：构造即注册到页面，省掉手动维护
  ``page.services`` 的样板；它按扩展名精确过滤，比系统 VIDEO 类型更贴近本项目
  支持的格式表。
* **排序结果用 ``use_memo`` 缓存**：500 项列表不必在每次位置轮询引发的重渲染里
  重新排序，只有列表或排序键变化时才重算。
* **卸载时保存设置**：``use_effect`` 返回清理函数，而不是把「保存」误当副作用
  在首帧执行。
"""

from __future__ import annotations

import asyncio
import logging

import ui

from components.kit import confirm_dialog, toast
from components.player_area import PlayerArea
from components.sidebar import Sidebar
from configs.app_config import (
    KEYBOARD_SHORTCUTS,
    PLAYBACK_SPEEDS,
    SEEK_STEP_SHORT,
    SIDEBAR_DEFAULT_VISIBLE,
    SIDEBAR_DEFAULT_WIDTH,
    SPEED_MAX,
    SPEED_MIN,
    VIDEO_EXTENSIONS,
    VOLUME_STEP,
)
from core.player_controller import PlayerController
from utils.error_handler import handle_error
from utils.file_scanner import make_playlist_items, scan_videos

logger = logging.getLogger(__name__)

#: 对话框扩展名（不带点），来自应用支持的格式表 —— 只有一个事实源。
VIDEO_FILTER = tuple(sorted(ext.lstrip(".") for ext in VIDEO_EXTENSIONS))


@ui.component
def App(controller: PlayerController):
    """应用根组件。"""
    # ─── 控制器 → 重渲染 ───
    tick, set_tick = ui.use_state(0)

    def _on_state_change(_state):
        set_tick(lambda t: t + 1)

    def _register_listener():
        controller.add_listener(_on_state_change)

    ui.use_effect(_register_listener, dependencies=[])

    state = controller.state
    play_nonce = controller.play_nonce
    recents = controller.recents
    sort_key = controller.sort_key

    sidebar_visible, set_sidebar_visible = ui.use_state(SIDEBAR_DEFAULT_VISIBLE)
    session_checked = ui.use_ref(False)
    sidebar_width = float(SIDEBAR_DEFAULT_WIDTH)

    #: 排序只在「列表 / 排序键」变化时重算，位置轮询不触发排序。
    display = ui.use_memo(
        lambda: controller.get_sorted_playlist(), [tick, sort_key]
    )

    page = ui.context.page
    # 构造即注册到当前页（cs-ui 的 FileDialog 契约），每个会话只建一份。
    file_dialog = ui.use_ref(ui.FileDialog).current

    # ─── 启动时询问是否恢复上次会话 ───
    def _check_session():
        if session_checked.current:
            return
        session_checked.current = True
        session = controller.get_saved_session()
        if not session:
            return
        items, idx, pos, mode = session

        def _resume(e):
            page.pop_dialog()
            controller.restore_session(items, idx, pos, mode)

        def _dismiss(e):
            page.pop_dialog()

        page.show_dialog(
            confirm_dialog(
                heading="恢复上次播放",
                message=(
                    f"检测到上次未播放完的列表（{len(items)} 个视频）。\n"
                    "是否从上次位置继续播放？"
                ),
                cancel_label="不恢复",
                confirm_label="继续播放",
                on_cancel=_dismiss,
                on_confirm=_resume,
            )
        )

    ui.use_effect(_check_session, dependencies=[])

    # ─── 倍速档位步进（纯计算，快捷键与菜单共用） ───
    def _step_speed(direction: int) -> float | None:
        current = state.playback_rate
        candidates = PLAYBACK_SPEEDS if direction > 0 else tuple(reversed(PLAYBACK_SPEEDS))
        for value in candidates:
            changed = (
                value > current + 1e-9
                if direction > 0
                else value < current - 1e-9
            )
            if changed:
                return min(value, SPEED_MAX) if direction > 0 else max(value, SPEED_MIN)
        return SPEED_MAX if direction > 0 else SPEED_MIN

    # ─── 键盘快捷键 ───
    def _on_keyboard(e: ui.KeyboardEvent):
        key = e.key.lower()

        if e.ctrl:
            if key == "o":
                asyncio.ensure_future(_open_folder() if e.shift else _open_file())
            return

        action = KEYBOARD_SHORTCUTS.get(key)
        if action is None:
            return

        if action == "play_pause":
            async def _do():
                await controller.engine.play_or_pause()
                controller.toggle_playing()
            asyncio.ensure_future(_do())
        elif action == "seek_backward":
            asyncio.ensure_future(
                controller.engine.seek_relative(-SEEK_STEP_SHORT * (2 if e.shift else 1))
            )
        elif action == "seek_forward":
            asyncio.ensure_future(
                controller.engine.seek_relative(SEEK_STEP_SHORT * (2 if e.shift else 1))
            )
        elif action == "volume_up":
            controller.set_volume(min(100.0, state.volume + VOLUME_STEP))
        elif action == "volume_down":
            controller.set_volume(max(0.0, state.volume - VOLUME_STEP))
        elif action in ("speed_up", "speed_down"):
            rate = _step_speed(+1 if action == "speed_up" else -1)
            if rate is not None:
                controller.set_playback_rate(rate)
        elif action == "toggle_mute":
            controller.toggle_mute()
        elif action == "toggle_fullscreen":
            controller.toggle_fullscreen()
        elif action == "next_track":
            controller.play_next()
        elif action == "prev_track":
            controller.play_prev()
        elif action == "stop":
            async def _do_stop():
                await controller.engine.stop()
                controller.stop()
            asyncio.ensure_future(_do_stop())
        elif action == "toggle_remaining_time":
            controller.toggle_remaining_time()
        elif action == "exit_fullscreen":
            if state.is_fullscreen:
                controller.set_fullscreen(False)
        elif action == "remove_current":
            controller.remove_current()

    def _setup_keyboard():
        page.on_keyboard_event = _on_keyboard

    ui.use_effect(_setup_keyboard, dependencies=[])

    # ─── 窗口关闭：先落盘，再销毁 ───
    def _setup_window_close():
        page.window.prevent_close = True

        def _on_window_event(e: ui.WindowEvent):
            if e.type == ui.WindowEventType.CLOSE:
                controller.save_settings()
                controller.save_session()
                asyncio.ensure_future(page.window.destroy())

        page.window.on_event = _on_window_event

    ui.use_effect(_setup_window_close, dependencies=[])

    # ─── 标题跟随当前片名 ───
    def _sync_title():
        page.title = (
            f"{state.current_item.title} — CS Video Player"
            if state.has_video
            else "CS Video Player"
        )
        page.update()

    ui.use_effect(_sync_title, dependencies=[play_nonce])

    # ─── 错误回执 ───
    def _on_error_change():
        if state.last_error:
            toast(page, state.last_error, tone="error", duration=4000)
            controller.clear_error()

    ui.use_effect(_on_error_change, dependencies=[state.last_error])

    # ─── 卸载时保存设置（use_effect 的 cleanup，不在首帧误执行） ───
    ui.use_effect(
        lambda: None,
        dependencies=[],
        cleanup=lambda: controller.save_settings(),
    )

    # ─── 文件操作 ───
    async def _open_file():
        try:
            paths = await file_dialog.pick_files(
                title="选择视频文件",
                extensions=VIDEO_FILTER,
                multiple=True,
            )
            if not paths:
                return
            items = make_playlist_items([str(p) for p in paths])
            if items:
                controller.add_files(items, replace=True)
            else:
                toast(page, "所选文件均不受支持", tone="warning")
        except Exception as exc:
            handle_error(exc, page=page, context="打开文件")

    async def _open_folder():
        try:
            folder = await file_dialog.pick_directory(title="选择视频文件夹")
            if folder is None:
                return
            items = scan_videos(str(folder))
            if not items:
                toast(page, "该文件夹下未找到视频文件", tone="warning")
                return
            controller.add_files(items, replace=True)
        except Exception as exc:
            handle_error(exc, page=page, context="打开文件夹")

    def _open_recent(path: str):
        try:
            controller.play_recent(path)
        except Exception as exc:
            handle_error(exc, page=page, context="打开最近文件")

    def _remove_recent(path: str):
        if path == "":
            controller.clear_recents()
        else:
            controller.remove_recent(path)
        # 记录变更不走 _notify，本地触发一次重渲染即可。
        set_tick(lambda t: t + 1)

    def _toggle_sidebar():
        set_sidebar_visible(lambda v: not v)

    # ─── 视图 ───
    return ui.Row(
        controls=[
            Sidebar(
                display=display,
                current_index=state.current_index,
                sort_key=sort_key,
                recents=recents,
                on_play=controller.play_at,
                on_remove=controller.remove_from_playlist,
                on_reorder=controller.reorder,
                on_sort=controller.set_sort_key,
                on_open_file=_open_file,
                on_open_folder=_open_folder,
                on_open_recent=_open_recent,
                on_clear_playlist=controller.clear_playlist,
                on_remove_recent=_remove_recent,
                on_toggle_visible=_toggle_sidebar,
                sidebar_visible=sidebar_visible,
                sidebar_width=sidebar_width,
            ),
            PlayerArea(
                state=state,
                engine=controller.engine,
                play_nonce=play_nonce,
                on_track_change=controller.on_track_change,
                on_complete=controller.on_complete,
                on_prev=controller.play_prev,
                on_next=controller.play_next,
                on_stop=controller.stop,
                on_toggle_play_mode=controller.cycle_play_mode,
                on_toggle_play=controller.toggle_playing,
                on_seek=controller.update_position,
                on_set_volume=controller.set_volume,
                on_toggle_mute=controller.toggle_mute,
                on_toggle_fullscreen=controller.toggle_fullscreen,
                on_set_rate=controller.set_playback_rate,
                on_position_change=controller.update_position,
                on_duration_change=controller.update_duration,
                on_toggle_remaining_time=controller.toggle_remaining_time,
                on_toggle_sidebar=_toggle_sidebar,
                sidebar_visible=sidebar_visible,
                on_open_file=_open_file,
            ),
        ],
        expand=True,
        spacing=0,
    )
