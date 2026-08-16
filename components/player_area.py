# -*- coding: utf-8 -*-
"""
PlayerArea component - Video display with custom control bar.

Declarative component: receives player state and callbacks,
high-frequency state is isolated within the component.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

import flet as ft
from flet_video import Video, VideoControlsMode

from configs.app_config import PLAYBACK_SPEEDS
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
    on_toggle_play_mode: Callable,
    on_toggle_play: Callable,
    on_seek: Callable[[int], None],
    on_set_volume: Callable[[float], None],
    on_toggle_mute: Callable,
    on_toggle_fullscreen: Callable,
    on_set_rate: Callable[[float], None],
    on_position_change: Callable[[int], None],
    on_duration_change: Callable[[int], None],
):
    """Player area component."""
    position_ms, set_position_ms = ft.use_state(0)
    duration_ms, set_duration_ms = ft.use_state(0)
    is_playing, set_is_playing = ft.use_state(False)
    auto_play_toggle_init = ft.use_ref(True)
    video_ref = ft.use_ref()

    page = ft.context.page
    engine.bind_page(page)

    def _do_play():
        if not state.playlist or not video_ref.current:
            return

        async def _jump():
            v = video_ref.current
            if v and 0 <= state.current_index < len(state.playlist):
                try:
                    await v.jump_to(state.current_index)
                    await asyncio.sleep(0.05)
                    await v.play()
                    set_is_playing(True)
                except Exception as e:
                    logger.error("play failed: %s", e)

        asyncio.ensure_future(_jump())

    ft.use_effect(_do_play, dependencies=[play_nonce])

    def _on_auto_play_toggle():
        if auto_play_toggle_init.current:
            auto_play_toggle_init.current = False
            return
        if not state.has_video:
            return
        engine.pending_restore = (position_ms, is_playing)

        async def _restore():
            await engine.restore_after_mode_change(position_ms, is_playing)

        asyncio.ensure_future(_restore())

    ft.use_effect(_on_auto_play_toggle, dependencies=[state.play_mode])

    def _on_load(e):
        pending = engine.pending_restore
        if pending:
            pos, was_playing = pending
            engine.pending_restore = None

            async def _restore():
                if pos > 0:
                    await engine.seek(pos)
                if was_playing:
                    await engine.play()
                set_is_playing(was_playing)

            asyncio.ensure_future(_restore())
            return
        set_is_playing(True)

    def _on_complete(e):
        on_complete()

    def _on_pos(e):
        if not engine.is_seeking:
            ms = parse_ms(e.data)
            set_position_ms(ms)
            on_position_change(ms)

    def _on_dur(e):
        ms = parse_ms(e.data)
        set_duration_ms(ms)
        on_duration_change(ms)

    def _on_enter_fs(e):
        on_toggle_fullscreen()

    def _on_exit_fs(e):
        on_toggle_fullscreen()

    async def _toggle_play():
        await engine.play_or_pause()
        set_is_playing(not is_playing)
        on_toggle_play()

    def _on_slider_start(e):
        engine.is_seeking = True
        engine.seek_pos = position_ms

    def _on_slider_change(e):
        try:
            pos = int(float(e.data))
            engine.seek_pos = pos
            set_position_ms(pos)
        except (TypeError, ValueError):
            pass

    def _on_slider_end(e):
        try:
            pos = int(float(e.data))
        except (TypeError, ValueError):
            pos = engine.seek_pos
        engine.is_seeking = False
        set_position_ms(pos)

        async def _do_seek():
            await engine.seek(pos)

        asyncio.ensure_future(_do_seek())
        on_seek(pos)

    async def _vol_change(e):
        try:
            val = float(e.data)
        except (TypeError, ValueError):
            return
        on_set_volume(val)

    def _rate_label(r: float) -> str:
        return f"{r:g}x"

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
        PlayMode.SEQUENCE: "Sequence",
        PlayMode.REPEAT_ALL: "Loop All",
        PlayMode.REPEAT_ONE: "Loop One",
        PlayMode.SHUFFLE: "Shuffle",
    }
    current_mode_icon = play_mode_icons.get(state.play_mode, ft.Icons.PLAY_ARROW)
    current_mode_label = play_mode_labels.get(state.play_mode, "Sequence")

    def _icon_btn(icon, on_click, tooltip="", enabled=True, color=None):
        return ft.IconButton(
            icon=icon,
            icon_color=color or C_TEXT,
            on_click=on_click,
            tooltip=tooltip,
            disabled=not enabled,
            icon_size=20,
        )

    video_control = Video(
        ref=video_ref,
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
                        on_double_tap=lambda e: on_toggle_fullscreen(),
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
                                    "Open a video file",
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
            ft.Container(
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
                                ft.Text(
                                    fmt_time(position_ms),
                                    color=C_TEXT_SUB,
                                    size=FONT_SIZE_TINY,
                                ),
                                ft.Slider(
                                    min=0,
                                    max=slider_max,
                                    value=position_ms,
                                    active_color=C_PRIMARY,
                                    inactive_color=C_BORDER,
                                    thumb_color=C_PRIMARY,
                                    expand=True,
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
                                    "Previous",
                                    enabled=state.has_prev,
                                ),
                                _icon_btn(
                                    ft.Icons.PAUSE
                                    if is_playing
                                    else ft.Icons.PLAY_ARROW,
                                    _toggle_play,
                                    "Play/Pause",
                                    enabled=has_video,
                                    color=C_PRIMARY,
                                ),
                                _icon_btn(
                                    ft.Icons.SKIP_NEXT,
                                    lambda e: on_next(),
                                    "Next",
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
                                _icon_btn(
                                    ft.Icons.VOLUME_OFF
                                    if state.muted or state.volume == 0
                                    else ft.Icons.VOLUME_UP,
                                    lambda e: on_toggle_mute(),
                                    "Mute",
                                    color=C_TEXT_SUB,
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
                                    "Fullscreen",
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
            ),
        ],
        expand=True,
        spacing=0,
    )
