"""视图模型层 —— 纯 Python 状态适配器，不依赖任何 UI 控件。

依赖方向：View → ViewModel → Service → Infra；所有层可引用 Models。
"""

from cs_video_player.viewmodel.app_vm import AppViewModel

__all__ = ["AppViewModel"]
