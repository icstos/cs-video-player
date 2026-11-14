"""媒体播放层 —— 视频能力（原生后端门面 + 控制件），不再由 cs-ui 提供。

cs-ui 只做通用 UI；视频播放器要接管时间轴、音量、全屏与播放列表状态，是一个
应用而不是一个控件，所以整层收在本项目：

* :mod:`.backend` —— ``flet_video`` 的唯一入口：原生播放器、播放列表类型、
  按品牌色下发的全屏控制条；
* :mod:`.controls` —— 无状态控制件：时间轴 / 音量 / 倍速 / 图标按钮，可脱离
  播放器单独构造与截图。

配色不在这层定义 —— :class:`configs.theme.MediaPalette` 是设计层的事，这里只
消费它。于是「换品牌色」仍然只改 :data:`configs.theme.BRAND_PRIMARY` 一处。
"""

from components.media.backend import (
    MaterialDesktopVideoControls,
    NativeVideo,
    PlaylistMode,
    VideoControlsMode,
    VideoMedia,
    desktop_controls,
)
from components.media.controls import (
    BAR_PADDING,
    VOLUME_SLIDER_WIDTH,
    IconAction,
    SpeedMenu,
    TimeSlider,
    VolumeControl,
)

__all__ = [
    "BAR_PADDING",
    "VOLUME_SLIDER_WIDTH",
    "IconAction",
    "MaterialDesktopVideoControls",
    "NativeVideo",
    "PlaylistMode",
    "SpeedMenu",
    "TimeSlider",
    "VideoControlsMode",
    "VideoMedia",
    "VolumeControl",
    "desktop_controls",
]
