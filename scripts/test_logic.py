"""纯逻辑回归 —— 不需要窗口，``python scripts/test_logic.py`` 直接跑。

覆盖三类「可复算」的东西：格式化与解析、播放引擎/控制器的状态推导、
设计层色表的确定性。UI 构建期的问题由 ``verify_app.py`` 负责。
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

# src 布局：项目包在 src/ 下，脚本在仓库根的 scripts/ 下。
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import ui  # noqa: E402

from cs_video_player.configs.theme import (  # noqa: E402
    BRAND_PRIMARY,
    THEME_MODE,
    MediaPalette,
    palette_snapshot,
)
from cs_video_player.core.models import PlayMode, PlaylistItem, PlayerState, SortKey  # noqa: E402
from cs_video_player.core.player_controller import PlayerController  # noqa: E402
from cs_video_player.core.video_engine import VideoEngine  # noqa: E402
from cs_video_player.utils.error_handler import classify_error  # noqa: E402
from cs_video_player.utils.formatters import (  # noqa: E402
    fmt_rate,
    fmt_time,
    human_size,
    parse_idx,
    parse_ms,
    slider_position,
    to_uri,
    volume_after_wheel,
)


def _items(n: int = 3) -> list[PlaylistItem]:
    return [
        PlaylistItem(
            path=f"D:/media/v{i}.mp4",
            title=f"视频 {i}",
            size=1024 * (i + 1),
            modified=datetime(2026, 1, i + 1),
        )
        for i in range(n)
    ]


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
        self.assertTrue(to_uri("D:/media/a.mp4").startswith("file:///"))

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
        self.assertIn("编码", classify_error("Unsupported codec h266"))
        self.assertIn("不存在", classify_error(FileNotFoundError("no such file")))
        self.assertIn("播放出错", classify_error("something odd"))


class EngineTest(unittest.TestCase):
    def test_playlist_mapping(self):
        items = _items()
        self.assertEqual(len(VideoEngine.build_playlist(items, PlayMode.SEQUENCE, 1)), 3)
        single = VideoEngine.build_playlist(items, PlayMode.REPEAT_ONE, 1)
        self.assertEqual(len(single), 1)
        self.assertIn("v1.mp4", single[0].resource.lower())
        self.assertEqual(VideoEngine.build_playlist([], PlayMode.SEQUENCE, 0), [])

    def test_playlist_mode(self):
        self.assertEqual(
            VideoEngine.get_playlist_mode(PlayMode.REPEAT_ONE).value, "single"
        )
        self.assertEqual(
            VideoEngine.get_playlist_mode(PlayMode.REPEAT_ALL).value, "loop"
        )
        self.assertEqual(
            VideoEngine.get_playlist_mode(PlayMode.SEQUENCE).value, "none"
        )

    def test_fullscreen_controls_share_palette(self):
        controls = VideoEngine.build_fullscreen_controls()
        palette = palette_snapshot()
        self.assertEqual(controls.seek_bar_position_color, palette["primary"])
        self.assertEqual(controls.button_bar_button_color, palette["text"])
        self.assertFalse(controls.play_and_pause_on_tap)
        self.assertTrue(controls.toggle_fullscreen_on_double_press)


class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.controller = PlayerController()
        self.controller.set_playlist(_items())

    def test_navigation(self):
        c = self.controller
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
        c = self.controller
        c.set_play_mode(PlayMode.REPEAT_ALL)
        c.play_at(2)
        c.play_next()
        self.assertEqual(c.state.current_index, 0)

    def test_volume_and_mute(self):
        c = self.controller
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
        c = self.controller
        modes = [c.state.play_mode]
        for _ in range(4):
            c.cycle_play_mode()
            modes.append(c.state.play_mode)
        self.assertEqual(modes[0], modes[-1])
        self.assertEqual(len(set(modes[:-1])), 4)

    def test_sorted_playlist_keeps_original_index(self):
        c = self.controller
        c.state.playlist = [
            PlaylistItem(path="b", title="b", size=1),
            PlaylistItem(path="a", title="a", size=9),
        ]
        c.set_sort_key(SortKey.NAME)
        self.assertEqual([idx for idx, _ in c.get_sorted_playlist()], [1, 0])
        c.set_sort_key(SortKey.SIZE)
        self.assertEqual([idx for idx, _ in c.get_sorted_playlist()], [1, 0])

    def test_remove_keeps_current_index_valid(self):
        c = self.controller
        c.play_at(2)
        c.remove_from_playlist(2)
        self.assertEqual(c.state.current_index, 1)
        c.remove_from_playlist(0)
        self.assertEqual(c.state.current_index, 0)

    def test_reorder_tracks_current(self):
        c = self.controller
        c.play_at(0)
        c.reorder(0, 2)
        self.assertEqual(c.state.current_index, 2)


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
        s = PlayerState(playlist=_items(), current_index=1)
        self.assertTrue(s.has_video)
        self.assertTrue(s.has_prev)
        self.assertTrue(s.has_next)
        self.assertEqual(s.current_item.title, "视频 1")
        s.duration_ms = 1000
        s.position_ms = 250
        self.assertAlmostEqual(s.progress, 0.25)


if __name__ == "__main__":
    unittest.main(verbosity=2)
