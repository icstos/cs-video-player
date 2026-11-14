"""原生视频后端门面 —— 全项目只有这里 ``import flet_video``。

为什么收成一层：``flet_video`` 的字段（``volume`` / ``playback_rate`` / ``muted`` /
``fullscreen``）是属性、控制方法是 async，全屏控制条又要按品牌色下发**具体色值**
（Flutter 侧不解析角色名）。把这些散落在视图里，任何一次扩展包升级都得翻遍 UI；
收在一处之后，视图只认 ``NativeVideo`` / ``desktop_controls`` 这几个名字。

约定：``ui.Video`` 曾经是「嵌在正文里的播放器外壳」，已随视频能力一起从 cs-ui
移除；本项目的播放器接管了全部交互，因此直接用带完整事件与 ``ref`` 的
``NativeVideo``，二者不再混用。
"""

from __future__ import annotations

import flet_video as fv

from configs.theme import MediaPalette, PALETTE

__all__ = [
    "MaterialDesktopVideoControls",
    "NativeVideo",
    "PlaylistMode",
    "VideoControlsMode",
    "VideoMedia",
    "desktop_controls",
]

#: 带完整事件与 ``ref`` 的底层播放器。
NativeVideo = fv.Video
#: 播放列表里的一项：``resource`` 加可选的 ``http_headers`` / ``extras``。
VideoMedia = fv.VideoMedia
#: 播放列表模式：``NONE`` / ``LOOP`` / ``SINGLE``。
PlaylistMode = fv.PlaylistMode
#: 控制条形态：``NORMAL`` / ``FULLSCREEN`` / ``NONE``。
VideoControlsMode = fv.VideoControlsMode
MaterialDesktopVideoControls = fv.MaterialDesktopVideoControls


def desktop_controls(
    palette: MediaPalette | None = None,
) -> MaterialDesktopVideoControls:
    """主题化的桌面全屏控制条。

    把 :class:`~configs.theme.MediaPalette` 的结果下发给原生控制条；与控制栏
    自绘部分同源，切到全屏时不会突然换一套蓝。交互参数固定：单击画面不切换
    播放、双击进/出全屏、挂载时不抢占画面 —— 控制栏由应用自己画。
    """
    p = palette or PALETTE
    return MaterialDesktopVideoControls(
        seek_bar_position_color=p.primary,
        seek_bar_thumb_color=p.primary,
        seek_bar_color=p.track,
        seek_bar_hover_color=p.hover,
        volume_bar_active_color=p.primary,
        volume_bar_thumb_color=p.primary,
        volume_bar_color=p.track,
        button_bar_button_color=p.text,
        play_and_pause_on_tap=False,
        toggle_fullscreen_on_double_press=True,
        visible_on_mount=False,
    )
