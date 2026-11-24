"""view / formatters —— 控件值格式化与平台事件解析。

时间格式在本模块定义（而不是转手 cs-ui）：控制栏读数、拖动浮标、时长标签
必须走**同一个**函数，否则同一段视频会出现两套舍入规则。这里的实现是纯整数
运算，可以脱离界面单测；``fmt_rate`` 同理。
"""

from __future__ import annotations

import json
from typing import Any

import ui

__all__ = [
    "fmt_rate",
    "fmt_time",
    "human_size",
    "parse_idx",
    "parse_ms",
    "safe_float",
    "safe_int",
    "slider_position",
    "volume_after_wheel",
]


def fmt_time(ms: int | float | None) -> str:
    """毫秒 → ``MM:SS`` / ``HH:MM:SS``；空值与负数一律读作 ``00:00``。"""
    if ms is None or ms <= 0:
        return "00:00"
    hours, remainder = divmod(int(ms) // 1000, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def fmt_rate(rate: float) -> str:
    """倍速 → ``1x`` / ``1.5x``（去掉无意义的尾零）。"""
    return f"{rate:g}x"


def human_size(value: int | float | None) -> str:
    """字节数转可读字符串。"""
    if value is None or value < 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _duration_dict_to_ms(value: dict[str, Any]) -> int:
    return (
        int(value.get("days", 0)) * 86_400_000
        + int(value.get("hours", 0)) * 3_600_000
        + int(value.get("minutes", 0)) * 60_000
        + int(value.get("seconds", 0)) * 1_000
        + int(value.get("milliseconds", 0))
    )


def parse_ms(data: Any) -> int:
    """把 Flet Duration / 事件数据解析成毫秒。

    底层播放器在不同事件里会给出 ``Duration`` 对象、字典或 JSON 字符串，
    这里一次收敛成整数；无法解析时返回 0，绝不把脏数据抛给状态层。
    """
    if data is None:
        return 0
    if isinstance(data, ui.Duration):
        return int(data.in_milliseconds)
    if isinstance(data, dict):
        return _duration_dict_to_ms(data)
    if isinstance(data, (int, float)):
        return int(data)
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return _duration_dict_to_ms(parsed)
            return int(parsed)
        except (json.JSONDecodeError, TypeError, ValueError):
            return 0
    return 0


def parse_idx(data: Any) -> int:
    """解析轨道索引，兼容整数、数字字符串与 JSON 字符串。"""
    if isinstance(data, int):
        return data
    if isinstance(data, str):
        try:
            return int(data)
        except ValueError:
            try:
                return int(json.loads(data))
            except (json.JSONDecodeError, TypeError, ValueError):
                return 0
    return 0


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def volume_after_wheel(volume: float, delta_y: float, step: float) -> float:
    """滚轮调音量的纯计算：上滚加、下滚减，结果夹在 0~100。

    从事件回调里抽出来，是为了让「方向」和「边界」可以被单测，而不是只能靠
    手滚鼠标验证。``delta_y`` 为 0 时返回原值（调用方可据此跳过一次状态更新）。
    """
    if delta_y == 0:
        return volume
    return max(0.0, min(100.0, volume + (step if delta_y < 0 else -step)))


def slider_position(event: Any) -> int | None:
    """从滑块事件里取毫秒值：优先 ``event.data``，其次控件当前值。

    Flet 的新值先随事件到达，``control.value`` 的回写可能晚一帧，所以顺序不能反。
    """
    for candidate in (
        getattr(event, "data", None),
        getattr(getattr(event, "control", None), "value", None),
    ):
        if candidate is None:
            continue
        try:
            return int(float(candidate))
        except (TypeError, ValueError):
            continue
    return None
