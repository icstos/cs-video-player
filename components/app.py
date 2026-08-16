"""
应用根组件 — 连接 PlayerController 与 UI 组件的声明式根。
管理全局状态、FilePicker 服务、键盘快捷键。
"""

from __future__ import annotations

import asyncio
import logging

import flet as ft

from configs.app_config import KEYBOARD_SHORTCUTS, SIDEBAR_WIDTH
from components.sidebar import Sidebar
from components.player_area import PlayerArea
from core.models import SortKey
from core.player_controller import PlayerController
from utils.file_scanner import make_playlist_item, scan_videos

logger = logging.getLogger(__name__)


@ft.component
def App(controller: PlayerController):
    """应用根组件。"""
    # ─── 重渲染驱动：controller 状态变更时触发 tick ───
    tick, set_tick = ft.use_state(0)

    def _on_state_change(_state):
        set_tick(lambda t: t + 1)

    def _register_listener():
        controller.add_listener(_on_state_change)

    ft.use_effect(_register_listener, dependencies=[])

    # ─── 全局状态快照 ───
    state = controller.state
    play_nonce = controller.play_nonce
    recents = controller.recents
    sort_key = controller.sort_key
    sidebar_width, set_sidebar_width = ft.use_state(float(SIDEBAR_WIDTH))

    # ─── FilePicker 服务 ───
    picker_ref = ft.use_ref(lambda: ft.FilePicker())

    page = ft.context.page

    def _register_picker():
        picker = picker_ref.current
        if picker and picker not in page.services:
            page.services.append(picker)
            page.update()

    ft.use_effect(_register_picker, dependencies=[])

    # ─── 键盘快捷键 ───
    def _on_keyboard(e: ft.KeyboardEvent):
        key = e.key.lower()
        action = KEYBOARD_SHORTCUTS.get(key)
        if action is None:
            return

        if action == "play_pause":
            async def _do():
                await controller.engine.play_or_pause()
                controller.toggle_playing()
            asyncio.ensure_future(_do())
        elif action == "seek_backward":
            asyncio.ensure_future(controller.engine.seek_relative(-5000))
        elif action == "seek_forward":
            asyncio.ensure_future(controller.engine.seek_relative(5000))
        elif action == "volume_up":
            new_vol = min(100.0, state.volume + 5.0)
            controller.set_volume(new_vol)
        elif action == "volume_down":
            new_vol = max(0.0, state.volume - 5.0)
            controller.set_volume(new_vol)
        elif action == "toggle_mute":
            controller.toggle_mute()
        elif action == "toggle_fullscreen":
            controller.toggle_fullscreen()
        elif action == "next_track":
            controller.play_next()
        elif action == "prev_track":
            controller.play_prev()
        elif action == "exit_fullscreen":
            if state.is_fullscreen:
                controller.set_fullscreen(False)

    def _setup_keyboard():
        page.on_keyboard_event = _on_keyboard

    ft.use_effect(_setup_keyboard, dependencies=[])

    # ─── 窗口标题同步 ───
    def _sync_title():
        if state.has_video:
            page.title = f"{state.current_item.title} — CS Video Player"
        else:
            page.title = "CS Video Player"
        page.update()

    ft.use_effect(_sync_title, dependencies=[play_nonce])

    # ─── 播放控制回调 ───
    def _play_at(idx: int):
        controller.play_at(idx)

    def _play_next():
        controller.play_next()

    def _play_prev():
        controller.play_prev()

    def _on_track_change(idx: int):
        controller.on_track_change(idx)

    def _on_complete():
        controller.on_complete()

    def _toggle_play_mode():
        controller.cycle_play_mode()

    def _on_toggle_play():
        controller.toggle_playing()

    def _on_seek(pos: int):
        controller.update_position(pos)

    def _on_set_volume(vol: float):
        controller.set_volume(vol)

    def _on_toggle_mute():
        controller.toggle_mute()

    def _on_toggle_fullscreen():
        controller.toggle_fullscreen()

    def _on_set_rate(rate: float):
        controller.set_playback_rate(rate)

    def _on_position_change(ms: int):
        controller.update_position(ms)

    def _on_duration_change(ms: int):
        controller.update_duration(ms)

    def _on_sort(key: SortKey):
        controller.set_sort_key(key)

    def _on_remove(idx: int):
        controller.remove_from_playlist(idx)

    def _on_clear_playlist():
        controller.clear_playlist()

    def _on_remove_recent(path: str):
        if path == "":
            controller.clear_recents()
        else:
            controller.remove_recent(path)
        page.update()

    # ─── File 操作 ───
    async def _open_file():
        picker = picker_ref.current
        if not picker:
            return
        try:
            files = await picker.pick_files(
                dialog_title="选择视频文件",
                file_type=ft.FilePickerFileType.VIDEO,
            )
            if not files:
                return
            f = files[0]
            path = f.path or f.name
            item = make_playlist_item(path)
            controller.set_playlist([item])
        except Exception as e:
            logger.error("打开文件失败: %s", e)

    async def _open_folder():
        picker = picker_ref.current
        if not picker:
            return
        try:
            folder = await picker.get_directory_path(
                dialog_title="选择视频文件夹"
            )
            if not folder:
                return
            items = scan_videos(folder)
            if not items:
                page.overlay.append(
                    ft.SnackBar(content=ft.Text("该文件夹下未找到视频文件"))
                )
                page.update()
                return
            controller.set_playlist(items)
        except Exception as e:
            logger.error("打开文件夹失败: %s", e)

    def _open_recent(path: str):
        controller.play_recent(path)

    # ─── 排序后列表 ───
    display = controller.get_sorted_playlist()

    # ─── 卸载时保存设置 ───
    def _on_unmount():
        controller.save_settings()

    ft.use_effect(_on_unmount, dependencies=[])

    return ft.Row(
        controls=[
            Sidebar(
                display=display,
                current_index=state.current_index,
                sort_key=sort_key,
                recents=recents,
                on_play=_play_at,
                on_remove=_on_remove,
                on_sort=_on_sort,
                on_open_file=_open_file,
                on_open_folder=_open_folder,
                on_open_recent=_open_recent,
                on_clear_playlist=_on_clear_playlist,
                on_remove_recent=_on_remove_recent,
                sidebar_width=sidebar_width,
            ),
            PlayerArea(
                state=state,
                engine=controller.engine,
                play_nonce=play_nonce,
                on_track_change=_on_track_change,
                on_complete=_on_complete,
                on_prev=_play_prev,
                on_next=_play_next,
                on_toggle_play_mode=_toggle_play_mode,
                on_toggle_play=_on_toggle_play,
                on_seek=_on_seek,
                on_set_volume=_on_set_volume,
                on_toggle_mute=_on_toggle_mute,
                on_toggle_fullscreen=_on_toggle_fullscreen,
                on_set_rate=_on_set_rate,
                on_position_change=_on_position_change,
                on_duration_change=_on_duration_change,
            ),
        ],
        expand=True,
        spacing=0,
    )
