"""UI 词汇层 —— 把 cs-ui 的组件装配成这个播放器说话的方式。

各视图只写「结构 + 文案」，不写颜色、字号、圆角、内边距：这些统一由本模块和
:mod:`configs.theme`（cs-ui 令牌的语义投影）决定。好处很直接 —— 换品牌色、
调字号、改控件密度都只动一处，八个界面片段一起变，不会漏掉半棵树。

三条约定：

1. **控件一律走 ``ui`` 门面**，本模块不再直接依赖底层框架包；
2. **构件是纯函数**：值从参数进、意图从回调出，不持有状态、不读全局状态
   （配色是模块级常量快照，不是运行时可变状态），因此可单独构造、可单测；
3. **信息密度克制**：一个控件只承担一个意思，能用 tooltip 说清的不再加一行字。

对外只导出 :data:`__all__` 里的名字，视图层不需要知道 cs-ui 的具体类名。
"""

from __future__ import annotations

from typing import Callable, Optional

import ui
from ui import Button, Icons, Message, StyleType

from cs_video_player.components.media import IconAction
from cs_video_player.configs.theme import (
    C_BG_ACTIVE,
    C_BG_HOVER,
    C_BG_PANEL,
    C_DIVIDER,
    C_TEXT,
    C_TEXT_DIM,
    C_TEXT_SUB,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    FONT_SIZE_TITLE,
    ICON_SIZE_MD,
    ICON_SIZE_XL,
    PALETTE,
    RADIUS_SM,
    SPACING_LG,
    SPACING_MD,
    SPACING_SM,
    SPACING_XL,
)

__all__ = [
    "action_button",
    "caption",
    "clickable",
    "confirm_dialog",
    "empty_list",
    "empty_stage",
    "hairline",
    "icon_action",
    "muted",
    "panel",
    "popup_item",
    "section_label",
    "text",
    "title",
    "toast",
]

# ─────────────────────────────────────────────────────────────── 文本
def text(
    value: str,
    *,
    size: int = FONT_SIZE_SMALL,
    color: str = C_TEXT,
    weight: Optional[ui.FontWeight] = None,
    max_lines: Optional[int] = 1,
    align: Optional[ui.TextAlign] = None,
    expand: bool | int | None = None,
) -> ui.Text:
    """主文本：默认单行 + 省略号，避免长文件名把整行布局撑破。"""
    kwargs = {}
    if max_lines is not None:
        kwargs["max_lines"] = max_lines
        kwargs["overflow"] = ui.TextOverflow.ELLIPSIS
    if align is not None:
        kwargs["text_align"] = align
    if expand is not None:
        kwargs["expand"] = expand
    return ui.Text(
        value,
        size=size,
        color=color,
        weight=weight or ui.FontWeight.W_400,
        **kwargs,
    )


def title(value: str, **kwargs) -> ui.Text:
    """区块标题：14 / w700。"""
    return text(value, size=FONT_SIZE_TITLE, weight=ui.FontWeight.W_700, **kwargs)


def muted(value: str, *, size: int = FONT_SIZE_TINY, **kwargs) -> ui.Text:
    """次级信息：时间、大小、计数。"""
    return text(value, size=size, color=C_TEXT_SUB, **kwargs)


def caption(value: str, **kwargs) -> ui.Text:
    """辅助说明：与正文同级、次级色。"""
    return text(value, size=FONT_SIZE_BODY, color=C_TEXT_SUB, **kwargs)


def section_label(value: str) -> ui.Text:
    """分组标签（「播放列表」这类）：小字、半粗、次级色。"""
    return text(value, size=FONT_SIZE_TINY, color=C_TEXT_SUB, weight=ui.FontWeight.W_600)


# ─────────────────────────────────────────────────────────────── 容器与交互
def panel(
    content: ui.Control,
    *,
    width: float | None = None,
    expand: bool | int | None = None,
    bgcolor: str = C_BG_PANEL,
    border: Optional[ui.Border] = None,
    padding=None,
    visible: bool = True,
) -> ui.Container:
    """面板外壳：统一底色、圆角与可选边框。"""
    kwargs = {}
    if width is not None:
        kwargs["width"] = width
    if expand is not None:
        kwargs["expand"] = expand
    if padding is not None:
        kwargs["padding"] = padding
    if border is not None:
        kwargs["border"] = border
        kwargs["border_radius"] = RADIUS_SM
    return ui.Container(
        content=content, bgcolor=bgcolor, visible=visible, **kwargs
    )


def clickable(
    content: ui.Control,
    *,
    on_click: Callable | None = None,
    on_hover: Callable | None = None,
    bgcolor: str | None = None,
    padding=None,
    radius: float = RADIUS_SM,
    visible: bool = True,
) -> ui.Container:
    """可点击行 / 菜单项 / 排序小片：自带 ink 反馈与统一内边距。"""
    return ui.Container(
        content=content,
        padding=padding
        or ui.Padding.symmetric(horizontal=SPACING_MD, vertical=SPACING_SM),
        border_radius=radius,
        bgcolor=bgcolor,
        ink=True,
        on_click=on_click,
        on_hover=on_hover,
        visible=visible,
    )


def hairline(*, vertical: bool = False, color: str = C_DIVIDER) -> ui.Container:
    """1px 分隔线。横向留左右 12，纵向留上下 12，不贴边。"""
    if vertical:
        return ui.Container(
            width=1,
            bgcolor=color,
            margin=ui.Margin.symmetric(vertical=SPACING_LG, horizontal=SPACING_SM),
        )
    return ui.Container(
        height=1,
        bgcolor=color,
        margin=ui.Margin.symmetric(horizontal=SPACING_LG, vertical=SPACING_SM),
    )


def icon_action(
    icon,
    on_click: Callable | None = None,
    *,
    tooltip: str = "",
    disabled: bool = False,
    color: str | None = None,
    size: int = ICON_SIZE_MD,
) -> ui.IconButton:
    """控制栏图标按钮：:func:`components.media.IconAction` + 本产品的色表。"""
    return IconAction(
        icon,
        on_click,
        tooltip=tooltip,
        disabled=disabled,
        color=color,
        size=size,
        palette=PALETTE,
    )


def action_button(
    label: str,
    on_click: Callable,
    *,
    icon=None,
    primary: bool = True,
) -> Button:
    """空态 / 对话框里的实心主操作。"""
    return Button(
        label,
        icon=icon,
        on_click=on_click,
        style_type=StyleType.PRIMARY if primary else StyleType.DEFAULT,
    )


def popup_item(
    label: str,
    *,
    icon=None,
    on_click: Callable | None = None,
    color: str = C_TEXT,
    disabled: bool = False,
    size: int = FONT_SIZE_SMALL,
    checked: bool = False,
) -> ui.PopupMenuItem:
    """菜单项：图标 + 文案，当前项可打勾。"""
    return ui.PopupMenuItem(
        content=text(label, size=size, color=color),
        icon=icon,
        checked=checked,
        disabled=disabled,
        on_click=on_click,
    )


# ─────────────────────────────────────────────────────────────── 空态
def empty_list(message: str, *, hint: str = "") -> ui.Control:
    """侧栏列表的空态：一枚图标 + 一句人话 + 可选的下一步。"""
    controls: list[ui.Control] = [
        # 空态图标用次级文字色：比 38% 的极淡色更看得见，又不抢正文。
        ui.Icon(Icons.PLAYLIST_ADD, size=ICON_SIZE_XL, color=C_TEXT_SUB),
        ui.Container(height=SPACING_MD),
        muted(message, size=FONT_SIZE_SMALL),
    ]
    if hint:
        controls.append(ui.Container(height=SPACING_SM))
        controls.append(muted(hint, size=FONT_SIZE_TINY))
    return ui.Container(
        content=ui.Column(
            controls=controls,
            alignment=ui.MainAxisAlignment.CENTER,
            horizontal_alignment=ui.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        alignment=ui.Alignment.CENTER,
        padding=SPACING_XL,
        expand=True,
    )


def empty_stage(*, on_open: Callable | None = None) -> ui.Control:
    """画面区空态：告诉用户「现在没有视频」并给出唯一的主操作。

    文案只留两行 —— 格式列表放进次级说明，不铺一整屏帮助文字。
    """
    controls: list[ui.Control] = [
        ui.Icon(Icons.SMART_DISPLAY_OUTLINED, size=56, color=C_TEXT_DIM),
        ui.Container(height=SPACING_LG),
        text("还没有打开视频", size=FONT_SIZE_TITLE, weight=ui.FontWeight.W_600),
        ui.Container(height=SPACING_SM),
        muted("支持 MP4 · MKV · AVI · MOV · FLV 等常见格式", size=FONT_SIZE_SMALL),
    ]
    if on_open is not None:
        controls.append(ui.Container(height=SPACING_XL))
        controls.append(
            action_button("打开视频文件", on_open, icon=Icons.FOLDER_OPEN)
        )
    return ui.Container(
        content=ui.Column(
            controls=controls,
            alignment=ui.MainAxisAlignment.CENTER,
            horizontal_alignment=ui.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        expand=True,
        alignment=ui.Alignment.CENTER,
    )


# ─────────────────────────────────────────────────────────────── 反馈
def toast(page: ui.Page, message: str, *, tone: str = "info", duration: int = 3000) -> None:
    """一次性回执：cs-ui 的顶部居中 Message，同款合并、自动消失。"""
    style = StyleType(tone) if tone in {s.value for s in StyleType} else StyleType.INFO
    try:
        Message(message, style_type=style, duration=duration).show(page)
    except Exception:
        # 展示失败不该让业务流程中断（例如窗口正在关闭）。
        pass


def confirm_dialog(
    *,
    heading: str,
    message: str,
    confirm_label: str,
    cancel_label: str,
    on_confirm: Callable,
    on_cancel: Callable,
) -> ui.AlertDialog:
    """确认框：标题 + 一句说明 + 「取消 / 确认」，按钮文案写具体动作。

    两个回调负责 ``page.pop_dialog()``：对话框不持有页面引用，纯构件更容易测。
    """
    return ui.AlertDialog(
        modal=True,
        title=text(heading, size=FONT_SIZE_TITLE, weight=ui.FontWeight.W_600),
        content=ui.Container(
            content=text(
                message,
                size=FONT_SIZE_BODY,
                color=C_TEXT_SUB,
                max_lines=None,
            ),
            padding=ui.Padding.only(top=SPACING_SM, bottom=SPACING_MD),
        ),
        actions=[
            Button(cancel_label, on_click=on_cancel),
            Button(confirm_label, on_click=on_confirm),
        ],
        actions_alignment=ui.MainAxisAlignment.END,
        bgcolor=C_BG_PANEL,
    )


# ─────────────────────────────────────────────────────────────── 列表行样式
#: 供列表项在「常态 / 悬停 / 选中」之间切换的底色，集中在此避免各处自己拼。
ROW_BG = {
    "idle": None,
    "hover": C_BG_HOVER,
    "active": C_BG_ACTIVE,
}

#: 排序小片与播放列表行共用的内边距（4px 网格）。
ROW_PADDING = ui.Padding.symmetric(
    horizontal=SPACING_LG, vertical=SPACING_SM
)

__all__ += ["ROW_BG", "ROW_PADDING"]
