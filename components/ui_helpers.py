"""
通用 UI 辅助函数 — 可复用的控件工厂。
"""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from configs.theme import (
    C_BORDER,
    C_PRIMARY,
    C_TEXT,
    C_TEXT_SUB,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    ICON_SIZE_LG,
)


def icon_button(
    icon: str,
    on_click: Callable | None = None,
    *,
    tooltip: str = "",
    enabled: bool = True,
    color: Optional[str] = None,
    icon_size: int = ICON_SIZE_LG,
) -> ft.IconButton:
    """构建标准图标按钮。"""
    return ft.IconButton(
        icon=icon,
        icon_color=color or C_TEXT,
        on_click=on_click,
        tooltip=tooltip,
        disabled=not enabled,
        icon_size=icon_size,
    )


def text_label(
    value: str,
    *,
    color: str = C_TEXT,
    size: int = FONT_SIZE_SMALL,
    weight: ft.FontWeight = ft.FontWeight.W_400,
    max_lines: int = 0,
    overflow: ft.TextOverflow = ft.TextOverflow.ELLIPSIS,
    text_align: ft.TextAlign = ft.TextAlign.LEFT,
) -> ft.Text:
    """构建标准文本标签。"""
    return ft.Text(
        value=value,
        color=color,
        size=size,
        weight=weight,
        max_lines=max_lines,
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
) -> ft.Slider:
    """构建标准滑块。"""
    return ft.Slider(
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
) -> ft.Container:
    """构建分割线。"""
    if horizontal:
        return ft.Container(
            height=thickness,
            bgcolor=color,
            margin=ft.Margin.symmetric(horizontal=12, vertical=4),
        )
    return ft.Container(
        width=thickness,
        bgcolor=color,
        margin=ft.Margin.symmetric(vertical=12, horizontal=4),
    )


def empty_state(
    icon: str,
    message: str,
    *,
    sub_message: str = "",
) -> ft.Container:
    """构建空状态占位。"""
    controls: list[ft.Control] = [
        ft.Icon(icon, size=56, color=C_TEXT_SUB),
        ft.Text(message, color=C_TEXT_SUB, size=FONT_SIZE_BODY),
    ]
    if sub_message:
        controls.append(
            ft.Text(sub_message, color=C_TEXT_SUB, size=FONT_SIZE_TINY)
        )
    return ft.Container(
        content=ft.Column(
            controls=controls,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )
