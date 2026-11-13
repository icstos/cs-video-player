"""兼容层 —— 旧版 UI 辅助函数，全部改为经 ``ui`` 门面构造。

**新代码请用 :mod:`components.kit`**：那里的构件按产品语汇命名、配色来自
cs-ui 色表、参数也更克制。本模块只保留旧名字，避免外部脚本 / 早期示例失效，
不再新增函数。

唯一还使用原生控件的是 ``styled_slider``：cs-ui 的 ``ui.Slider`` 是 observable
（要构造后调 ``.ui()``），与旧函数「返回一个控件」的契约不同；这里用 cs-ui 门面
提供的 ``ui.NativeSlider``，应用侧不需要知道底层框架包。
"""

from __future__ import annotations

from typing import Callable, Optional

import ui

from configs.theme import (
    C_BORDER,
    C_PRIMARY,
    C_TEXT,
    FONT_SIZE_SMALL,
    ICON_SIZE_LG,
    SPACING_LG,
    SPACING_SM,
)
from components.kit import empty_list, hairline, icon_action

__all__ = ["divider", "empty_state", "icon_button", "styled_slider", "text_label"]


def icon_button(
    icon: str,
    on_click: Callable | None = None,
    *,
    tooltip: str = "",
    enabled: bool = True,
    color: Optional[str] = None,
    icon_size: int = ICON_SIZE_LG,
) -> ui.IconButton:
    """标准图标按钮 → kit.icon_action。"""
    return icon_action(
        icon,
        on_click,
        tooltip=tooltip,
        disabled=not enabled,
        color=color,
        size=icon_size,
    )


def text_label(
    value: str,
    *,
    color: str = C_TEXT,
    size: int = FONT_SIZE_SMALL,
    weight: ui.FontWeight = ui.FontWeight.W_400,
    max_lines: int = 0,
    overflow: ui.TextOverflow = ui.TextOverflow.ELLIPSIS,
    text_align: ui.TextAlign = ui.TextAlign.LEFT,
) -> ui.Text:
    """标准文本标签（保留旧签名，含 overflow / text_align）。"""
    return ui.Text(
        value=value,
        color=color,
        size=size,
        weight=weight,
        max_lines=max_lines or None,
        overflow=overflow,
        text_align=text_align,
    )


def styled_slider(
    value: float,
    *,
    min_val: float = 0,
    max_val: float = 100,
    on_change: Callable | None = None,
    on_change_start: Callable | None = None,
    on_change_end: Callable | None = None,
    expand: bool = False,
    width: Optional[float] = None,
):
    """标准滑块（cs-ui 门面里的原生滑块）。"""
    return ui.NativeSlider(
        min=min_val,
        max=max_val,
        value=value,
        active_color=C_PRIMARY,
        inactive_color=C_BORDER,
        thumb_color=C_PRIMARY,
        expand=expand,
        width=width,
        on_change=on_change,
        on_change_start=on_change_start,
        on_change_end=on_change_end,
    )


def divider(
    *,
    horizontal: bool = True,
    color: str = C_BORDER,
    thickness: float = 1,
) -> ui.Container:
    """分割线 → kit.hairline（thickness 保留但统一走 1px 设计）。"""
    line = hairline()
    if horizontal:
        return line
    return ui.Container(
        width=thickness,
        bgcolor=color,
        margin=ui.Margin.symmetric(
            vertical=SPACING_LG, horizontal=SPACING_SM
        ),
    )


def empty_state(
    icon: str,
    message: str,
    *,
    sub_message: str = "",
) -> ui.Container:
    """空状态占位 → kit.empty_list（图标参数保留以兼容旧调用）。"""
    return empty_list(message, hint=sub_message)
