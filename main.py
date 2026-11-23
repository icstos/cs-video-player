"""项目入口 —— 把 ``src`` 挂上 sys.path，再把控制权交给项目包。

这段引导是 **打包必需项**，不是开发兜底：隔离打包环境（serious_python /
PyInstaller 等）不会执行 ``pip install -e .``，包被编译进 ``<app>/src/`` 下，
而运行时 ``sys.path`` 只有 ``<app>/`` 根、不含 ``src``。删掉即打包后
``ModuleNotFoundError``。

开发态同样走这段（重复插入会被守卫挡掉），所以本地跑到的就是打包跑到的路径。
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path and (_SRC / "cs_video_player").exists():
    sys.path.insert(0, str(_SRC))

from cs_video_player.bootstrap import run  # noqa: E402

if __name__ == "__main__":
    run()
