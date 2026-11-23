"""播放区 —— 画面 + 事件编排 + 控制栏容器。

组件只负责「播放器的一生」：起播、位置/时长同步、拖动 seek、播放模式切换后的
恢复、全屏切换、全屏时控制栏自动隐藏。按钮怎么排、颜色怎么取，交给
:mod:`components.control_bar` 与 :mod:`components.kit`。

三条不变式（都是实测踩过的坑）：

1. **全屏 / 窗口共用同一棵树**。切换全屏时只改属性、不重建 ``NativeVideo``，
   底层 media_kit 只切原生窗口，播放位置与状态自然保持；不需要人为 seek/restore。
2. **拖动期间屏蔽位置回写**。``engine.is_seeking`` 为真时忽略底层发来的
   ``on_position_change``，否则松手前画面会一直往回跳。
3. **状态快照用 ref 兜底**。事件回调可能拿到过期的闭包值，播放与否、当前位置
   一律从 ``*_ref`` 读最新快照。

高频状态（位置 / 时长 / 播放中 / 控制栏可见）留在组件内部，避免每 500ms 的
位置更新触发整页重渲染。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

import ui
from cs_video_player.components.media import NativeVideo, VideoControlsMode, desktop_controls

from cs_video_player.components.control_bar import ControlsActions, ControlsView, build_control_bar
from cs_video_player.components.kit import empty_stage
from cs_video_player.configs.app_config import CONTROLS_AUTO_HIDE_MS, VOLUME_WHEEL_STEP
from cs_video_player.configs.theme import C_BG_DARKEST, PALETTE
from cs_video_player.core.models import PlayerState
from cs_video_player.core.video_engine import VideoEngine
from cs_video_player.utils.error_handler import handle_error
from cs_video_player.utils.formatters import (
    fmt_time,
    parse_idx,
    parse_ms,
    slider_position,
    volume_after_wheel,
)

logger = logging.getLogger(__name__)


@ui.component
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
    on_toggle_sidebar: Callable | None = None,
    sidebar_visible: bool = True,
    on_open_file: Callable | None = None,
):
    """播放区组件（根组件传入状态快照与意图回调）。"""
    position_ms, set_position_ms = ui.use_state(0)
    duration_ms, set_duration_ms = ui.use_state(0)
    is_playing, set_is_playing = ui.use_state(False)
    controls_visible, set_controls_visible = ui.use_state(True)

    auto_play_toggle_init = ui.use_ref(True)
    auto_hide_timer = ui.use_ref(None)
    is_switching = ui.use_ref(False)      # 全屏切换进行中，屏蔽过时位置事件
    fs_prev = ui.use_ref(False)

    # ─── 事件回调读最新值的快照 ref ───
    is_playing_ref = ui.use_ref(False)
    position_ms_ref = ui.use_ref(0)
    is_playing_ref.current = is_playing
    position_ms_ref.current = position_ms

    page = ui.context.page
    engine.bind_page(page)

    # ─── 外部触发的播放 / 暂停（键盘快捷键等）同步回本地 ───
    def _sync_playing():
        if state.is_playing != is_playing:
            set_is_playing(state.is_playing)

    ui.use_effect(_sync_playing, dependencies=[state.is_playing])

    # ─── 全屏控制栏自动隐藏 ───
    def _schedule_auto_hide():
        if not state.is_fullscreen:
            return
        prev = auto_hide_timer.current
        if prev is not None and not prev.done():
            prev.cancel()

        async def _delayed_hide():
            try:
                await asyncio.sleep(CONTROLS_AUTO_HIDE_MS / 1000.0)
                set_controls_visible(False)
            except asyncio.CancelledError:
                pass

        auto_hide_timer.current = asyncio.ensure_future(_delayed_hide())

    def _show_controls_and_schedule():
        if state.is_fullscreen:
            set_controls_visible(True)
            _schedule_auto_hide()

    ui.use_effect(
        lambda: _schedule_auto_hide() if state.is_fullscreen else None,
        dependencies=[state.is_fullscreen],
    )

    # ─── 起播：等播放器挂到页面再 jump_to + play ───
    def _do_play():
        if not state.playlist:
            return

        async def _jump():
            v = engine.video
            if not v or not (0 <= state.current_index < len(state.playlist)):
                return
            # 控件挂载是异步的：首帧 / 会话恢复时 jump_to 可能先于挂载到达。
            # 只重试「尚未挂到页面」这一类可恢复错误，其余错误立刻上报。
            for attempt in range(20):
                try:
                    await v.jump_to(state.current_index)
                    await asyncio.sleep(0.05)
                    await v.play()
                    set_is_playing(True)
                    return
                except RuntimeError as exc:
                    if "added to the page" in str(exc).lower() and attempt < 19:
                        await asyncio.sleep(0.1)
                        continue
                    handle_error(exc, page=page, context="播放视频")
                    return
                except Exception as exc:
                    handle_error(exc, page=page, context="播放视频")
                    return
            logger.warning("播放器未能在 2 秒内挂载到页面")

        asyncio.ensure_future(_jump())

    ui.use_effect(_do_play, dependencies=[play_nonce])

    # ─── 播放模式切换后恢复进度 ───
    def _on_mode_change():
        if auto_play_toggle_init.current:
            auto_play_toggle_init.current = False
            return
        if not state.has_video:
            return
        pos = position_ms_ref.current
        was_playing = is_playing_ref.current
        engine.pending_restore = (pos, was_playing)

        async def _restore():
            try:
                await engine.restore_after_mode_change(pos, was_playing)
            except Exception as exc:
                handle_error(exc, page=page, context="恢复播放状态")

        asyncio.ensure_future(_restore())

    ui.use_effect(_on_mode_change, dependencies=[state.play_mode])

    # ─── 全屏切换：只标记，不重建控件 ───
    def _on_fullscreen_toggle():
        prev = fs_prev.current
        fs_prev.current = state.is_fullscreen
        if prev == state.is_fullscreen or not state.has_video:
            return
        is_switching.current = True

        async def _clear():
            await asyncio.sleep(0.15)
            is_switching.current = False

        asyncio.ensure_future(_clear())

    ui.use_effect(_on_fullscreen_toggle, dependencies=[state.is_fullscreen])

    # ─── 播放器事件 ───
    def _on_load(e):
        try:
            _handle_load()
        except Exception as exc:
            handle_error(exc, page=page, context="视频加载")

    def _handle_load():
        if is_switching.current:
            return
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
            if is_switching.current or engine.is_seeking:
                return
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
            set_is_playing(not is_playing_ref.current)
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

    # ─── 进度条拖动 ───
    def _on_seek_start(e):
        engine.is_seeking = True
        engine.seek_pos = position_ms_ref.current

    def _on_seek_change(e):
        pos = slider_position(e)
        if pos is not None:
            engine.seek_pos = pos
            set_position_ms(pos)

    def _on_seek_end(e):
        pos = slider_position(e)
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

    # ─── 音量 ───
    async def _vol_change(e):
        # 事件先送新值，control.value 的回写可能晚一帧，以 e.data 为准。
        try:
            value = float(e.data)
        except (TypeError, ValueError):
            return
        on_set_volume(value)

    def _on_vol_wheel(e: ui.ScrollEvent):
        delta = getattr(e.scroll_delta, "y", 0) if e.scroll_delta is not None else 0
        new_vol = volume_after_wheel(state.volume, delta, VOLUME_WHEEL_STEP)
        if new_vol != state.volume:
            on_set_volume(new_vol)

    # ─── 画面区悬停：全屏时唤醒控制栏 ───
    def _on_video_area_hover(e: ui.HoverEvent):
        if state.is_fullscreen and e.local_position is not None:
            _show_controls_and_schedule()

    # ─── 原生播放器 ───
    video_playlist = VideoEngine.build_playlist(
        state.playlist, state.play_mode, state.current_index
    )
    playlist_mode = VideoEngine.get_playlist_mode(state.play_mode)
    slider_label = fmt_time(position_ms) if engine.is_seeking else ""

    video_control = NativeVideo(
        ref=engine.ref,
        playlist=video_playlist,
        playlist_mode=playlist_mode,
        controls={
            VideoControlsMode.NORMAL: None,
            VideoControlsMode.FULLSCREEN: desktop_controls(PALETTE),
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

    # ─── 控制栏：一份实例，窗口模式贴底、全屏模式浮在画面底部 ───
    controls_bar = build_control_bar(
        ControlsView(
            state=state,
            is_playing=is_playing,
            position_ms=position_ms,
            duration_ms=duration_ms,
            sidebar_visible=sidebar_visible,
            slider_label=slider_label,
        ),
        ControlsActions(
            on_prev=lambda e=None: on_prev(),
            on_next=lambda e=None: on_next(),
            on_toggle_play=_toggle_play,
            on_stop=_stop,
            on_toggle_play_mode=lambda e=None: on_toggle_play_mode(),
            on_set_rate=on_set_rate,
            on_toggle_mute=lambda e=None: on_toggle_mute(),
            on_set_volume=_vol_change,
            on_toggle_fullscreen=lambda e=None: on_toggle_fullscreen(),
            on_toggle_sidebar=lambda e=None: (
                on_toggle_sidebar() if on_toggle_sidebar else None
            ),
            on_toggle_remaining_time=lambda e=None: on_toggle_remaining_time(),
            on_seek_start=_on_seek_start,
            on_seek_change=_on_seek_change,
            on_seek_end=_on_seek_end,
            on_volume_wheel=_on_vol_wheel,
        ),
    )

    return ui.Column(
        controls=[
            ui.Stack(
                controls=[
                    ui.GestureDetector(
                        content=ui.Container(
                            content=video_control,
                            expand=True,
                            bgcolor=C_BG_DARKEST,
                        ),
                        on_double_tap=lambda e: on_toggle_fullscreen(),
                        on_hover=_on_video_area_hover,
                        on_scroll=_on_vol_wheel,
                        expand=True,
                    ),
                    ui.Container(
                        content=empty_stage(on_open=on_open_file),
                        expand=True,
                        alignment=ui.Alignment.CENTER,
                        visible=not state.has_video,
                    ),
                    ui.Container(
                        content=controls_bar
                        if state.is_fullscreen
                        else ui.Container(),
                        alignment=ui.Alignment.BOTTOM_CENTER,
                        visible=state.is_fullscreen and controls_visible,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            controls_bar if not state.is_fullscreen else ui.Container(height=0),
        ],
        expand=True,
        spacing=0,
    )
