"""infra / preferences —— JSON 文件持久化适配器。

所有磁盘异常都在这里降级为日志 + 默认值，业务层不会因为用户目录不可写而崩溃。
数据目录通过构造参数注入，验证脚本可指向临时目录，不碰用户真实数据。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, TypeVar

from cs_video_player.infra.ports import PreferencesPort
from cs_video_player.models.config import (
    APP_DATA_DIR,
    MAX_RECENTS,
    PLAYBACK_STATE_FILE,
    RECENTS_FILE,
    SESSION_FILE,
    SETTINGS_FILE,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


class JsonPreferences(PreferencesPort):
    """基于 JSON 文件的设置 / 近期记录 / 会话存储。"""

    def __init__(self, root: Path | None = None) -> None:
        self._root: Path = root or APP_DATA_DIR
        self._recents_file: Path = self._root / RECENTS_FILE.name
        self._settings_file: Path = self._root / SETTINGS_FILE.name
        self._states_file: Path = self._root / PLAYBACK_STATE_FILE.name
        self._session_file: Path = self._root / SESSION_FILE.name

    def _ensure_dir(self) -> None:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("无法创建数据目录 %s: %s", self._root, exc)

    def _read(self, path: Path, default: Any) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("读取 JSON 失败 %s: %s", path, exc)
        return default

    def _write(self, path: Path, data: Any) -> bool:
        self._ensure_dir()
        try:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return True
        except OSError as exc:
            logger.warning("写入 JSON 失败 %s: %s", path, exc)
            return False

    def load_recents(self) -> tuple[str, ...]:
        data: Any = self._read(self._recents_file, [])
        if isinstance(data, list):
            return tuple(str(p) for p in data if isinstance(p, str))[:MAX_RECENTS]
        return ()

    def save_recents(self, paths: tuple[str, ...]) -> None:
        self._write(self._recents_file, list(paths[:MAX_RECENTS]))

    @staticmethod
    def add_recent(path: str, existing: tuple[str, ...]) -> tuple[str, ...]:
        """纯计算：路径置顶去重，返回新元组。"""
        return (path, *(item for item in existing if item != path))[:MAX_RECENTS]

    def get_setting(self, key: str, default: T) -> T:
        data: Any = self._read(self._settings_file, {})
        value: Any = data.get(key, default) if isinstance(data, dict) else default
        return value if isinstance(value, type(default)) or value is None else default

    def set_setting(self, key: str, value: object) -> None:
        data: Any = self._read(self._settings_file, {})
        settings: dict[str, Any] = dict(data) if isinstance(data, dict) else {}
        settings[key] = value
        self._write(self._settings_file, settings)

    def load_playback_states(self) -> dict[str, int]:
        data: Any = self._read(self._states_file, {})
        if isinstance(data, dict):
            return {
                str(k): int(v)
                for k, v in data.items()
                if isinstance(v, (int, float))
            }
        return {}

    def set_playback_state(self, path: str, position_ms: int) -> None:
        states: dict[str, int] = self.load_playback_states()
        states[path] = position_ms
        self._write(self._states_file, states)

    def load_session(self) -> dict[str, Any]:
        data: Any = self._read(self._session_file, {})
        return dict(data) if isinstance(data, dict) else {}

    def save_session(self, data: dict[str, Any]) -> None:
        self._write(self._session_file, data)

    def clear_session(self) -> None:
        self._write(self._session_file, {})
