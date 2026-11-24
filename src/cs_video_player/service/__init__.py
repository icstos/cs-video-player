"""服务层 —— 业务规则与编排。

只依赖 ``models`` 与 ``infra.ports``；不 import UI 框架、具体实现或上层模块。
"""

from cs_video_player.service.playback import Listener, PlaybackService

__all__ = ["Listener", "PlaybackService"]
