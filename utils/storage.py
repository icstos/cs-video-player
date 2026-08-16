"""
持久化存储管理 — 近期播放记录、应用设置与播放进度。
所有操作均包含异常处理，保证不会因磁盘问题导致应用崩溃。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List

from configs.app_config import (
    APP_DATA_DIR,
    MAX_RECENTS,
    PLAYBACK_STATE_FILE,
    RECENTS_FILE,
    SETTINGS_FILE,
)

logger = logging.getLogger(__name__)


class StorageManager:
    """管理近期记录、应用设置与播放进度的读写。"""

    @staticmethod
    def ensure_data_dir() -> None:
        try:
            APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("无法创建数据目录: %s", exc)

    @staticmethod
    def _read_json(filepath: Path, default: Any) -> Any:
        try:
            if filepath.exists():
                return json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("读取 JSON 失败 %s: %s", filepath, exc)
        return default

    @staticmethod
    def _write_json(filepath: Path, data: Any) -> bool:
        StorageManager.ensure_data_dir()
        try:
            filepath.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except OSError as exc:
            logger.warning("写入 JSON 失败 %s: %s", filepath, exc)
            return False

    # ─── 近期播放记录 ───

    @staticmethod
    def load_recents() -> List[str]:
        data = StorageManager._read_json(RECENTS_FILE, [])
        if isinstance(data, list):
            return [str(p) for p in data if isinstance(p, str)][:MAX_RECENTS]
        return []

    @staticmethod
    def save_recents(paths: List[str]) -> None:
        StorageManager._write_json(RECENTS_FILE, paths[:MAX_RECENTS])

    @staticmethod
    def add_recent(path: str, existing: List[str]) -> List[str]:
        """将路径添加到近期列表头部（去重），返回新列表。"""
        new_list = [path] + [r for r in existing if r != path]
        return new_list[:MAX_RECENTS]

    # ─── 应用设置 ───

    @staticmethod
    def load_settings() -> dict[str, Any]:
        data = StorageManager._read_json(SETTINGS_FILE, {})
        return data if isinstance(data, dict) else {}

    @staticmethod
    def save_settings(settings: dict[str, Any]) -> None:
        StorageManager._write_json(SETTINGS_FILE, settings)

    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        return StorageManager.load_settings().get(key, default)

    @staticmethod
    def set_setting(key: str, value: Any) -> None:
        settings = StorageManager.load_settings()
        settings[key] = value
        StorageManager.save_settings(settings)

    # ─── 播放进度记忆（按文件路径记录上次播放位置）───

    @staticmethod
    def load_playback_states() -> dict[str, int]:
        data = StorageManager._read_json(PLAYBACK_STATE_FILE, {})
        if isinstance(data, dict):
            return {str(k): int(v) for k, v in data.items() if isinstance(v, (int, float))}
        return {}

    @staticmethod
    def save_playback_states(states: dict[str, int]) -> None:
        StorageManager._write_json(PLAYBACK_STATE_FILE, states)

    @staticmethod
    def get_playback_state(path: str) -> int:
        return StorageManager.load_playback_states().get(path, 0)

    @staticmethod
    def set_playback_state(path: str, position_ms: int) -> None:
        states = StorageManager.load_playback_states()
        states[path] = position_ms
        StorageManager.save_playback_states(states)
