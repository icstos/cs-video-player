"""播放控制件 —— 纯函数：值从参数进，意图从回调出。

时间轴、音量、倍速、图标按钮都不持有状态，因此可以脱离播放器单独构造、单独
截图、单独核对按钮清单。状态归调用方（``player_area`` 的 ``use_state``），
这里只负责画。

配色也不在这里定义：默认取设计层的 :data:`configs.theme.PALETTE`，与画面区、
侧边栏、全屏控制条同源 —— 换品牌色时整台播放器一起变，不会只剩控制栏是旧蓝。

与原 cs-ui 版本的差别只有两处：保留控件树的纯函数契约（不用 observable 的
``ui.Slider``），配色默认值从「读全局主题」改成「读设计层快照」，少一次全局
状态依赖。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import ui
from ui.core.tokens import FONT_SIZE, FONT_WEIGHT, ICON_SIZE, SPACE

from cs_video_player.configs.theme import MediaPalette, PALETTE
from cs_video_player.utils.formatters import fmt_rate, fmt_time

__all__ = [
    "BAR_PADDING",
    "VOLUME_SLIDER_WIDTH",
    "IconAction",
    "SpeedMenu",
    "TimeSlider",
    "VolumeControl",
]

#: 音量滑块的轨道宽度。控制栏一行里既要有倍速、标题，又要留出主画面，
#: 80 是「能拖准 5% 又不吃掉标题」的折中；取自 4px 网格，不是手挑的数。
VOLUME_SLIDER_WIDTH = SPACE["10"] * 2

#: 控制条内边距：左右对称给滑块拇指留余量，上下 1 档贴着 4px 网格。
BAR_PADDING = ui.Padding.only(
    left=SPACE["2"], right=SPACE["2"], top=SPACE["1"], bottom=SPACE["1"]
)


def _palette(palette: MediaPalette | None) -> MediaPalette:
    """统一取色：显式传入优先，否则用设计层快照（固定深色档）。"""
    return palette or PALETTE


def IconAction(
    icon,
    on_click: Callable | None = None,
    *,
    tooltip: str = "",
    disabled: bool = False,
    color: str | None = None,
    size: int = ICON_SIZE["md"],
    palette: MediaPalette | None = None,
) -> ui.IconButton:
    """紧凑图标按钮：控制栏里的最小交互单元。

    内边距走令牌、图标尺寸走图标刻度，所以一排按钮高度天然齐平；``tooltip``
    是唯一文案，避免为了说清一个图标再塞一行字压低信息密度。
    """
    p = _palette(palette)
    return ui.IconButton(
        icon=icon,
        icon_color=color or p.text,
        on_click=on_click,
        tooltip=tooltip,
        disabled=disabled,
        icon_size=size,
        style=ui.ButtonStyle(padding=ui.Padding.all(SPACE["1"])),
    )


def TimeSlider(
    position_ms: int,
    duration_ms: int,
    *,
    show_remaining: bool = False,
    label: str = "",
    disabled: bool = False,
    on_change_start: Callable | None = None,
    on_change: Callable | None = None,
    on_change_end: Callable | None = None,
    on_toggle_time: Callable | None = None,
    formatter: Callable[[int], str] = fmt_time,
    palette: MediaPalette | None = None,
) -> ui.Row:
    """时间轴：当前时间 + 进度滑块 + 总时长。

    左侧时间可点（``on_toggle_time``）在「已播 / 剩余」之间切换，负号只出现在
    剩余模式；拖动时的浮标文案由调用方给（``label``），组件不猜业务格式。
    三个滑块回调分别对应「开始拖 / 拖动预览 / 松手提交」，让视图模型能在拖动
    期间暂停位置轮询，避免画面回跳。
    """
    p = _palette(palette)
    maximum = max(duration_ms, 1)
    remaining = show_remaining and duration_ms > 0
    left_value = (
        f"-{formatter(max(0, duration_ms - position_ms))}"
        if remaining
        else formatter(position_ms)
    )
    left = ui.Text(left_value, color=p.muted, size=FONT_SIZE["caption"])
    if on_toggle_time is not None:
        left = ui.GestureDetector(content=left, on_tap=on_toggle_time)

    return ui.Row(
        controls=[
            left,
            # 原生滑块：ui.Slider 是 observable（要 .ui() 才能进控件树），
            # 这里要的是一个能直接摆进 Row 的 Control，故用底层类。
            ui.ft.Slider(
                min=0,
                max=maximum,
                value=min(max(position_ms, 0), maximum),
                active_color=p.primary,
                inactive_color=p.track,
                thumb_color=p.primary,
                expand=True,
                label=label,
                disabled=disabled,
                on_change_start=on_change_start,
                on_change=on_change,
                on_change_end=on_change_end,
            ),
            ui.Text(formatter(duration_ms), color=p.muted, size=FONT_SIZE["caption"]),
        ],
        spacing=SPACE["1"],
        vertical_alignment=ui.CrossAxisAlignment.CENTER,
    )


def VolumeControl(
    volume: float,
    muted: bool,
    *,
    on_change: Callable | None = None,
    on_toggle_mute: Callable | None = None,
    on_scroll: Callable | None = None,
    width: float = VOLUME_SLIDER_WIDTH,
    palette: MediaPalette | None = None,
) -> ui.Row:
    """音量组：图标按钮 + 短滑块，图标上滚滚轮也能调（``on_scroll``）。

    ``muted`` 时轨道归零但保留 ``volume`` 的值 —— 取消静音应回到原来的音量，
    而不是又从 0 开始拖。
    """
    p = _palette(palette)
    icon = ui.Icons.VOLUME_OFF if muted or volume <= 0 else ui.Icons.VOLUME_UP
    button = IconAction(
        icon, on_toggle_mute, tooltip="静音", color=p.muted, palette=p
    )
    if on_scroll is not None:
        button = ui.GestureDetector(content=button, on_scroll=on_scroll)
    return ui.Row(
        controls=[
            button,
            ui.ft.Slider(
                min=0,
                max=100,
                value=0 if muted else volume,
                active_color=p.primary,
                inactive_color=p.track,
                thumb_color=p.primary,
                width=width,
                on_change=on_change,
            ),
        ],
        spacing=SPACE["0"],
        vertical_alignment=ui.CrossAxisAlignment.CENTER,
    )


def SpeedMenu(
    rate: float,
    rates: Sequence[float],
    on_select: Callable[[float], None],
    *,
    formatter: Callable[[float], str] = fmt_rate,
    palette: MediaPalette | None = None,
) -> ui.PopupMenuButton:
    """倍速菜单：当前档打勾并高亮，选完即收起。

    档位由调用方给（不同业务对 0.25x~16x 的取舍不同），组件只负责把「当前值」
    显示成一行紧凑文案 —— 控制栏里不需要常驻 12 个按钮。
    """
    p = _palette(palette)
    items: list[ui.PopupMenuItem] = [
        ui.PopupMenuItem(
            content=ui.Text(
                formatter(value),
                color=p.primary if value == rate else p.text,
                size=FONT_SIZE["small"],
            ),
            icon=ui.Icons.CHECK if value == rate else None,
            on_click=lambda e, value=value: on_select(value),
        )
        for value in rates
    ]
    return ui.PopupMenuButton(
        # 纯数值（「1x」）看不出能点，跟一枚下拉箭头才符合交互直觉；
        # 箭头比文字弱一档，不跟当前倍速抢注意力。
        content=ui.Row(
            controls=[
                ui.Text(
                    formatter(rate),
                    color=p.primary,
                    size=FONT_SIZE["small"],
                    weight=FONT_WEIGHT["semibold"],
                ),
                ui.Icon(
                    ui.Icons.ARROW_DROP_DOWN,
                    size=ICON_SIZE["xs"],
                    color=p.muted,
                ),
            ],
            spacing=SPACE["0"],
        ),
        items=items,
        bgcolor=p.panel,
        menu_position=ui.PopupMenuPosition.UNDER,
    )
