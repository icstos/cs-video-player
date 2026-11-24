"""视图层 —— cs-ui 声明式渲染 + 平台事件分发，无任何业务逻辑。

依赖：View → ViewModel → Service → Infra；所有层可引用 Models。
唯一允许 import ``flet_video`` 的文件是本层的 ``native_video.py``。
"""

from cs_video_player.view.app import App
from cs_video_player.view.control_bar import build_control_bar
from cs_video_player.view.native_video import VideoHandle, fullscreen_controls
from cs_video_player.view.player_area import PlayerArea
from cs_video_player.view.sidebar import Sidebar
from cs_video_player.view.theme import MediaPalette, PALETTE, palette_snapshot

__all__ = [
    "App", "MediaPalette", "PALETTE", "PlayerArea", "Sidebar", "VideoHandle",
    "build_control_bar", "fullscreen_controls", "palette_snapshot",
]
