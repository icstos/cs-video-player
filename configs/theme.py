"""设计层 —— cs-ui 令牌在「CS Video Player」里的语义投影。

这里**不定义**颜色、字号、间距与图标刻度：那些的唯一事实源是 ``ui.core.tokens``
与 :class:`ui.MediaPalette`。本模块只做两件事：

1. 声明这个产品唯一的自选色 :data:`BRAND_PRIMARY`（科技蓝），把它交给
   ``MediaPalette.derive(brand, mode="dark")`` 算出整套播放器色表；
2. 把算出来的角色、以及 cs-ui 的字号 / 图标 / 4px 网格 / 控件高度，投影成
   业务侧读得懂的名字（``C_BG_PANEL``、``FONT_SIZE_SMALL``……）。

于是「换品牌色」只是改一个常量；「查当前配色」读 ``PALETTE.as_dict()``；
「核对某个间距是否越界」对照 ``SPACE`` 即可 —— 全部可查、可复算。
深色是播放器的固定档：画面本身是内容，浅色界面会在四周形成亮边框抢注意力。
"""

from __future__ import annotations

import ui
from ui import CONTROL_HEIGHT, FONT_SIZE, ICON_SIZE, RADIUS, SPACE
from ui.core.tokens import semantic_text
from ui.display.media import MediaPalette

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

#: 设计层的可查询快照：Agent / 文档 / 测试可直接读，不必反推一堆常量。
def palette_snapshot() -> dict[str, str]:
    """返回当前播放器色表（含品牌色与模式）。"""
    return {"brand": BRAND_PRIMARY, "mode": THEME_MODE, **PALETTE.as_dict()}
