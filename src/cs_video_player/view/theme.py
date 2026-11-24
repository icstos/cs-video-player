"""设计层 —— 播放器色表 + cs-ui 令牌的语义投影。

这里**不定义**字号、间距与图标刻度：那些的唯一事实源是 ``ui.core.tokens``。
本模块做三件事：

1. 声明这个产品唯一的自选色 :data:`BRAND_PRIMARY`（科技蓝）；
2. 用 :class:`MediaPalette` 把它推导成整套播放器色表（画面底色、面板、轨道、
   选中态……），同参数同结果、可缓存、可打印；
3. 把算出来的角色、以及 cs-ui 的字号 / 图标 / 4px 网格 / 控件高度，投影成
   业务侧读得懂的名字（``C_BG_PANEL``、``FONT_SIZE_SMALL``……）。

于是「换品牌色」只是改一个常量；「查当前配色」读 ``PALETTE.as_dict()``；
「核对某个间距是否越界」对照 ``SPACE`` 即可 —— 全部可查、可复算。

:class:`MediaPalette` 从 cs-ui 收回到了这里：它只依赖品牌色与明暗档，属于
设计决策而不是通用控件，放在设计层才能保证「配色公式」和「用色的人」在同一处。
深色是播放器的固定档：画面本身是内容，浅色界面会在四周形成亮边框抢注意力。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

import ui
from ui import CONTROL_HEIGHT, FONT_SIZE, ICON_SIZE, RADIUS, SPACE
from ui.core.palette import build_scheme, tonal
from ui.core.tokens import PRIMARY_SEEDS, semantic_text


@dataclass(frozen=True, slots=True)
class MediaPalette:
    """播放器语义色表 —— 由品牌色与明暗档唯一决定。

    字段是**用途**不是色值：``track`` 是未填充轨道，``panel`` 是控制条底，
    ``active`` 是选中项，``darkest`` 是画面区黑底。任何一处想换颜色，都应改
    :meth:`derive` 的映射，而不是在组件里塞一个十六进制。

    ``as_dict()`` 是给检索 / 快照用的：整张表可以打印、可以断言、可以复算。
    """

    brand: str          # 品牌色本身（主按钮、进度、强调文字）
    primary: str
    hover: str          # 悬停：比主色亮一档
    track: str          # 未填充轨道 / 细边框
    border: str         # 面板描边
    divider: str        # 分割线
    panel: str          # 控制条 / 侧栏
    surface: str        # 页面底
    darkest: str        # 画面区黑底
    active: str         # 选中项底色
    text: str           # 主要文字
    muted: str          # 次要文字 / 图标
    danger: str         # 破坏性操作

    def as_dict(self) -> dict[str, str]:
        """整张色表的可序列化快照（供检索、测试与文档使用）。"""
        return asdict(self)

    @classmethod
    def derive(
        cls, brand: str = PRIMARY_SEEDS["blue"], *, mode: str = "dark"
    ) -> MediaPalette:
        """按品牌色与明暗档推导色表；同参数同结果，结果带缓存。

        Args:
            brand: 十六进制品牌色。
            mode: ``"dark"`` / ``"light"``，与 ``build_scheme`` 的档位一致。
        """
        return _derive(brand, mode)


@lru_cache(maxsize=16)
def _derive(brand: str, mode: str) -> MediaPalette:
    """色表推导本体。

    只做两件事：把 ``build_scheme`` 的角色投影成播放器语汇，再从 ``tonal``
    色阶取一档作为悬停态。不读全局状态、不做 I/O —— 所以可缓存、可复算。
    """
    scheme = build_scheme(brand, mode)
    ramp = tonal(brand)
    return MediaPalette(
        brand=brand,
        primary=scheme["primary"],
        hover=ramp[300],
        track=scheme["outline_variant"],
        # 1px 线用表面梯度而不是 outline：M3 的 outline 在暗色下是亮灰（#797C7F），
        # 拉成一整条侧栏边框会盖过内容；表面梯度差一档刚好「看得见、不抢戏」。
        border=scheme["surface_container_high"],
        divider=scheme["surface_container"],
        panel=scheme["surface_container_low"],
        surface=scheme["surface"],
        darkest=scheme["surface_container_lowest"],
        active=scheme["primary_container"],
        text=scheme["on_surface"],
        muted=scheme["on_surface_variant"],
        danger=scheme["error"],
    )


# ─── 唯一色值输入 ───
#: 品牌蓝。main.py 会把它写进 ui 主题，ui 组件与自绘控件因此同源。
BRAND_PRIMARY = "#3B9CFF"
#: 播放器固定深色；与 ``MediaPalette.derive`` 的档位一致。
THEME_MODE = "dark"

#: 整套色表（14 个语义角色），由品牌色 + 明暗档唯一决定，带缓存。
PALETTE = MediaPalette.derive(BRAND_PRIMARY, mode=THEME_MODE)

# ─── 主色 / 交互 ───
C_PRIMARY = PALETTE.primary
C_PRIMARY_DARK = PALETTE.active
C_HOVER = PALETTE.hover
C_GLOW = ui.Colors.with_opacity(0.2, C_PRIMARY)

# ─── 背景层级：由深到浅，四级表面梯度 ───
C_BG_DARKEST = PALETTE.darkest       # 画面区
C_BG_DARK = PALETTE.surface          # 页面底
C_BG_PANEL = PALETTE.panel           # 侧栏 / 控制条
C_BG_ITEM = PALETTE.divider          # 列表项常态
C_BG_ACTIVE = PALETTE.active         # 当前播放项
C_BG_HOVER = PALETTE.border          # 列表项悬停

# ─── 文字：三档视觉重量 ───
C_TEXT = PALETTE.text
C_TEXT_SUB = PALETTE.muted
C_TEXT_DIM = ui.Colors.with_opacity(0.38, C_TEXT)

# ─── 边框 / 分割线 ───
C_BORDER = PALETTE.border
C_BORDER_LIGHT = PALETTE.track
C_DIVIDER = PALETTE.divider

# ─── 功能色：走 cs-ui 的语义色（按暗色档求解对比度） ───
C_RED = PALETTE.danger
C_GREEN = semantic_text("success", mode=THEME_MODE)
C_YELLOW = semantic_text("warning", mode=THEME_MODE)
C_ORANGE = semantic_text("info", mode=THEME_MODE)

# ─── 滑块 ───
SEEK_BAR_COLOR = PALETTE.track
SEEK_BAR_HOVER_COLOR = PALETTE.hover

# ─── 排印：只取 cs-ui 的字阶，最小 11（不再有 9/10 这种读不清的字） ───
FONT_SIZE_TITLE = FONT_SIZE["body"]        # 14
FONT_SIZE_BODY = FONT_SIZE["small"]        # 12
FONT_SIZE_SMALL = FONT_SIZE["caption"]     # 11
FONT_SIZE_TINY = FONT_SIZE["caption"]      # 11
FONT_SIZE_MICRO = FONT_SIZE["caption"]     # 11

# ─── 图标：cs-ui 的六级刻度 ───
ICON_SIZE_SM = ICON_SIZE["sm"]             # 14
ICON_SIZE_MD = ICON_SIZE["md"]             # 16
ICON_SIZE_LG = ICON_SIZE["lg"]             # 18
ICON_SIZE_XL = ICON_SIZE["xl"]             # 20
ICON_SIZE_XXL = ICON_SIZE["2xl"]           # 24

# ─── 间距：4px 网格 ───
SPACING_XS = SPACE["1"]                    # 4
SPACING_SM = SPACE["1"]                    # 4
SPACING_MD = SPACE["2"]                    # 8
SPACING_LG = SPACE["3"]                    # 12
SPACING_XL = SPACE["4"]                    # 16

# ─── 圆角 ───
RADIUS_SM = RADIUS["sm"]
RADIUS_MD = RADIUS["md"]
RADIUS_LG = RADIUS["lg"]

# ─── 控制栏高度：与 cs-ui 的控件高度刻度一致 ───
CONTROLS_BAR_HEIGHT = CONTROL_HEIGHT["lg"]   # 44
CONTROLS_BAR_COMPACT = CONTROL_HEIGHT["md"]  # 36


def palette_snapshot() -> dict[str, str]:
    """设计层的可查询快照：Agent / 文档 / 测试可直接读，不必反推一堆常量。"""
    return {"brand": BRAND_PRIMARY, "mode": THEME_MODE, **PALETTE.as_dict()}
