"""播放控制栏 —— 紧凑单行，全屏 / 窗口两种形态完全共用。

从 ``player_area`` 里独立出来的理由：视频区关心的是「播放器事件与恢复时机」，
控制栏关心的是「一排按钮怎么摆」。两者混在一个组件里，任何一次文案或间距调整
都要在 400 行状态逻辑里翻找；拆开之后，控制栏是一棵纯控件树，可以单独构造、
单独截图、单独核对按钮清单。

契约：

* :class:`ControlsView` 是**只读快照**，@dataclass(frozen=True) 保证渲染期间
  不会被回调偷偷改写；
* :class:`ControlsActions` 是**回调集合**，值从参数进、意图从回调出；
* :func:`build_control_bar` 是无状态纯函数，不读全局状态、不注册副作用。

时间轴、音量、倍速、图标按钮分别用 :mod:`components.media` 的 ``TimeSlider`` /
``VolumeControl`` / ``SpeedMenu`` / ``IconAction``，配色与本应用的 ``PALETTE``
同源（视频能力已从 cs-ui 收回本项目，见 :mod:`components.media`）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import ui

from configs.app_config import PLAYBACK_SPEEDS
from configs.theme import (
    C_BG_PANEL,
    C_DIVIDER,
    C_PRIMARY,
    C_TEXT_SUB,
    FONT_SIZE_TINY,
    ICON_SIZE_LG,
    ICON_SIZE_MD,
    PALETTE,
    SPACING_SM,
)
from core.models import PlayMode, PlayerState
from components.kit import icon_action, muted
from components.media import BAR_PADDING, SpeedMenu, TimeSlider, VolumeControl

#: 播放模式 → (图标, tooltip)。数据与视图分离，快捷键提示也可复用这张表。
PLAY_MODE_STYLE: dict[PlayMode, tuple[object, str]] = {
    PlayMode.SEQUENCE: (ui.Icons.PLAY_ARROW, "顺序播放"),
    PlayMode.REPEAT_ALL: (ui.Icons.REPEAT, "列表循环"),
    PlayMode.REPEAT_ONE: (ui.Icons.REPEAT_ONE, "单曲循环"),
    PlayMode.SHUFFLE: (ui.Icons.SHUFFLE, "随机播放"),
}


@dataclass(frozen=True, slots=True)
class ControlsView:
    """控制栏渲染所需的全部值（一次渲染一份快照）。"""

    state: PlayerState
    is_playing: bool
    position_ms: int
    duration_ms: int
    sidebar_visible: bool
    slider_label: str = ""


@dataclass(frozen=True, slots=True)
class ControlsActions:
    """控制栏能发出的全部意图。缺省回调为 None 时对应控件自动隐藏或禁用。"""

    on_prev: Callable[[], None]
    on_next: Callable[[], None]
    on_toggle_play: Callable
    on_stop: Callable
    on_toggle_play_mode: Callable[[], None]
    on_set_rate: Callable[[float], None]
    on_toggle_mute: Callable[[], None]
    on_set_volume: Callable
    on_toggle_fullscreen: Callable[[], None]
    on_toggle_sidebar: Callable[[], None]
    on_toggle_remaining_time: Callable[[], None]
    on_seek_start: Callable
    on_seek_change: Callable
    on_seek_end: Callable
    on_volume_wheel: Callable


def build_control_bar(
    view: ControlsView, actions: ControlsActions
) -> ui.Control:
    """构造控制栏：上排时间轴、下排按钮，两排之间不留空隙。"""
    state = view.state
    has_video = state.has_video
    title = state.current_item.title if has_video else ""
    mode_icon, mode_label = PLAY_MODE_STYLE.get(
        state.play_mode, PLAY_MODE_STYLE[PlayMode.SEQUENCE]
    )

    def _btn(icon, on_click, tooltip="", *, enabled=True, color=None, size=ICON_SIZE_MD):
        return icon_action(
            icon, on_click, tooltip=tooltip, disabled=not enabled,
            color=color, size=size,
        )

    # ─── 上排：时间轴 ───
    timeline = TimeSlider(
        view.position_ms,
        view.duration_ms,
        show_remaining=state.show_remaining_time,
        label=view.slider_label,
        on_change_start=actions.on_seek_start,
        on_change=actions.on_seek_change,
        on_change_end=actions.on_seek_end,
        on_toggle_time=actions.on_toggle_remaining_time,
        palette=PALETTE,
    )

    # ─── 下排：按钮 ───
    buttons: list[ui.Control] = []

    # 侧边栏开关只在窗口模式出现；全屏时画面应当完整。
    if not state.is_fullscreen:
        buttons.append(
            _btn(
                ui.Icons.MENU_OPEN_ROUNDED
                if view.sidebar_visible
                else ui.Icons.MENU_ROUNDED,
                lambda e: actions.on_toggle_sidebar(),
                "侧边栏",
                color=C_TEXT_SUB,
            )
        )

    buttons.extend(
        [
            _btn(ui.Icons.SKIP_PREVIOUS_ROUNDED, lambda e: actions.on_prev(),
                 "上一曲", enabled=state.has_prev),
            _btn(
                ui.Icons.PAUSE_ROUNDED if view.is_playing else ui.Icons.PLAY_ARROW_ROUNDED,
                actions.on_toggle_play,
                "播放 / 暂停",
                enabled=has_video,
                color=C_PRIMARY,
                size=ICON_SIZE_LG,
            ),
            _btn(ui.Icons.SKIP_NEXT_ROUNDED, lambda e: actions.on_next(),
                 "下一曲", enabled=state.has_next),
            _btn(ui.Icons.STOP_CIRCLE_OUTLINED, actions.on_stop,
                 "停止", enabled=has_video, color=C_TEXT_SUB),
            _btn(mode_icon, lambda e: actions.on_toggle_play_mode(),
                 mode_label, enabled=has_video, color=C_PRIMARY),
            ui.Container(width=SPACING_SM),
            SpeedMenu(
                state.playback_rate,
                PLAYBACK_SPEEDS,
                actions.on_set_rate,
                palette=PALETTE,
            ),
            ui.Container(expand=True),
        ]
    )

    # 全屏时把片名放在中间：此时没有侧栏，画面里需要一行「我在看什么」。
    buttons.append(
        ui.Container(
            content=muted(title, size=FONT_SIZE_TINY),
            expand=state.is_fullscreen,
            visible=state.is_fullscreen and has_video,
            alignment=ui.Alignment.CENTER,
        )
    )

    buttons.append(
        VolumeControl(
            state.volume,
            state.muted,
            on_change=actions.on_set_volume,
            on_toggle_mute=actions.on_toggle_mute,
            on_scroll=actions.on_volume_wheel,
            palette=PALETTE,
        )
    )
    buttons.append(
        _btn(
            ui.Icons.FULLSCREEN_EXIT if state.is_fullscreen else ui.Icons.FULLSCREEN,
            lambda e: actions.on_toggle_fullscreen(),
            "全屏",
            color=C_TEXT_SUB,
        )
    )

    return ui.Container(
        content=ui.Column(
            controls=[
                timeline,
                ui.Row(
                    controls=buttons,
                    spacing=SPACING_SM,
                    vertical_alignment=ui.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=0,
        ),
        bgcolor=C_BG_PANEL,
        border=ui.Border.only(top=ui.BorderSide(1, C_DIVIDER)),
        padding=BAR_PADDING,
    )
