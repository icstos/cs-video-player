"""纯逻辑回归 —— ``python scripts/test_logic.py``，无需窗口。

覆盖三类可复算的东西：格式化与事件解析、业务规则与服务状态机、设计层色表。
UI 构建期的问题由 ``verify_app.py`` 负责；分层约束由 ``check_architecture.py``
负责。三条命令合起来回答「逻辑对不对 / 界面能否构建 / 架构有没有退化」。
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import ui  # noqa: E402

from cs_video_player.infra import FileSystemScanner, JsonPreferences, MediaController  # noqa: E402
from cs_video_player.models import (  # noqa: E402
    PlayMode,
    PlaybackState,
    PlaylistItem,
    SortKey,
)
from cs_video_player.service import PlaybackService  # noqa: E402
from cs_video_player.service import rules  # noqa: E402
from cs_video_player.view.formatters import (  # noqa: E402
    fmt_rate,
    fmt_time,
    human_size,
    parse_idx,
    parse_ms,
    slider_position,
    volume_after_wheel,
)
from cs_video_player.view.native_video import fullscreen_controls  # noqa: E402
from cs_video_player.view.theme import (  # noqa: E402
    BRAND_PRIMARY,
    THEME_MODE,
    MediaPalette,
    palette_snapshot,
)


def _items(n: int = 3) -> tuple[PlaylistItem, ...]:
    return tuple(
        PlaylistItem(
            path=f"D:/media/v{i}.mp4",
            title=f"视频 {i}",
            size=1024 * (i + 1),
            modified=datetime(2026, 1, i + 1),
        )
        for i in range(n)
    )


def _service() -> PlaybackService:
    """测试用服务：临时目录 + 未绑定播放器，所有 I/O 都落在临时区。"""
    return PlaybackService(
        media=MediaController(),
        preferences=JsonPreferences(root=Path(tempfile.mkdtemp(prefix="cvp-test-"))),
        scanner=FileSystemScanner(),
    )


class FormattingTest(unittest.TestCase):
    def test_time(self):
        self.assertEqual(fmt_time(None), "00:00")
        self.assertEqual(fmt_time(-10), "00:00")
        self.assertEqual(fmt_time(0), "00:00")
        self.assertEqual(fmt_time(61_000), "01:01")
        self.assertEqual(fmt_time(3_661_000), "01:01:01")
        self.assertEqual(fmt_time(59 * 60_000 + 59_000), "59:59")

    def test_rate(self):
        self.assertEqual(fmt_rate(1.0), "1x")
        self.assertEqual(fmt_rate(1.5), "1.5x")
        self.assertEqual(fmt_rate(0.25), "0.25x")

    def test_size_and_uri(self):
        self.assertEqual(human_size(None), "0 B")
        self.assertEqual(human_size(512), "512 B")
        self.assertEqual(human_size(2048), "2.0 KB")
        self.assertTrue(FileSystemScanner().to_uri("D:/media/a.mp4").startswith("file:///"))

    def test_parse_ms(self):
        self.assertEqual(parse_ms(None), 0)
        self.assertEqual(parse_ms(ui.Duration(milliseconds=1500)), 1500)
        self.assertEqual(parse_ms({"minutes": 1, "seconds": 2, "milliseconds": 3}), 62_003)
        self.assertEqual(parse_ms('{"seconds": 4}'), 4000)
        self.assertEqual(parse_ms("1234"), 1234)
        self.assertEqual(parse_ms("oops"), 0)

    def test_parse_idx(self):
        self.assertEqual(parse_idx(3), 3)
        self.assertEqual(parse_idx("7"), 7)
        self.assertEqual(parse_idx('"9"'), 9)
        self.assertEqual(parse_idx("bad"), 0)

    def test_volume_wheel(self):
        self.assertEqual(volume_after_wheel(50, -1, 5), 55)
        self.assertEqual(volume_after_wheel(50, 1, 5), 45)
        self.assertEqual(volume_after_wheel(50, 0, 5), 50)
        self.assertEqual(volume_after_wheel(99, -1, 5), 100)
        self.assertEqual(volume_after_wheel(2, 1, 5), 0)

    def test_slider_position(self):
        class E:
            data = "1234.9"
            control = None
        self.assertEqual(slider_position(E()), 1234)
        class E2:
            data = None
            class control:
                value = 99.0
        self.assertEqual(slider_position(E2()), 99)

    def test_error_classification(self):
        self.assertIn("编码", rules.classify_error("Unsupported codec h266"))
        self.assertIn("不存在", rules.classify_error(FileNotFoundError("no such file")))
        self.assertIn("播放出错", rules.classify_error("something odd"))


class RulesTest(unittest.TestCase):
    def test_playlist_mapping(self):
        items = _items()
        to_uri = FileSystemScanner().to_uri
        self.assertEqual(len(rules.project_playlist(items, PlayMode.SEQUENCE, 1, to_uri)), 3)
        single = rules.project_playlist(items, PlayMode.REPEAT_ONE, 1, to_uri)
        self.assertEqual(len(single), 1)
        self.assertIn("v1.mp4", single[0].uri.lower())
        self.assertEqual(rules.project_playlist((), PlayMode.SEQUENCE, 0, to_uri), ())

    def test_playlist_mode(self):
        self.assertEqual(rules.list_mode_for(PlayMode.REPEAT_ONE).value, "single")
        self.assertEqual(rules.list_mode_for(PlayMode.REPEAT_ALL).value, "loop")
        self.assertEqual(rules.list_mode_for(PlayMode.SEQUENCE).value, "none")

    def test_fullscreen_controls_share_palette(self):
        controls = fullscreen_controls()
        palette = palette_snapshot()
        self.assertEqual(controls.seek_bar_position_color, palette["primary"])
        self.assertEqual(controls.button_bar_button_color, palette["text"])
        self.assertFalse(controls.play_and_pause_on_tap)
        self.assertTrue(controls.toggle_fullscreen_on_double_press)

    def test_speed_step(self):
        self.assertEqual(rules.step_speed(1.0, +1), 1.25)
        self.assertEqual(rules.step_speed(1.0, -1), 0.75)
        self.assertEqual(rules.step_speed(16.0, +1), 16.0)


class ServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = _service()
        self.service.add_files(_items(), replace=True)

    def test_navigation(self):
        c = self.service
        c.play_at(1)
        self.assertEqual(c.state.current_index, 1)
        c.play_next()
        self.assertEqual(c.state.current_index, 2)
        c.play_prev()
        self.assertEqual(c.state.current_index, 1)
        c.play_at(2)
        c.play_next()  # 顺序模式到末尾不回卷
        self.assertEqual(c.state.current_index, 2)

    def test_repeat_all_wraps(self):
        c = self.service
        c.set_play_mode(PlayMode.REPEAT_ALL)
        c.play_at(2)
        c.play_next()
        self.assertEqual(c.state.current_index, 0)

    def test_volume_and_mute(self):
        c = self.service
        c.set_volume(150)
        self.assertEqual(c.state.volume, 100)
        c.set_volume(-5)
        self.assertEqual(c.state.volume, 0)
        c.set_volume(60)
        c.toggle_mute()
        self.assertTrue(c.state.muted)
        c.set_volume(70)  # 调音量自动解除静音
        self.assertFalse(c.state.muted)

    def test_cycle_mode_is_stable(self):
        c = self.service
        modes = [c.state.play_mode]
        for _ in range(4):
            c.cycle_play_mode()
            modes.append(c.state.play_mode)
        self.assertEqual(modes[0], modes[-1])
        self.assertEqual(len(set(modes[:-1])), 4)

    def test_sorted_playlist_keeps_original_index(self):
        c = self.service
        c.add_files(
            (
                PlaylistItem(path="b", title="b", size=1),
                PlaylistItem(path="a", title="a", size=9),
            ),
            replace=True,
        )
        c.set_sort_key(SortKey.NAME)
        self.assertEqual([idx for idx, _ in c.sorted_playlist()], [1, 0])
        c.set_sort_key(SortKey.SIZE)
        self.assertEqual([idx for idx, _ in c.sorted_playlist()], [1, 0])

    def test_remove_keeps_current_index_valid(self):
        c = self.service
        c.play_at(2)
        c.remove_from_playlist(2)
        self.assertEqual(c.state.current_index, 1)
        c.remove_from_playlist(0)
        self.assertEqual(c.state.current_index, 0)

    def test_reorder_tracks_current(self):
        c = self.service
        c.play_at(0)
        c.reorder(0, 2)
        self.assertEqual(c.state.current_index, 2)

    def test_native_projection_follows_mode(self):
        c = self.service
        self.assertEqual(len(c.state.native_playlist), 3)
        c.play_at(1)
        c.set_play_mode(PlayMode.REPEAT_ONE)
        self.assertEqual(len(c.state.native_playlist), 1)
        self.assertIn("v1.mp4", c.state.native_playlist[0].uri)


class DesignTest(unittest.TestCase):
    def test_palette_is_recomputable(self):
        first = MediaPalette.derive(BRAND_PRIMARY, mode=THEME_MODE)
        second = MediaPalette.derive(BRAND_PRIMARY, mode=THEME_MODE)
        self.assertEqual(first, second)
        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertNotEqual(
            first.as_dict()["surface"],
            MediaPalette.derive(BRAND_PRIMARY, mode="light").as_dict()["surface"],
        )

    def test_snapshot_is_complete(self):
        snap = palette_snapshot()
        self.assertEqual(snap["brand"], BRAND_PRIMARY)
        self.assertEqual(snap["mode"], THEME_MODE)
        for key in ("primary", "panel", "surface", "darkest", "text", "muted", "danger"):
            self.assertTrue(snap[key].startswith("#"), key)

    def test_player_state_flags(self):
        s = PlaybackState(playlist=_items(), current_index=1)
        self.assertTrue(s.has_video)
        self.assertTrue(s.has_prev)
        self.assertTrue(s.has_next)
        self.assertEqual(s.current_item.title, "视频 1")  # type: ignore[union-attr]
        s = PlaybackState(playlist=_items(), duration_ms=1000, position_ms=250)
        self.assertAlmostEqual(s.progress, 0.25)


if __name__ == "__main__":
    unittest.main(verbosity=2)
