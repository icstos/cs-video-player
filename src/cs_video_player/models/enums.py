"""models / enums —— 状态枚举，无业务逻辑，所有层共享。"""

from __future__ import annotations

from enum import Enum


class PlayMode(Enum):
    """业务播放模式。原生播放列表模式由 :class:`ListMode` 表达。"""

    SEQUENCE = "sequence"
    REPEAT_ALL = "repeat_all"
    REPEAT_ONE = "repeat_one"
    SHUFFLE = "shuffle"

    @property
    def label(self) -> str:
        """给用户看的短标签。"""
        return {
            PlayMode.SEQUENCE: "顺序播放",
            PlayMode.REPEAT_ALL: "列表循环",
            PlayMode.REPEAT_ONE: "单曲循环",
            PlayMode.SHUFFLE: "随机播放",
        }[self]


class SortKey(Enum):
    """播放列表排序方式（只影响展示顺序，不改底层索引）。"""

    DEFAULT = "default"
    NAME = "name"
    SIZE = "size"
    DATE = "date"

    @property
    def label(self) -> str:
        """排序条的紧凑文案。"""
        return {
            SortKey.DEFAULT: "默认",
            SortKey.NAME: "名称",
            SortKey.SIZE: "大小",
            SortKey.DATE: "日期",
        }[self]


class ListMode(Enum):
    """播放器可消费的播放列表模式（业务模式经 Service 规则投影而来）。"""

    NONE = "none"
    SINGLE = "single"
    LOOP = "loop"


class NoticeTone(Enum):
    """一次性回执的语气。"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FileRequestKind(Enum):
    """ViewModel 向 View 发出的文件对话框请求类型。"""

    FILES = "files"
    FOLDER = "folder"
