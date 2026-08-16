"""
时间、大小与事件数据格式化工具。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import flet as ft


def fmt_time(ms: int | float | None) -> str:
    """毫秒转 MM:SS 或 HH:MM:SS。"""
    if ms is None or ms <= 0:
        return "00:00"
    total_s = int(ms) // 1000
    hours, remainder = divmod(total_s, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


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


def to_uri(path: str) -> str:
    """将本地路径转换成 file URI。"""
    return Path(path).expanduser().resolve().as_uri()


def _duration_dict_to_ms(value: dict[str, Any]) -> int:
    return (
        int(value.get("days", 0)) * 86_400_000
        + int(value.get("hours", 0)) * 3_600_000
        + int(value.get("minutes", 0)) * 60_000
        + int(value.get("seconds", 0)) * 1_000
        + int(value.get("milliseconds", 0))
    )


def parse_ms(data: Any) -> int:
    """将 Flet Duration 或事件数据解析为毫秒。"""
    if data is None:
        return 0
    if isinstance(data, ft.Duration):
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
    """解析索引数据。"""
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
