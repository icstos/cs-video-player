"""service / rules —— 纯业务规则（无 I/O、无状态、可单测）。

规则与编排分开：这里只回答「怎么算」，``playback.PlaybackService`` 负责
「什么时候算、算完调哪个端口」。凡是涉及时间、音量、索引、排序、错误分类的
判断都收在这里，保证同一规则在按钮、菜单、快捷键三条入口得到同一结果。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from cs_video_player.models.config import (
    PLAYBACK_SPEEDS,
    SPEED_MAX,
    SPEED_MIN,
)
from cs_video_player.models.entities import MediaTrack, PlaylistItem
from cs_video_player.models.enums import ListMode, PlayMode, SortKey

# 错误分类与友好提示（顺序即优先级）
_ERROR_PATTERNS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("codec", "decoder", "demuxer", "no video", "unsupported codec"),
        "视频编码格式不受支持，无法解码播放",
    ),
    (
        ("format", "container", "mime", "invalid format", "not a valid"),
        "视频文件格式不受支持或已损坏",
    ),
    (
        ("corrupt", "damaged", "truncated", "broken", "incomplete"),
        "视频文件可能已损坏或不完整",
    ),
    (
        ("subtitle", "sub", "caption", "track"),
        "字幕加载失败，已忽略字幕轨道",
    ),
    (
        ("permission", "access denied", "forbidden", "locked"),
        "没有访问该文件的权限",
    ),
    (
        ("not found", "no such file", "does not exist", "missing"),
        "文件不存在或已被移动",
    ),
    (
        ("network", "connection", "timeout", "unreachable"),
        "网络连接异常，无法加载资源",
    ),
    (
        ("out of memory", "oom", "allocation"),
        "内存不足，请关闭其他程序后重试",
    ),
    (
        ("hardware", "gpu", "acceleration", "dxva", "vaapi", "vdpau"),
        "硬件加速初始化失败，已切换为软件解码",
    ),
    (
        ("eof", "end of file", "premature"),
        "视频数据不完整，可能已损坏",
    ),
)


def classify_error(exc: BaseException | str) -> str:
    """把底层异常翻译成一句人话（未知错误保留原文）。"""
    msg: str = str(exc).lower()
    for keywords, friendly in _ERROR_PATTERNS:
        if any(keyword in msg for keyword in keywords):
            return friendly
    return f"播放出错：{exc}" if exc else "发生未知错误"


def sorted_items(
    items: tuple[PlaylistItem, ...], key: SortKey
) -> tuple[tuple[int, PlaylistItem], ...]:
    """返回 ``(原始索引, 项)`` 的展示序列；排序不改变底层索引。"""
    entries: list[tuple[int, PlaylistItem]] = list(enumerate(items))
    if key == SortKey.NAME:
        entries.sort(key=lambda pair: pair[1].title.lower())
    elif key == SortKey.SIZE:
        entries.sort(key=lambda pair: pair[1].size, reverse=True)
    elif key == SortKey.DATE:
        entries.sort(
            key=lambda pair: pair[1].modified or datetime.min, reverse=True
        )
    return tuple(entries)


def list_mode_for(mode: PlayMode) -> ListMode:
    """业务播放模式 → 原生播放列表模式（单曲循环只投喂当前项）。"""
    if mode == PlayMode.REPEAT_ONE:
        return ListMode.SINGLE
    if mode == PlayMode.REPEAT_ALL:
        return ListMode.LOOP
    return ListMode.NONE


def project_playlist(
    items: tuple[PlaylistItem, ...],
    mode: PlayMode,
    current_index: int,
    to_uri: Callable[[str], str],
) -> tuple[MediaTrack, ...]:
    """把业务播放列表投影成 URI 轨道序列；只依赖注入的 URI 转换函数。"""
    if not items:
        return ()
    if mode == PlayMode.REPEAT_ONE:
        if 0 <= current_index < len(items):
            return (MediaTrack(uri=to_uri(items[current_index].path)),)
        return ()
    return tuple(MediaTrack(uri=to_uri(item.path)) for item in items)


def step_speed(current: float, direction: int) -> float:
    """倍速档位步进：在档位表里找严格大于 / 小于当前值的下一档。"""
    candidates: Sequence[float] = (
        PLAYBACK_SPEEDS if direction > 0 else tuple(reversed(PLAYBACK_SPEEDS))
    )
    for value in candidates:
        changed: bool = (
            value > current + 1e-9 if direction > 0 else value < current - 1e-9
        )
        if changed:
            return min(value, SPEED_MAX) if direction > 0 else max(value, SPEED_MIN)
    return SPEED_MAX if direction > 0 else SPEED_MIN


def clamp_volume(volume: float) -> float:
    """音量夹到 0~100。"""
    return max(0.0, min(100.0, volume))


def volume_after_wheel(volume: float, delta_y: float, step: float) -> float:
    """滚轮调音量：上滚加、下滚减；delta 为 0 时原值返回。"""
    if delta_y == 0:
        return volume
    return clamp_volume(volume + (step if delta_y < 0 else -step))


def index_after_remove(current: int, removed: int, size_before: int) -> int:
    """删除一项后当前索引应落到哪里（size_before 是删除前的列表长度）。"""
    if not 0 <= removed < size_before:
        return current
    if removed < current:
        return current - 1
    if removed == current:
        return min(current, size_before - 2) if size_before > 1 else 0
    return current


def index_after_move(current: int, src: int, dst: int) -> int:
    """移动一项后当前索引的新位置。"""
    if current == src:
        return dst
    if src < current <= dst:
        return current - 1
    if dst <= current < src:
        return current + 1
    return current


def is_valid_index(index: int, size: int) -> bool:
    """索引是否落在列表内。"""
    return 0 <= index < size
