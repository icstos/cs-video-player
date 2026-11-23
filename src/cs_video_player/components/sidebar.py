"""侧边栏 —— 播放列表、排序、文件入口、近期记录。

一个 ``@ui.component`` 组件，只持有一份高频局部状态（悬停行号），其余全部来自
参数与回调。列表项支持拖拽排序与右键菜单；排序只改变展示顺序，不改变底层索引
（回调里传的是原始索引）。

结构从上到下：品牌栏 → 文件入口 → 分割线 → 播放列表（含排序条）→ 状态栏。
文案只保留必要的名词和动词，快捷键 / 格式说明交给 tooltip 与控制栏。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Sequence

import ui

from cs_video_player.configs.app_config import SIDEBAR_DEFAULT_WIDTH
from cs_video_player.configs.theme import (
    C_BG_PANEL,
    C_BORDER,
    C_DIVIDER,
    C_HOVER,
    C_PRIMARY,
    C_RED,
    C_TEXT,
    C_TEXT_SUB,
    CONTROLS_BAR_COMPACT,
    FONT_SIZE_BODY,
    FONT_SIZE_TINY,
    ICON_SIZE_LG,
    ICON_SIZE_MD,
    ICON_SIZE_SM,
    RADIUS_SM,
    SPACING_LG,
    SPACING_MD,
    SPACING_SM,
)
from cs_video_player.core.models import PlaylistItem, SortKey
from cs_video_player.utils.formatters import human_size
from cs_video_player.components.kit import (
    ROW_BG,
    ROW_PADDING,
    clickable,
    empty_list,
    hairline,
    icon_action,
    muted,
    popup_item,
    section_label,
    text,
    title,
)

#: 排序条顺序固定，与 SortKey 的四种取值一一对应。
SORT_ORDER: tuple[SortKey, ...] = (
    SortKey.DEFAULT,
    SortKey.NAME,
    SortKey.SIZE,
    SortKey.DATE,
)


@ui.component
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
    sidebar_width: float = SIDEBAR_DEFAULT_WIDTH,
):
    """侧边栏组件（签名与根组件保持一致）。"""
    hovered_seq, set_hovered_seq = ui.use_state(-1)

    # ─── 顶部：品牌 + 折叠 ───
    header = ui.Container(
        content=ui.Row(
            controls=[
                ui.Icon(ui.Icons.SMART_DISPLAY, size=ICON_SIZE_LG, color=C_PRIMARY),
                title("CS Video Player"),
                ui.Container(expand=True),
                icon_action(
                    ui.Icons.MENU_OPEN_ROUNDED,
                    lambda e: on_toggle_visible(),
                    tooltip="折叠侧边栏",
                    color=C_TEXT_SUB,
                ),
            ],
            spacing=SPACING_MD,
        ),
        padding=ui.Padding.symmetric(horizontal=SPACING_LG, vertical=SPACING_MD),
    )

    # ─── 文件入口 ───
    def _menu_row(icon, label: str, on_click: Callable) -> ui.Control:
        return clickable(
            ui.Row(
                controls=[
                    ui.Icon(icon, size=ICON_SIZE_MD, color=C_PRIMARY),
                    text(label, size=FONT_SIZE_BODY),
                ],
                spacing=SPACING_MD,
            ),
            on_click=on_click,
            padding=ui.Padding.symmetric(horizontal=SPACING_MD, vertical=SPACING_MD),
        )

    recent_items: list[ui.PopupMenuItem] = []
    if recents:
        for path in recents[:10]:
            recent_items.append(
                popup_item(
                    Path(path).name,
                    icon=ui.Icons.HISTORY,
                    on_click=lambda e, path=path: on_open_recent(path),
                )
            )
        recent_items.append(
            ui.PopupMenuItem(
                content=ui.Container(height=1, bgcolor=C_DIVIDER)
            )
        )
        recent_items.append(
            popup_item(
                "清空记录",
                icon=ui.Icons.CLEAR_ALL,
                color=C_RED,
                on_click=lambda e: on_remove_recent(""),
            )
        )
    else:
        recent_items.append(
            popup_item("暂无记录", disabled=True, color=C_TEXT_SUB)
        )

    actions = ui.Container(
        content=ui.Column(
            controls=[
                _menu_row(ui.Icons.VIDEO_FILE, "打开文件", on_open_file),
                _menu_row(ui.Icons.FOLDER_OPEN, "打开文件夹", on_open_folder),
                ui.PopupMenuButton(
                    content=ui.Row(
                        controls=[
                            ui.Icon(ui.Icons.HISTORY, size=ICON_SIZE_MD, color=C_PRIMARY),
                            text("近期记录", size=FONT_SIZE_BODY),
                        ],
                        spacing=SPACING_MD,
                    ),
                    items=recent_items,
                    bgcolor=C_BG_PANEL,
                    menu_position=ui.PopupMenuPosition.UNDER,
                ),
            ],
            spacing=0,
        ),
        padding=ui.Padding.symmetric(horizontal=SPACING_SM, vertical=SPACING_SM),
    )

    # ─── 排序条 ───
    def _sort_chip(key: SortKey) -> ui.Control:
        active = sort_key == key
        return ui.Container(
            content=text(
                key.label,
                size=FONT_SIZE_TINY,
                # 选中态底色是深蓝（primary_container），再用主色写字会糊成一团；
                # 亮蓝 hover 档压在上面有 ~4.9:1，既保留强调又读得清。
                color=C_HOVER if active else C_TEXT_SUB,
                weight=ui.FontWeight.W_600 if active else ui.FontWeight.W_400,
            ),
            padding=ui.Padding.symmetric(horizontal=SPACING_MD, vertical=SPACING_SM),
            border_radius=RADIUS_SM,
            bgcolor=ROW_BG["active"] if active else None,
            ink=True,
            on_click=lambda e: on_sort(key),
        )

    sort_bar = ui.Container(
        content=ui.Row(
            controls=[
                section_label("播放列表"),
                ui.Container(expand=True),
                *[_sort_chip(key) for key in SORT_ORDER],
            ],
            spacing=SPACING_SM,
        ),
        padding=ui.Padding.symmetric(horizontal=SPACING_LG, vertical=SPACING_SM),
    )

    # ─── 播放列表项 ───
    def _playlist_row(orig_idx: int, item: PlaylistItem, seq: int) -> ui.DragTarget:
        is_active = orig_idx == current_index
        is_hovered = seq == hovered_seq
        bg = (
            ROW_BG["active"]
            if is_active
            else (ROW_BG["hover"] if is_hovered else ROW_BG["idle"])
        )

        row = clickable(
            ui.Row(
                controls=[
                    ui.Icon(
                        ui.Icons.PLAY_CIRCLE if is_active else ui.Icons.VIDEO_FILE,
                        size=ICON_SIZE_SM,
                        color=C_PRIMARY if is_active else C_TEXT_SUB,
                    ),
                    ui.Column(
                        controls=[
                            text(
                                item.title,
                                color=C_TEXT,
                                weight=ui.FontWeight.W_600
                                if is_active
                                else ui.FontWeight.W_400,
                            ),
                            muted(human_size(item.size)),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ui.Icon(ui.Icons.DRAG_HANDLE, size=ICON_SIZE_SM, color=C_TEXT_SUB),
                ],
                spacing=SPACING_MD,
            ),
            on_click=lambda e: on_play(orig_idx),
            on_hover=lambda e: set_hovered_seq(
                seq if str(e.data) == "true" else -1
            ),
            bgcolor=bg,
            padding=ROW_PADDING,
            radius=RADIUS_SM,
        )

        context = ui.ContextMenu(
            content=row,
            secondary_items=[
                popup_item(
                    "播放",
                    icon=ui.Icons.PLAY_ARROW,
                    on_click=lambda e: on_play(orig_idx),
                ),
                popup_item(
                    "从列表移除",
                    icon=ui.Icons.DELETE_OUTLINE,
                    color=C_RED,
                    on_click=lambda e: on_remove(orig_idx),
                ),
            ],
        )

        draggable = ui.Draggable(
            content=context,
            group="playlist",
            data=orig_idx,
            content_when_dragging=ui.Container(
                content=ui.Container(
                    height=CONTROLS_BAR_COMPACT,
                    bgcolor=C_BORDER,
                    border_radius=RADIUS_SM,
                ),
                opacity=0.3,
            ),
        )

        def _on_accept(e: ui.DragTargetEvent):
            src = e.src
            if src is not None and src.data is not None:
                src_idx = int(src.data)
                if src_idx != orig_idx:
                    on_reorder(src_idx, orig_idx)

        return ui.DragTarget(
            content=draggable,
            group="playlist",
            on_accept=_on_accept,
        )

    rows: Sequence[ui.Control] = (
        [_playlist_row(oi, item, seq) for seq, (oi, item) in enumerate(display)]
        or [empty_list("列表还是空的", hint="打开文件或文件夹开始播放")]
    )

    list_area = ui.Container(
        content=ui.ListView(
            controls=list(rows),
            expand=True,
            spacing=1,
            padding=ui.Padding.symmetric(horizontal=SPACING_SM, vertical=SPACING_SM),
        ),
        expand=True,
    )

    # ─── 底部状态 ───
    footer = ui.Container(
        content=ui.Row(
            controls=[
                muted(f"{len(display)} 个视频"),
                ui.Container(expand=True),
                clickable(
                    text("清空", size=FONT_SIZE_TINY, color=C_RED),
                    on_click=on_clear_playlist,
                    padding=ui.Padding.symmetric(
                        horizontal=SPACING_MD, vertical=SPACING_SM
                    ),
                    radius=RADIUS_SM,
                    visible=bool(display),
                ),
            ],
            spacing=SPACING_MD,
        ),
        padding=ui.Padding.symmetric(horizontal=SPACING_LG, vertical=SPACING_SM),
        border=ui.Border.only(top=ui.BorderSide(1, C_DIVIDER)),
    )

    return ui.Container(
        content=ui.Column(
            controls=[header, actions, hairline(), sort_bar, list_area, footer],
            spacing=0,
        ),
        width=sidebar_width if sidebar_visible else 0,
        bgcolor=C_BG_PANEL,
        border=ui.Border.only(right=ui.BorderSide(1, C_BORDER)),
        visible=sidebar_visible,
        expand=False,
    )
