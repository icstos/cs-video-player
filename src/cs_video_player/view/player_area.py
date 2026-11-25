"""view / player_area —— 播放区的纯声明式渲染与事件分发。

这里没有 ``use_state``、没有 ``use_effect`` 业务分支、没有定时器：位置、时长、
播放中、控制栏显隐、拖动状态全部来自 :class:`AppState`。用户操作只做两件事——
把平台事件数据解析成基本类型，然后调用 :class:`AppViewModel` 的意图方法。

三条不变式（沿用实测经验）：

1. 全屏 / 窗口共用同一棵树，只改属性、不重建播放器，播放位置自然保持；
2. 拖动期间由 ViewModel 屏蔽位置回写，画面不往回跳；
3. 播放器句柄跨帧稳定，Service 通过端口协议操作它，View 不反向读业务状态。
"""

from __future__ import annotations

from typing import Any

import ui

from cs_video_player.models.state import AppState
from cs_video_player.view.control_bar import ControlsActions, ControlsView, build_control_bar
from cs_video_player.view.formatters import fmt_time, parse_idx, parse_ms, slider_position
from cs_video_player.view.kit import empty_stage
from cs_video_player.view.native_video import VideoCallbacks, VideoHandle
from cs_video_player.view.theme import C_BG_DARKEST
from cs_video_player.viewmodel import AppViewModel


@ui.component
def PlayerArea(state: AppState, vm: AppViewModel) -> ui.Control:
    """按状态快照渲染画面 + 控制栏；所有交互回灌 ViewModel。"""
    handle: VideoHandle = ui.use_ref(VideoHandle).current

    def _attach() -> None:
        vm.attach_media_control(handle)

    ui.use_effect(_attach, dependencies=[])

    def _on_load(e: Any) -> None:
        vm.on_video_loaded()

    def _on_track_change(e: Any) -> None:
        vm.on_track_change(parse_idx(e.data))

    def _on_complete(e: Any) -> None:
        vm.on_complete()

    def _on_position(e: Any) -> None:
        vm.on_position(parse_ms(e.data))

    def _on_duration(e: Any) -> None:
        vm.on_duration(parse_ms(e.data))

    def _on_enter_fs(e: Any) -> None:
        if not state.is_fullscreen:
            vm.on_fullscreen_event(True)

    def _on_exit_fs(e: Any) -> None:
        if state.is_fullscreen:
            vm.on_fullscreen_event(False)

    # 每帧都构造新的 Video 描述：Flet 按控件 ID 就地差分，播放器不会重载。
    # 不能把控件对象放进 use_memo —— 重渲染会丢弃缓存实例，ref 就会指向未被
    # 挂载的控件，所有播放器命令都会报「Control must be added to the page」。
    video = handle.build(
        tracks=state.native_playlist,
        mode=state.native_mode,
        callbacks=VideoCallbacks(
            on_load=_on_load,
            on_track_change=_on_track_change,
            on_complete=_on_complete,
            on_position=_on_position,
            on_duration=_on_duration,
            on_enter_fullscreen=_on_enter_fs,
            on_exit_fullscreen=_on_exit_fs,
        ),
        fullscreen=state.is_fullscreen,
        volume=state.volume,
        playback_rate=state.playback_rate,
        muted=state.muted,
        fill_color=C_BG_DARKEST,
    )

    def _on_seek_start(e: Any) -> None:
        vm.begin_seek()

    def _on_seek_change(e: Any) -> None:
        position = slider_position(e)
        if position is not None:
            vm.preview_seek(position)

    def _on_seek_end(e: Any) -> None:
        position = slider_position(e)
        vm.end_seek(position if position is not None else state.seek_preview_ms)

    async def _on_volume(e: Any) -> None:
        try:
            vm.set_volume(float(e.data))
        except (TypeError, ValueError):
            return

    def _on_wheel(e: ui.ScrollEvent) -> None:
        delta = getattr(e.scroll_delta, "y", 0) if e.scroll_delta is not None else 0
        vm.wheel_volume(delta)

    def _on_hover(e: ui.HoverEvent) -> None:
        if state.is_fullscreen and e.local_position is not None:
            vm.on_video_hover()

    controls = build_control_bar(
        ControlsView(
            state=state,
            is_playing=state.is_playing,
            position_ms=(
                state.seek_preview_ms if state.is_seeking else state.position_ms
            ),
            duration_ms=state.duration_ms,
            sidebar_visible=state.sidebar_visible,
            slider_label=fmt_time(state.seek_preview_ms) if state.is_seeking else "",
        ),
        ControlsActions(
            on_prev=lambda: vm.play_prev(),
            on_next=lambda: vm.play_next(),
            on_toggle_play=lambda e=None: vm.toggle_play(),
            on_stop=lambda e=None: vm.stop(),
            on_toggle_play_mode=lambda: vm.toggle_play_mode(),
            on_set_rate=vm.set_rate,
            on_toggle_mute=lambda: vm.toggle_mute(),
            on_set_volume=_on_volume,
            on_toggle_fullscreen=lambda: vm.toggle_fullscreen(),
            on_toggle_sidebar=lambda: vm.toggle_sidebar(),
            on_toggle_remaining_time=lambda: vm.toggle_remaining_time(),
            on_seek_start=_on_seek_start,
            on_seek_change=_on_seek_change,
            on_seek_end=_on_seek_end,
            on_volume_wheel=_on_wheel,
        ),
    )

    return ui.Column(
        controls=[
            ui.Stack(
                controls=[
                    ui.GestureDetector(
                        content=ui.Container(
                            content=video, expand=True, bgcolor=C_BG_DARKEST
                        ),
                        on_double_tap=lambda e: vm.toggle_fullscreen(),
                        on_hover=_on_hover,
                        on_scroll=_on_wheel,
                        expand=True,
                    ),
                    ui.Container(
                        content=empty_stage(on_open=vm.request_open_files),
                        expand=True,
                        alignment=ui.Alignment.CENTER,
                        visible=not state.has_video,
                    ),
                    ui.Container(
                        content=controls if state.is_fullscreen else ui.Container(),
                        alignment=ui.Alignment.BOTTOM_CENTER,
                        visible=state.is_fullscreen and state.controls_visible,
                        expand=True,
                    ),
                ],
                expand=True,
            ),
            controls if not state.is_fullscreen else ui.Container(height=0),
        ],
        expand=True,
        spacing=0,
    )
