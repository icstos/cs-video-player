"""CS Video Player —— 基于 cs-ui 的声明式本地视频播放器。

顶层包只承担三项「全局唯一」的职责：

- 声明版本号（打包与 `pip show` 读这里）；
- 收敛资源路径（:mod:`cs_video_player._paths`）；
- 暴露启动入口（:func:`cs_video_player.bootstrap.run`）。

真正的代码分住在四个子包里::

    components/  — 声明式 UI：kit（UI 词汇）/ media（视频后端与控制件）/ 视图
    configs/     — 应用常量 + 设计层（cs-ui 令牌的语义投影）
    core/        — 数据模型、播放引擎、播放控制器（纯逻辑，不碰界面）
    utils/       — 格式化、文件扫描、持久化、错误处理（纯函数优先）
"""

from __future__ import annotations

__version__ = "2.0.0"

__all__ = ["__version__"]
