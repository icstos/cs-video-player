"""资源与目录路径的唯一出口。

src 布局下「向上数几层找目录」非常容易算错，而且算错时不报错 —— 只会静默地
拿到一个不存在的路径。所以本项目里**任何**需要项目目录的地方都从这里取，
不要在别处再写 ``Path(__file__).parents[n]``。

覆盖三种运行形态：

- 开发态 ``python main.py``（仓库根）
- ``pip install -e .`` 后从任意目录导入
- 隔离打包（serious_python / PyInstaller）后包被拷进 ``<app>/src/cs_video_player/``

三者对本文件的相对位置一致，因此向上查找真实存在的目录即可，无需分支判断。
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["assets_dir", "project_root"]

_ASSETS_NAME = "assets"


def project_root() -> Path:
    """仓库根目录（``src`` 的上一级）。

    用法仅限「需要落地到仓库内的文件」，例如验证脚本导出的截图。
    """
    return Path(__file__).resolve().parents[2]


def assets_dir() -> Path:
    """资源目录；不存在时返回「按布局推算的位置」，由调用方决定如何降级。

    向上查找而不是死算层数：打包工具会把包整体搬走，层数可能变，但
    ``assets`` 与入口的相对关系不会变。
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / _ASSETS_NAME
        if candidate.is_dir():
            return candidate
    # src/<project>/_paths.py 的上三级即仓库根；摊平结构通常已在上面的循环命中。
    return here.parents[2] / _ASSETS_NAME
