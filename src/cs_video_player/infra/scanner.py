"""infra / scanner —— 文件系统扫描适配器。

把磁盘路径转换为 :class:`PlaylistItem` / file URI；文件系统异常一律降级为
日志与空结果。排序、去重上限等**业务规则**不在这里，由 Service 的规则函数
统一决定（见 ``service.rules``）。
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from cs_video_player.infra.ports import ScannerPort
from cs_video_player.models.config import MAX_PLAYLIST, VIDEO_EXTENSIONS
from cs_video_player.models.entities import PlaylistItem

logger = logging.getLogger(__name__)


class FileSystemScanner(ScannerPort):
    """本地文件系统的只读扫描器。"""

    def _make_item(self, entry: Path) -> PlaylistItem | None:
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
        except Exception as exc:
            logger.error("创建播放列表项失败 %s: %s", entry, exc)
            return None

    def scan_videos(self, folder: str) -> tuple[PlaylistItem, ...]:
        """扫描文件夹（非递归），按文件名排序。"""
        try:
            folder_path = Path(folder).expanduser()
            if not folder_path.is_dir():
                logger.warning("路径不是目录: %s", folder)
                return ()
        except Exception as exc:
            logger.error("路径解析失败 %s: %s", folder, exc)
            return ()

        items: list[PlaylistItem] = []
        try:
            for entry in sorted(folder_path.iterdir(), key=lambda p: p.name.lower()):
                if (
                    entry.is_file()
                    and entry.suffix.lower() in VIDEO_EXTENSIONS
                    and len(items) < MAX_PLAYLIST
                ):
                    item = self._make_item(entry)
                    if item is not None:
                        items.append(item)
        except (OSError, PermissionError) as exc:
            logger.error("扫描文件夹失败 %s: %s", folder, exc)
        except Exception as exc:
            logger.error("扫描文件夹时发生意外错误 %s: %s", folder, exc)
        return tuple(items)

    def scan_videos_recursive(
        self, folder: str, max_depth: int = 3
    ) -> tuple[PlaylistItem, ...]:
        """递归扫描文件夹（保留原有深度上限能力）。"""
        folder_path = Path(folder).expanduser()
        if not folder_path.is_dir():
            return ()
        items: list[PlaylistItem] = []
        self._scan_recursive(folder_path, items, 0, max_depth)
        items.sort(key=lambda x: x.title.lower())
        return tuple(items)

    def _scan_recursive(
        self,
        folder: Path,
        items: list[PlaylistItem],
        depth: int,
        max_depth: int,
    ) -> None:
        if depth > max_depth or len(items) >= MAX_PLAYLIST:
            return
        try:
            for entry in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
                if len(items) >= MAX_PLAYLIST:
                    break
                if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                    item = self._make_item(entry)
                    if item is not None:
                        items.append(item)
                elif entry.is_dir():
                    self._scan_recursive(entry, items, depth + 1, max_depth)
        except (OSError, PermissionError) as exc:
            logger.warning("递归扫描失败 %s: %s", folder, exc)

    def make_playlist_item(self, path: str) -> PlaylistItem:
        """单路径转换；无效路径返回占位项而非抛异常。"""
        try:
            p = Path(path).expanduser()
            item = self._make_item(p)
            return item if item is not None else PlaylistItem(path=path, title=p.stem, size=0)
        except Exception as exc:
            logger.error("创建播放列表项失败 %s: %s", path, exc)
            return PlaylistItem(path=path, title=Path(path).stem, size=0)

    def make_playlist_items(self, paths: tuple[str, ...]) -> tuple[PlaylistItem, ...]:
        """批量转换：去重、过滤、排序与上限都由这里的文件侧规则处理。"""
        seen: set[str] = set()
        items: list[PlaylistItem] = []
        for path_str in paths:
            try:
                p = Path(path_str).expanduser()
                key = str(p.resolve())
                if key in seen:
                    continue
                seen.add(key)
                if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
                    item = self._make_item(p)
                    if item is not None:
                        items.append(item)
                elif p.is_dir():
                    for sub in self.scan_videos(str(p)):
                        skey = str(Path(sub.path).resolve())
                        if skey not in seen:
                            seen.add(skey)
                            items.append(sub)
            except (OSError, PermissionError) as exc:
                logger.warning("处理路径失败 %s: %s", path_str, exc)
            except Exception as exc:
                logger.error("处理路径时发生意外错误 %s: %s", path_str, exc)
        items.sort(key=lambda x: x.title.lower())
        return tuple(items[:MAX_PLAYLIST])

    def is_valid_video(self, path: str) -> bool:
        """路径是否指向受支持的视频文件。"""
        p = Path(path)
        return p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS

    def count_videos(self, folder: str) -> int:
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

    def to_uri(self, path: str) -> str:
        """本地路径 → file URI（原生播放列表要求）。"""
        return Path(path).expanduser().resolve().as_uri()
