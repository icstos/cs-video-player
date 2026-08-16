"""
侧边栏组件 — 播放列表、排序、文件打开、近期记录。

声明式组件：接收播放器状态与回调，高频状态隔离在组件内部。
支持折叠/展开切换。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List

import flet as ft

from configs.app_config import SORT_LABELS
from configs.theme import (
    C_BG_ACTIVE,
    C_BG_HOVER,
    C_BG_PANEL,
    C_BORDER,
    C_DIVIDER,
    C_PRIMARY,
    C_RED,
    C_TEXT,
    C_TEXT_SUB,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    FONT_SIZE_TITLE,
    ICON_SIZE_SM,
    ICON_SIZE_MD,
    SPACING_SM,
    SPACING_MD,
    SPACING_LG,
)
from core.models import PlaylistItem, SortKey
from utils.formatters import human_size


@ft.component
def Sidebar(
    display: List[tuple[int, PlaylistItem]],
    current_index: int,
    sort_key: SortKey,
    recents: List[str],
    on_play: Callable[[int], None],
    on_remove: Callable[[int], None],
    on_reorder: Callable[[int, int], None],
    on_sort: Callable[[SortKey], None],
    on_open_file: Callable,
    on_open_folder: Callable,
    on_open_recent: Callable[[str], None],
    on_clear_playlist: Callable,
    on_remove_recent: Callable[[str], None],
    on_toggle_visible: Callable,
    sidebar_visible: bool = True,
    sidebar_width: float = 280.0,
):
    """侧边栏组件。"""
    hovered_idx, set_hovered_idx = ft.use_state(-1)

    def _sort_btn(key: SortKey) -> ft.Container:
        active = sort_key == key
        return ft.Container(
            content=ft.Text(
                SORT_LABELS[key.value],
                color=C_PRIMARY if active else C_TEXT_SUB,
                size=FONT_SIZE_TINY,
                weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400,
            ),
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            border_radius=4,
            bgcolor=C_BG_ACTIVE if active else None,
            ink=True,
            on_click=lambda e: on_sort(key),
        )

    def _menu_btn(icon: str, text: str, on_click: Callable) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=ICON_SIZE_MD, color=C_PRIMARY),
                    ft.Text(text, color=C_TEXT, size=FONT_SIZE_BODY),
                ],
                spacing=SPACING_MD,
            ),
            padding=ft.Padding.symmetric(horizontal=10, vertical=7),
            border_radius=6,
            ink=True,
            on_click=on_click,
        )

    recent_items: list[ft.PopupMenuItem] = []
    if recents:
        for p in recents[:10]:
            recent_items.append(
                ft.PopupMenuItem(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.HISTORY, size=13, color=C_TEXT_SUB),
                            ft.Text(
                                Path(p).name,
                                color=C_TEXT,
                                size=FONT_SIZE_SMALL,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True,
                            ),
                        ],
                        spacing=SPACING_MD,
                    ),
                    on_click=lambda e, path=p: on_open_recent(path),
                )
            )
        recent_items.append(ft.PopupMenuItem())
        recent_items.append(
            ft.PopupMenuItem(
                content=ft.Text("清空记录", color=C_RED, size=FONT_SIZE_SMALL),
                icon=ft.Icons.CLEAR_ALL,
                on_click=lambda e: on_remove_recent(""),
            )
        )
    else:
        recent_items.append(
            ft.PopupMenuItem(
                content=ft.Text("暂无记录", color=C_TEXT_SUB, size=FONT_SIZE_SMALL),
                disabled=True,
            )
        )

    def _playlist_item(orig_idx: int, item: PlaylistItem, seq: int) -> ft.DragTarget:
        is_active = orig_idx == current_index
        is_hovered = seq == hovered_idx
        bg = C_BG_ACTIVE if is_active else (C_BG_HOVER if is_hovered else None)

        item_content = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.PLAY_CIRCLE if is_active else ft.Icons.VIDEO_FILE,
                        size=ICON_SIZE_SM,
                        color=C_PRIMARY if is_active else C_TEXT_SUB,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                item.title,
                                color=C_TEXT,
                                size=FONT_SIZE_SMALL,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400,
                            ),
                            ft.Text(
                                human_size(item.size),
                                color=C_TEXT_SUB,
                                size=FONT_SIZE_TINY,
                            ),
                        ],
                        spacing=1,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.DRAG_HANDLE, size=12, color=C_TEXT_SUB),
                ],
                spacing=SPACING_MD,
            ),
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            bgcolor=bg,
            border_radius=4,
            ink=True,
            on_click=lambda e: on_play(orig_idx),
            on_hover=lambda e: (
                set_hovered_idx(seq) if str(e.data) == "true" else set_hovered_idx(-1)
            ),
        )

        ctx = ft.ContextMenu(
            content=item_content,
            secondary_items=[
                ft.PopupMenuItem(
                    content=ft.Text("播放", color=C_TEXT, size=FONT_SIZE_SMALL),
                    icon=ft.Icons.PLAY_ARROW,
                    on_click=lambda e: on_play(orig_idx),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("从列表移除", color=C_RED, size=FONT_SIZE_SMALL),
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=lambda e: on_remove(orig_idx),
                ),
            ],
        )

        draggable = ft.Draggable(
            content=ctx,
            group="playlist",
            data=orig_idx,
            content_when_dragging=ft.Container(
                content=ft.Container(height=36, bgcolor=C_BORDER, border_radius=4),
                opacity=0.3,
            ),
        )

        def _on_accept(e: ft.DragTargetEvent):
            src = e.src
            if src is not None and src.data is not None:
                src_idx = int(src.data)
                if src_idx != orig_idx:
                    on_reorder(src_idx, orig_idx)

        return ft.DragTarget(
            content=draggable,
            group="playlist",
            on_accept=_on_accept,
        )

    playlist_controls: list[ft.Control] = [
        _playlist_item(oi, item, seq) for seq, (oi, item) in enumerate(display)
    ]
    if not playlist_controls:
        playlist_controls = [
            ft.Container(
                content=ft.Text(
                    "暂无视频\n请打开文件或文件夹",
                    color=C_TEXT_SUB,
                    size=FONT_SIZE_SMALL,
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                padding=30,
            )
        ]

    # ─── 侧边栏内容 ───
    sidebar_content = ft.Container(
        content=ft.Column(
            controls=[
                # 顶部标题栏 + 折叠按钮
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SMART_DISPLAY, size=18, color=C_PRIMARY),
                            ft.Text(
                                "CS Video Player",
                                color=C_TEXT,
                                size=FONT_SIZE_TITLE,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.Icons.MENU_OPEN_ROUNDED,
                                icon_color=C_TEXT_SUB,
                                icon_size=ICON_SIZE_MD,
                                tooltip="折叠侧边栏",
                                on_click=lambda e: on_toggle_visible(),
                                style=ft.ButtonStyle(
                                    padding=ft.Padding.all(4),
                                ),
                            ),
                        ],
                        spacing=SPACING_MD,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                ),
                # 菜单按钮区
                ft.Container(
                    content=ft.Column(
                        controls=[
                            _menu_btn(ft.Icons.VIDEO_FILE, "打开文件", on_open_file),
                            _menu_btn(ft.Icons.FOLDER_OPEN, "打开文件夹", on_open_folder),
                            ft.PopupMenuButton(
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.HISTORY, size=ICON_SIZE_MD, color=C_PRIMARY),
                                        ft.Text("近期记录", color=C_TEXT, size=FONT_SIZE_BODY),
                                    ],
                                    spacing=SPACING_MD,
                                ),
                                items=recent_items,
                                bgcolor=C_BG_PANEL,
                                menu_position=ft.PopupMenuPosition.UNDER,
                            ),
                        ],
                        spacing=1,
                    ),
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                ),
                # 分割线
                ft.Container(height=1, bgcolor=C_DIVIDER, margin=ft.Margin.symmetric(horizontal=10, vertical=3)),
                # 排序栏
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                "播放列表",
                                color=C_TEXT_SUB,
                                size=FONT_SIZE_TINY,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Container(expand=True),
                            *[_sort_btn(SortKey(k)) for k in ("default", "name", "size", "date")],
                        ],
                        spacing=SPACING_SM,
                    ),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                ),
                # 列表区
                ft.Container(
                    content=ft.ListView(
                        controls=playlist_controls,
                        expand=True,
                        spacing=1,
                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                    ),
                    expand=True,
                ),
                # 底部状态栏
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                f"{len(display)} 个视频",
                                color=C_TEXT_SUB,
                                size=FONT_SIZE_TINY,
                            ),
                            ft.Container(expand=True),
                            ft.Container(
                                content=ft.Text("清空", color=C_RED, size=FONT_SIZE_TINY),
                                padding=ft.Padding.symmetric(horizontal=6, vertical=1),
                                border_radius=4,
                                ink=True,
                                on_click=on_clear_playlist,
                                visible=bool(display),
                            ),
                        ],
                        spacing=SPACING_MD,
                    ),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    border=ft.Border.only(top=ft.BorderSide(1, C_DIVIDER)),
                ),
            ],
            spacing=0,
        ),
        width=sidebar_width if sidebar_visible else 0,
        bgcolor=C_BG_PANEL,
        border=ft.Border.only(right=ft.BorderSide(1, C_BORDER)),
        visible=sidebar_visible,
        expand=False,
    )

    return sidebar_content
