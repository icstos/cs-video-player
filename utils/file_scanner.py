"""
文件扫描工具 — 递归或非递归扫描文件夹中的视频文件。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from configs.app_config import VIDEO_EXTENSIONS, MAX_PLAYLIST
from core.models import PlaylistItem

logger = logging.getLogger(__name__)


def _make_item(entry: Path) -> PlaylistItem | None:
    try:
        stat = entry.stat()
        return PlaylistItem(
            path=str(entry),
            title=entry.stem,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
        )
    except (OSError, PermissionError) as exc:
        logger.warning("无法读取文件信息 %s: %s", entry, exc)
        return None


def scan_videos(folder: str) -> List[PlaylistItem]:
    """扫描文件夹（非递归）中所有视频文件。"""
    folder_path = Path(folder).expanduser()
    if not folder_path.is_dir():
        logger.warning("路径不是目录: %s", folder)
        return []

    items: List[PlaylistItem] = []
    try:
        for entry in sorted(folder_path.iterdir(), key=lambda p: p.name.lower()):
            if (
                entry.is_file()
                and entry.suffix.lower() in VIDEO_EXTENSIONS
                and len(items) < MAX_PLAYLIST
            ):
                item = _make_item(entry)
                if item:
                    items.append(item)
    except (OSError, PermissionError) as exc:
        logger.error("扫描文件夹失败 %s: %s", folder, exc)
    return items


def scan_videos_recursive(folder: str, max_depth: int = 3) -> List[PlaylistItem]:
    """递归扫描文件夹中的视频文件。"""
    folder_path = Path(folder).expanduser()
    if not folder_path.is_dir():
        return []

    items: List[PlaylistItem] = []
    _scan_recursive(folder_path, items, 0, max_depth)
    items.sort(key=lambda x: x.title.lower())
    return items


def _scan_recursive(
    folder: Path,
    items: List[PlaylistItem],
    depth: int,
    max_depth: int,
) -> None:
    if depth > max_depth or len(items) >= MAX_PLAYLIST:
        return
    try:
        for entry in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if len(items) >= MAX_PLAYLIST:
                break
            if (
                entry.is_file()
                and entry.suffix.lower() in VIDEO_EXTENSIONS
            ):
                item = _make_item(entry)
                if item:
                    items.append(item)
            elif entry.is_dir():
                _scan_recursive(entry, items, depth + 1, max_depth)
    except (OSError, PermissionError) as exc:
        logger.warning("递归扫描失败 %s: %s", folder, exc)


def make_playlist_item(path: str) -> PlaylistItem:
    """从单个路径创建 PlaylistItem。"""
    p = Path(path).expanduser()
    item = _make_item(p)
    return item if item else PlaylistItem(path=path, title=p.stem, size=0)


def make_playlist_items(paths: List[str]) -> List[PlaylistItem]:
    """从多个路径批量创建 PlaylistItem，自动过滤无效文件并按文件名排序。"""
    seen: set[str] = set()
    items: List[PlaylistItem] = []
    for path_str in paths:
        p = Path(path_str).expanduser()
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
            item = _make_item(p)
            if item:
                items.append(item)
        elif p.is_dir():
            for sub in scan_videos(str(p)):
                skey = str(Path(sub.path).resolve())
                if skey not in seen:
                    seen.add(skey)
                    items.append(sub)
    items.sort(key=lambda x: x.title.lower())
    return items[:MAX_PLAYLIST]


def is_valid_video(path: str) -> bool:
    """检查路径是否为受支持的视频文件。"""
    p = Path(path)
    return p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS


def count_videos(folder: str) -> int:
    """统计文件夹中的视频数量（不递归）。"""
    folder_path = Path(folder).expanduser()
    if not folder_path.is_dir():
        return 0
    count = 0
    try:
        for entry in folder_path.iterdir():
            if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                count += 1
    except (OSError, PermissionError):
        pass
    return count
