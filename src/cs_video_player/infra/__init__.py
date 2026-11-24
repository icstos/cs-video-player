"""基础设施层 —— 抽象端口 + 技术实现适配器。

对外承诺 :mod:`cs_video_player.infra.ports` 中的 Protocol；``media`` /
``preferences`` / ``scanner`` 是它们的实现，由启动入口注入到 Service。
本层不含业务规则，也不 import Service / ViewModel / View。
"""

from cs_video_player.infra.media import MediaController
from cs_video_player.infra.ports import (
    ErrorHandler,
    MediaPort,
    PreferencesPort,
    ScannerPort,
    VideoControl,
)
from cs_video_player.infra.preferences import JsonPreferences
from cs_video_player.infra.scanner import FileSystemScanner

__all__ = [
    "ErrorHandler", "FileSystemScanner", "JsonPreferences", "MediaController",
    "MediaPort", "PreferencesPort", "ScannerPort", "VideoControl",
]
