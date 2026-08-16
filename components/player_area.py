# -*- coding: utf-8 -*-
"""
PlayerArea 组件 — 视频显示区 + 自定义控制栏。

声明式组件：接收播放器状态与回调，高频状态隔离在组件内部。
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Callable

import flet as ft
from flet_video import Video, VideoControlsMode

from configs.app_config import (
    CONTROLS_AUTO_HIDE_MS,
    PLAYBACK_SPEEDS,
    VOLUME_WHEEL_STEP,
)
from configs.theme import (
    C_BG_DARKEST,
    C_BG_PANEL,
    C_BORDER,
    C_PRIMARY,
    C_TEXT,
    C_TEXT_SUB,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
)
from core.models import PlayMode, PlayerState
from core.video_engine import VideoEngine
from utils.error_handler import handle_error
from utils.formatters import fmt_time, parse_ms, parse_idx

logger = logging.getLogger(__name__)


@ft.component
def PlayerArea(
    state: PlayerState,
    engine: VideoEngine,
    play_nonce: int,
    on_track_change: Callable,
    on_complete: Callable,
    on_prev: Callable,
    on_next: Callable,
    on_stop: Callable,
    on_toggle_play_mode: Callable,
    on_toggle_play: Callable,
    on_seek: Callable[[int], None],
    on_set_volume: Callable[[float], None],
    on_toggle_mute: Callable,
    on_toggle_fullscreen: Callable,
    on_set_rate: Callable[[float], None],
    on_position_change: Callable[[int], None],
    on_duration_change: Callable[[int], None],
    on_toggle_remaining_time: Callable,
):
    """Player area component."""
    position_ms, set_position_ms = ft.use_state(0)
    duration_ms, set_duration_ms = ft.use_state(0)
    is_playing, set_is_playing = ft.use_state(False)
    auto_play_toggle_init = ft.use_ref(True)
    controls_visible, set_controls_visible = ft.use_state(True)
    _auto_hide_timer = ft.use_ref(None)

    # ─── 状态快照 ref（供事件回调读取最新值，避免闭包过期）───
    is_playing_ref = ft.use_ref(False)
    position_ms_ref = ft.use_ref(0)
    is_playing_ref.current = is_playing
    position_ms_ref.current = position_ms

    # ─── 同步外部播放状态（键盘快捷键等外部触发的播放/暂停）───
    def _sync_playing():
        if state.is_playing != is_playing:
            set_is_playing(state.is_playing)
    ft.use_effect(_sync_playing, dependencies=[state.is_playing])

    page = ft.context.page
    engine.bind_page(page)

    # ─── 全屏控制栏自动隐藏 ───

    def _schedule_auto_hide():
        if not state.is_fullscreen:
            return

        def _hide():
            set_controls_visible(False)

        timer = _auto_hide_timer.current
        if timer:
            timer.cancel()
        _auto_hide_timer.current = threading.Timer(
            CONTROLS_AUTO_HIDE_MS / 1000.0, _hide
        )
        _auto_hide_timer.current.start()

    def _show_controls_and_schedule():
        if state.is_fullscreen:
            set_controls_visible(True)
            _schedule_auto_hide()

    ft.use_effect(lambda: _schedule_auto_hide() if state.is_fullscreen else None, dependencies=[state.is_fullscreen])

    # ─── 播放逻辑 ───

    def _do_play():
        if not state.playlist:
            return

        async def _jump():
            v = engine.video
            if not v or not (0 <= state.current_index < len(state.playlist)):
                return
            # 等待 Video 控件挂载到页面（page 属性在未挂载时抛 RuntimeError）
            for attempt in range(20):
                try:
                    _ = v.page
                    break
                except RuntimeError:
                    await asyncio.sleep(0.1)
            else:
                logger.warning("Video 控件未能在 2 秒内挂载到页面")
                return
            try:
                await v.jump_to(state.current_index)
                await asyncio.sleep(0.05)
                await v.play()
                set_is_playing(True)
            except Exception as e:
                handle_error(e, page=page, context="播放视频")

        asyncio.ensure_future(_jump())

    ft.use_effect(_do_play, dependencies=[play_nonce])

    def _on_auto_play_toggle():
        if auto_play_toggle_init.current:
            auto_play_toggle_init.current = False
            return
        if not state.has_video:
            return
        cur_pos = position_ms_ref.current
        cur_playing = is_playing_ref.current
        engine.pending_restore = (cur_pos, cur_playing)

        async def _restore():
            try:
                await engine.restore_after_mode_change(cur_pos, cur_playing)
            except Exception as e:
                handle_error(e, page=page, context="恢复播放状态")

        asyncio.ensure_future(_restore())

    ft.use_effect(_on_auto_play_toggle, dependencies=[state.play_mode])

    def _on_load(e):
        try:
            _handle_load()
        except Exception as exc:
            handle_error(exc, page=page, context="视频加载")

    def _handle_load():
        pending = engine.pending_restore
        if pending:
            pos, was_playing = pending
            engine.pending_restore = None

            async def _restore():
                try:
                    if pos > 0:
                        await engine.seek(pos)
                    if was_playing:
                        await engine.play()
                    set_is_playing(was_playing)
                except Exception as exc:
                    handle_error(exc, page=page, context="恢复播放位置")

            asyncio.ensure_future(_restore())
            return
        if state.pending_restore_pos > 0:
            restore_pos = state.pending_restore_pos
            state.pending_restore_pos = 0

            async def _restore_pos():
                try:
                    await asyncio.sleep(0.1)
                    await engine.seek(restore_pos)
                except Exception as exc:
                    handle_error(exc, page=page, context="恢复进度")

            asyncio.ensure_future(_restore_pos())
            set_is_playing(False)
            return
        set_is_playing(True)

    def _on_complete(e):
        try:
            on_complete()
        except Exception as exc:
            handle_error(exc, page=page, context="播放完成处理")

    def _on_pos(e):
        try:
            if not engine.is_seeking:
                ms = parse_ms(e.data)
                set_position_ms(ms)
                on_position_change(ms)
        except Exception as exc:
            logger.error("位置更新失败: %s", exc)

    def _on_dur(e):
        try:
            ms = parse_ms(e.data)
            set_duration_ms(ms)
            on_duration_change(ms)
        except Exception as exc:
            logger.error("时长更新失败: %s", exc)

    def _on_enter_fs(e):
        if not state.is_fullscreen:
            on_toggle_fullscreen()

    def _on_exit_fs(e):
        if state.is_fullscreen:
            on_toggle_fullscreen()

    async def _toggle_play(e=None):
        try:
            await engine.play_or_pause()
            new_playing = not is_playing_ref.current
            set_is_playing(new_playing)
            on_toggle_play()
        except Exception as exc:
            handle_error(exc, page=page, context="播放/暂停")

    async def _stop(e=None):
        try:
            await engine.stop()
            set_is_playing(False)
            set_position_ms(0)
            on_stop()
        except Exception as exc:
            handle_error(exc, page=page, context="停止播放")

    # ─── 进度条 ───

    def _on_slider_start(e):
        engine.is_seeking = True
        engine.seek_pos = position_ms_ref.current

    def _on_slider_change(e):
        pos = _slider_value(e)
        if pos is not None:
            engine.seek_pos = pos
            set_position_ms(pos)

    def _on_slider_end(e):
        pos = _slider_value(e)
        if pos is None:
            pos = engine.seek_pos
        set_position_ms(pos)

        async def _do_seek():
            try:
                await engine.seek(pos)
            except Exception as exc:
                handle_error(exc, page=page, context="进度跳转")
            finally:
                engine.is_seeking = False

        asyncio.ensure_future(_do_seek())
        on_seek(pos)

    def _slider_value(e) -> int | None:
        """从 Slider 事件中提取位置值（毫秒）。"""
        # 方式 1：解析 e.data
        try:
            if e.data is not None:
                return int(float(e.data))
        except (TypeError, ValueError):
            pass
        # 方式 2：从事件控件的 value 属性读取
        try:
            ctrl = getattr(e, "control", None)
            if ctrl is not None and getattr(ctrl, "value", None) is not None:
                return int(float(ctrl.value))
        except (TypeError, ValueError, AttributeError):
            pass
        return None

    # ─── 音量 ───

    async def _vol_change(e):
        try:
            val = float(e.data)
        except (TypeError, ValueError):
            return
        on_set_volume(val)

    def _on_vol_wheel(e: ft.ScrollEvent):
        if e.scroll_delta is None:
            return
        delta = e.scroll_delta.y if hasattr(e.scroll_delta, 'y') else 0
        if delta < 0:
            new_vol = min(100.0, state.volume + VOLUME_WHEEL_STEP)
        elif delta > 0:
            new_vol = max(0.0, state.volume - VOLUME_WHEEL_STEP)
        else:
            return
        on_set_volume(new_vol)

    # ─── 倍速 ───

    def _rate_label(r: float) -> str:
        return f"{r:g}x"

    # ─── UI 构建 ───

    has_video = state.has_video
    title = state.current_item.title if has_video else ""
    video_playlist = VideoEngine.build_playlist(
        state.playlist, state.play_mode, state.current_index
    )
    playlist_mode = VideoEngine.get_playlist_mode(state.play_mode)
    slider_max = max(duration_ms, 1)
    play_mode_icons = {
        PlayMode.SEQUENCE: ft.Icons.PLAY_ARROW,
        PlayMode.REPEAT_ALL: ft.Icons.REPEAT,
        PlayMode.REPEAT_ONE: ft.Icons.REPEAT_ONE,
        PlayMode.SHUFFLE: ft.Icons.SHUFFLE,
    }
    play_mode_labels = {
        PlayMode.SEQUENCE: "顺序播放",
        PlayMode.REPEAT_ALL: "列表循环",
        PlayMode.REPEAT_ONE: "单曲循环",
        PlayMode.SHUFFLE: "随机播放",
    }
    current_mode_icon = play_mode_icons.get(state.play_mode, ft.Icons.PLAY_ARROW)
    current_mode_label = play_mode_labels.get(state.play_mode, "顺序播放")

    def _icon_btn(icon, on_click, tooltip="", enabled=True, color=None):
        return ft.IconButton(
            icon=icon,
            icon_color=color or C_TEXT,
            on_click=on_click,
            tooltip=tooltip,
            disabled=not enabled,
            icon_size=20,
        )

    # ─── 时间显示 ───

    if state.show_remaining_time and duration_ms > 0:
        time_text = f"-{fmt_time(max(0, duration_ms - position_ms))}"
    else:
        time_text = fmt_time(position_ms)

    def _on_time_click(e):
        on_toggle_remaining_time()

    # ─── 进度条 label（拖拽时显示时间）───

    slider_label = fmt_time(position_ms) if engine.is_seeking else ""

    video_control = Video(
        ref=engine.ref,
        playlist=video_playlist,
        playlist_mode=playlist_mode,
        controls={
            VideoControlsMode.NORMAL: None,
            VideoControlsMode.FULLSCREEN: VideoEngine.build_fullscreen_controls(),
        },
        fullscreen=state.is_fullscreen,
        volume=state.volume,
        playback_rate=state.playback_rate,
        muted=state.muted,
        fill_color=C_BG_DARKEST,
        on_load=_on_load,
        on_track_change=lambda e: on_track_change(parse_idx(e.data)),
        on_complete=_on_complete,
        on_position_change=_on_pos,
        on_duration_change=_on_dur,
        on_enter_fullscreen=_on_enter_fs,
        on_exit_fullscreen=_on_exit_fs,
        expand=True,
    )

    # ─── 控制栏内容 ───

    def _build_controls_bar():
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text(
                            title,
                            color=C_TEXT,
                            size=FONT_SIZE_SMALL,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            weight=ft.FontWeight.W_500,
                        ),
                        padding=ft.Padding.only(left=12, right=12, top=8),
                        visible=has_video,
                    ),
                    ft.Row(
                        controls=[
                            ft.GestureDetector(
                                content=ft.Text(
                                    time_text,
                                    color=C_TEXT_SUB,
                                    size=FONT_SIZE_TINY,
                                ),
                                on_tap=_on_time_click,
                            ),
                            ft.Slider(
                                min=0,
                                max=slider_max,
                                value=position_ms,
                                active_color=C_PRIMARY,
                                inactive_color=C_BORDER,
                                thumb_color=C_PRIMARY,
                                expand=True,
                                label=slider_label,
                                on_change_start=_on_slider_start,
                                on_change=_on_slider_change,
                                on_change_end=_on_slider_end,
                            ),
                            ft.Text(
                                fmt_time(duration_ms),
                                color=C_TEXT_SUB,
                                size=FONT_SIZE_TINY,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        controls=[
                            _icon_btn(
                                ft.Icons.SKIP_PREVIOUS,
                                lambda e: on_prev(),
                                "上一曲",
                                enabled=state.has_prev,
                            ),
                            _icon_btn(
                                ft.Icons.PAUSE
                                if is_playing
                                else ft.Icons.PLAY_ARROW,
                                _toggle_play,
                                "播放/暂停",
                                enabled=has_video,
                                color=C_PRIMARY,
                            ),
                            _icon_btn(
                                ft.Icons.STOP_CIRCLE_OUTLINED,
                                _stop,
                                "停止",
                                enabled=has_video,
                                color=C_TEXT_SUB,
                            ),
                            _icon_btn(
                                ft.Icons.SKIP_NEXT,
                                lambda e: on_next(),
                                "下一曲",
                                enabled=state.has_next,
                            ),
                            _icon_btn(
                                current_mode_icon,
                                lambda e: on_toggle_play_mode(),
                                current_mode_label,
                                enabled=has_video,
                                color=C_PRIMARY,
                            ),
                            ft.Container(width=12),
                            ft.PopupMenuButton(
                                content=ft.Text(
                                    _rate_label(state.playback_rate),
                                    color=C_PRIMARY,
                                    size=FONT_SIZE_SMALL,
                                    weight=ft.FontWeight.W_600,
                                ),
                                items=[
                                    ft.PopupMenuItem(
                                        content=ft.Text(
                                            _rate_label(s),
                                            color=C_PRIMARY
                                            if s == state.playback_rate
                                            else C_TEXT,
                                            size=FONT_SIZE_SMALL,
                                        ),
                                        icon=ft.Icons.CHECK
                                        if s == state.playback_rate
                                        else None,
                                        on_click=lambda e, s=s: on_set_rate(s),
                                    )
                                    for s in PLAYBACK_SPEEDS
                                ],
                                bgcolor=C_BG_PANEL,
                                menu_position=ft.PopupMenuPosition.UNDER,
                            ),
                            ft.Container(expand=True),
                            ft.GestureDetector(
                                content=_icon_btn(
                                    ft.Icons.VOLUME_OFF
                                    if state.muted or state.volume == 0
                                    else ft.Icons.VOLUME_UP,
                                    lambda e: on_toggle_mute(),
                                    "静音",
                                    color=C_TEXT_SUB,
                                ),
                                on_scroll=_on_vol_wheel,
                            ),
                            ft.Slider(
                                min=0,
                                max=100,
                                value=0 if state.muted else state.volume,
                                active_color=C_PRIMARY,
                                inactive_color=C_BORDER,
                                thumb_color=C_PRIMARY,
                                width=90,
                                on_change=_vol_change,
                            ),
                            ft.Container(width=8),
                            _icon_btn(
                                ft.Icons.FULLSCREEN
                                if not state.is_fullscreen
                                else ft.Icons.FULLSCREEN_EXIT,
                                lambda e: on_toggle_fullscreen(),
                                "全屏",
                                color=C_TEXT_SUB,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=4,
            ),
            bgcolor=C_BG_PANEL,
            border=ft.Border.only(top=ft.BorderSide(1, C_BORDER)),
            padding=ft.Padding.only(left=8, right=12, top=4, bottom=8),
        )

    # ─── 全屏底部控制栏悬停区域 ───

    def _on_video_area_hover(e: ft.HoverEvent):
        if not state.is_fullscreen:
            return
        if e.local_position is None:
            return
        # 鼠标接近底部时显示控制栏
        # 由于无法获取确切高度，使用 0.85 作为阈值
        _show_controls_and_schedule()

    # ─── 控制栏（全屏/非全屏共用同一实例）───
    controls_bar = _build_controls_bar()

    return ft.Column(
        controls=[
            ft.Stack(
                controls=[
                    ft.GestureDetector(
                        content=ft.Container(
                            content=video_control,
                            expand=True,
                            bgcolor=C_BG_DARKEST,
                        ),
                        on_double_tap=lambda e: (
                            on_toggle_fullscreen() if not state.is_fullscreen else None
                        ),
                        on_hover=_on_video_area_hover,
                        on_scroll=_on_vol_wheel,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(
                                    ft.Icons.VIDEO_LIBRARY_OUTLINED,
                                    size=56,
                                    color=C_TEXT_SUB,
                                ),
                                ft.Text(
                                    "打开视频文件",
                                    color=C_TEXT_SUB,
                                    size=FONT_SIZE_SMALL,
                                ),
                                ft.Text(
                                    "MP4 / MKV / AVI / FLV / MOV ...",
                                    color=C_TEXT_SUB,
                                    size=FONT_SIZE_TINY,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        expand=True,
                        alignment=ft.Alignment.CENTER,
                        visible=not has_video,
                    ),
                ],
                expand=True,
            ),
            controls_bar,
        ],
        expand=True,
        spacing=0,
    )
