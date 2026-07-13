"""声明式本地视频播放器 — flet 0.85.3 + flet-video"""
import json
from pathlib import Path

import flet as ft
from flet_video import (
    Video,
    VideoMedia,
    PlaylistMode,
    VideoControlsMode,
    MaterialDesktopVideoControls,
)

# ═══════════════════════════════════════════════════════════
#  配色系统 — 专业蓝色 · 高级科技风（暗色主题）
# ═══════════════════════════════════════════════════════════
C_PRIMARY = "#2F80ED"   # 主色
C_HOVER = "#4A90F5"     # 悬停色
C_BG_DARK = "#0E131B"   # 最深背景
C_BG_PANEL = "#161E2E"  # 面板背景
C_BG_ITEM = "#1E283A"   # 列表项背景
C_BG_ACTIVE = "#1C3A5E" # 选中项背景
C_BG_HOVER = "#1B2436"  # 悬停背景
C_BORDER = "#2A3548"    # 描边色
C_TEXT = "#E8EDF5"      # 主文字
C_TEXT_SUB = "#8B95A8"  # 次文字
C_RED = "#FF5252"       # 危险色

VIDEO_EXTS = {
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
    ".webm", ".m4v", ".mpg", ".mpeg", ".ts", ".3gp", ".m2ts",
}
RECENTS_FILE = Path.home() / ".cs_video_player_recent.json"
SPEEDS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
SORT_LABELS = {"default": "默认", "name": "名称", "size": "大小"}


# ═══════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════
def fmt_time(ms: int) -> str:
    """毫秒 → MM:SS 或 HH:MM:SS"""
    if ms <= 0:
        return "00:00"
    s = ms // 1000
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def to_uri(p: str) -> str:
    return Path(p).resolve().as_uri()


def _duration_dict_to_ms(d: dict) -> int:
    """将 Duration dict 各字段累加为总毫秒数"""
    return (
        d.get("days", 0) * 86_400_000
        + d.get("hours", 0) * 3_600_000
        + d.get("minutes", 0) * 60_000
        + d.get("seconds", 0) * 1_000
        + d.get("milliseconds", 0)
    )


def parse_ms(data) -> int:
    """解析事件数据为总毫秒数（支持 Duration 对象 / dict / int / JSON str）"""
    if data is None:
        return 0
    if isinstance(data, ft.Duration):
        return data.in_milliseconds
    if isinstance(data, dict):
        return _duration_dict_to_ms(data)
    if isinstance(data, (int, float)):
        return int(data)
    if isinstance(data, str):
        try:
            obj = json.loads(data)
            return _duration_dict_to_ms(obj) if isinstance(obj, dict) else int(obj)
        except (json.JSONDecodeError, ValueError, TypeError):
            return 0
    return 0


def parse_idx(data) -> int:
    if isinstance(data, int):
        return data
    if isinstance(data, str):
        try:
            return int(data)
        except ValueError:
            try:
                return int(json.loads(data))
            except (json.JSONDecodeError, ValueError, TypeError):
                return 0
    return 0


def human_size(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {u}" if u != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def load_recents() -> list[str]:
    try:
        return json.loads(RECENTS_FILE.read_text("utf-8"))
    except Exception:
        return []


def save_recents(paths: list[str]):
    try:
        RECENTS_FILE.write_text(json.dumps(paths, ensure_ascii=False), "utf-8")
    except Exception:
        pass


def scan_videos(folder: str) -> list[dict]:
    items: list[dict] = []
    try:
        for f in Path(folder).iterdir():
            if f.is_file() and f.suffix.lower() in VIDEO_EXTS:
                items.append({"path": str(f), "title": f.stem, "size": f.stat().st_size})
    except Exception:
        pass
    items.sort(key=lambda x: x["title"].lower())
    return items


def _fullscreen_controls() -> MaterialDesktopVideoControls:
    """全屏模式内置控件 — 蓝色主题"""
    return MaterialDesktopVideoControls(
        seek_bar_position_color=C_PRIMARY,
        seek_bar_thumb_color=C_PRIMARY,
        seek_bar_color=C_BORDER,
        seek_bar_hover_color=C_HOVER,
        volume_bar_active_color=C_PRIMARY,
        volume_bar_thumb_color=C_PRIMARY,
        volume_bar_color=C_BORDER,
        button_bar_button_color=C_TEXT,
    )


# ═══════════════════════════════════════════════════════════
#  根组件
# ═══════════════════════════════════════════════════════════
@ft.component
def App():
    playlist, set_playlist = ft.use_state([])
    current_index, set_current_index = ft.use_state(0)
    recents, set_recents = ft.use_state(load_recents)
    sort_key, set_sort_key = ft.use_state("default")
    play_nonce, set_play_nonce = ft.use_state(0)

    # FilePicker 作为 Service 在首次渲染时自动注册
    picker_ref = ft.use_ref(lambda: ft.FilePicker())

    # ── 播放控制 ──
    def _add_recents(path: str):
        new = [path] + [r for r in recents if r != path][:9]
        set_recents(new)
        save_recents(new)

    def play_at(idx: int):
        if not playlist or idx < 0 or idx >= len(playlist):
            return
        set_current_index(idx)
        set_play_nonce(play_nonce + 1)
        _add_recents(playlist[idx]["path"])

    def play_next():
        if current_index < len(playlist) - 1:
            play_at(current_index + 1)

    def play_prev():
        if current_index > 0:
            play_at(current_index - 1)

    # ── 菜单动作 ──
    async def open_file():
        picker = picker_ref.current
        if not picker:
            return
        files = await picker.pick_files(
            dialog_title="选择视频文件",
            file_type=ft.FilePickerFileType.VIDEO,
        )
        if not files:
            return
        f = files[0]
        path = f.path or f.name
        set_playlist([{"path": path, "title": Path(path).stem, "size": f.size or 0}])
        set_current_index(0)
        set_play_nonce(play_nonce + 1)
        _add_recents(path)

    async def open_folder():
        picker = picker_ref.current
        if not picker:
            return
        folder = await picker.get_directory_path(dialog_title="选择视频文件夹")
        if not folder:
            return
        items = scan_videos(folder)
        if not items:
            return
        set_playlist(items)
        set_current_index(0)
        set_play_nonce(play_nonce + 1)
        _add_recents(items[0]["path"])

    def open_recent(path: str):
        size = 0
        try:
            size = Path(path).stat().st_size
        except Exception:
            pass
        set_playlist([{"path": path, "title": Path(path).stem, "size": size}])
        set_current_index(0)
        set_play_nonce(play_nonce + 1)
        _add_recents(path)

    # ── 播放列表操作 ──
    def remove_item(idx: int):
        new_list = list(playlist)
        new_list.pop(idx)
        set_playlist(new_list)
        if idx < current_index:
            set_current_index(current_index - 1)
        elif idx == current_index and new_list:
            ni = min(current_index, len(new_list) - 1)
            set_current_index(ni)
            set_play_nonce(play_nonce + 1)
        elif not new_list:
            set_current_index(0)

    # ── Video 事件回调 ──
    def on_track_change(e):
        idx = parse_idx(e.data)
        if 0 <= idx < len(playlist):
            set_current_index(idx)

    def on_complete(e):
        play_next()

    # ── 排序后的显示列表（保留原始索引） ──
    if sort_key == "name":
        display = sorted(enumerate(playlist), key=lambda x: x[1]["title"].lower())
    elif sort_key == "size":
        display = sorted(enumerate(playlist), key=lambda x: x[1]["size"], reverse=True)
    else:
        display = list(enumerate(playlist))

    return ft.Row(
        controls=[
            Sidebar(
                display=display,
                current_index=current_index,
                sort_key=sort_key,
                recents=recents,
                on_play=play_at,
                on_remove=remove_item,
                on_sort=set_sort_key,
                on_open_file=open_file,
                on_open_folder=open_folder,
                on_open_recent=open_recent,
            ),
            PlayerArea(
                playlist=playlist,
                current_index=current_index,
                play_nonce=play_nonce,
                on_track_change=on_track_change,
                on_complete=on_complete,
                on_prev=play_prev,
                on_next=play_next,
            ),
        ],
        expand=True,
        spacing=0,
    )


# ═══════════════════════════════════════════════════════════
#  侧边栏 — 菜单 + 播放列表
# ═══════════════════════════════════════════════════════════
@ft.component
def Sidebar(
    display: list,
    current_index: int,
    sort_key: str,
    recents: list,
    on_play,
    on_remove,
    on_sort,
    on_open_file,
    on_open_folder,
    on_open_recent,
):
    hovered_idx, set_hovered_idx = ft.use_state(-1)

    # ── 菜单按钮 ──
    def _menu_btn(icon, text, on_click):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=18, color=C_PRIMARY),
                    ft.Text(text, color=C_TEXT, size=13),
                ],
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=6,
            ink=True,
            on_click=on_click,
            on_hover=lambda e: set_hovered_idx(-2) if str(e.data) == "true" else set_hovered_idx(-1),
        )

    # ── 近期视频菜单项 ──
    recent_items = [
        ft.PopupMenuItem(
            content=ft.Text(
                Path(p).name,
                color=C_TEXT,
                size=12,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            on_click=lambda e, p=p: on_open_recent(p),
        )
        for p in recents[:10]
    ] or [ft.PopupMenuItem(content=ft.Text("暂无记录", color=C_TEXT_SUB, size=12))]

    # ── 排序按钮 ──
    def _sort_btn(key):
        active = sort_key == key
        return ft.Container(
            content=ft.Text(
                SORT_LABELS[key],
                color=C_PRIMARY if active else C_TEXT_SUB,
                size=11,
                weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400,
            ),
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            border_radius=4,
            bgcolor=C_BG_ACTIVE if active else None,
            ink=True,
            on_click=lambda e: on_sort(key),
        )

    # ── 播放列表项 ──
    def _playlist_item(orig_idx: int, item: dict, seq: int):
        is_active = orig_idx == current_index
        is_hovered = seq == hovered_idx
        bg = C_BG_ACTIVE if is_active else (C_BG_HOVER if is_hovered else None)

        return ft.ContextMenu(
            content=ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.PLAY_CIRCLE if is_active else ft.Icons.VIDEO_FILE,
                            size=16,
                            color=C_PRIMARY if is_active else C_TEXT_SUB,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    item["title"],
                                    color=C_TEXT if is_active else C_TEXT,
                                    size=12,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400,
                                ),
                                ft.Text(
                                    human_size(item["size"]),
                                    color=C_TEXT_SUB,
                                    size=10,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                bgcolor=bg,
                border_radius=4,
                ink=True,
                on_click=lambda e: on_play(orig_idx),
                on_hover=lambda e: set_hovered_idx(seq) if str(e.data) == "true" else set_hovered_idx(-1),
            ),
            secondary_items=[
                ft.PopupMenuItem(
                    content=ft.Text("播放", color=C_TEXT, size=12),
                    icon=ft.Icons.PLAY_ARROW,
                    on_click=lambda e: on_play(orig_idx),
                ),
                ft.PopupMenuItem(
                    content=ft.Text("从列表移除", color=C_RED, size=12),
                    icon=ft.Icons.DELETE_OUTLINE,
                    on_click=lambda e: on_remove(orig_idx),
                ),
            ],
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                # ── 标题 ──
                ft.Container(
                    content=ft.Text(
                        "CS Video Player",
                        color=C_TEXT,
                        size=15,
                        weight=ft.FontWeight.W_700,
                    ),
                    padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                ),

                # ── 菜单区 ──
                ft.Container(
                    content=ft.Column(
                        controls=[
                            _menu_btn(ft.Icons.VIDEO_FILE, "打开文件", on_open_file),
                            _menu_btn(ft.Icons.FOLDER_OPEN, "打开文件夹", on_open_folder),
                            ft.PopupMenuButton(
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.HISTORY, size=18, color=C_PRIMARY),
                                        ft.Text("近期视频", color=C_TEXT, size=13),
                                    ],
                                    spacing=8,
                                ),
                                items=recent_items,
                                bgcolor=C_BG_ITEM,
                                menu_position=ft.PopupMenuPosition.UNDER,
                            ),
                        ],
                        spacing=2,
                    ),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                ),

                # ── 分割线 ──
                ft.Container(
                    height=1, bgcolor=C_BORDER,
                    margin=ft.Padding.symmetric(horizontal=12, vertical=4),
                ),

                # ── 排序栏 ──
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text("播放列表", color=C_TEXT_SUB, size=11, weight=ft.FontWeight.W_600),
                            ft.Container(expand=True),
                            *[_sort_btn(k) for k in ("default", "name", "size")],
                        ],
                        spacing=4,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                ),

                # ── 播放列表 ──
                ft.Container(
                    content=ft.ListView(
                        controls=[
                            _playlist_item(oi, item, seq)
                            for seq, (oi, item) in enumerate(display)
                        ]
                        or [
                            ft.Container(
                                content=ft.Text(
                                    "暂无视频\n请打开文件或文件夹",
                                    color=C_TEXT_SUB,
                                    size=12,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                alignment=ft.Alignment.CENTER,
                                padding=40,
                            )
                        ],
                        expand=True,
                        spacing=2,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
        ),
        width=320,
        bgcolor=C_BG_PANEL,
        border=ft.Border(right=ft.BorderSide(1, C_BORDER)),
        expand=False,
    )


# ═══════════════════════════════════════════════════════════
#  播放器区域 — Video + 自定义控制条
# ═══════════════════════════════════════════════════════════
@ft.component
def PlayerArea(
    playlist: list,
    current_index: int,
    play_nonce: int,
    on_track_change,
    on_complete,
    on_prev,
    on_next,
):
    # ── 局部状态（高频更新隔离在 PlayerArea 内） ──
    position_ms, set_position_ms = ft.use_state(0)
    duration_ms, set_duration_ms = ft.use_state(0)
    is_playing, set_is_playing = ft.use_state(False)
    volume, set_volume = ft.use_state(100.0)
    rate, set_rate = ft.use_state(1.0)
    muted, set_muted = ft.use_state(False)
    is_fullscreen, set_is_fullscreen = ft.use_state(False)

    video_ref = ft.use_ref()
    # 拖拽状态用 ref 跟踪：立即生效、不触发重渲染、避免闭包过期
    seeking_ref = ft.use_ref(False)
    seek_pos_ref = ft.use_ref(0)

    # ── 播放请求：nonce 变化时跳转 + 播放 ──
    def _do_play():
        if not playlist or not video_ref.current:
            return

        async def _jump():
            v = video_ref.current
            if v and 0 <= current_index < len(playlist):
                await v.jump_to(current_index)
                await v.play()
                set_is_playing(True)

        import asyncio
        asyncio.ensure_future(_jump())

    ft.use_effect(_do_play, dependencies=[play_nonce])

    # ── Video 事件处理 ──
    def _on_load(e):
        set_is_playing(True)

    def _on_pos(e):
        if not seeking_ref.current:
            set_position_ms(parse_ms(e.data))

    def _on_dur(e):
        set_duration_ms(parse_ms(e.data))

    def _on_enter_fs(e):
        set_is_fullscreen(True)

    def _on_exit_fs(e):
        set_is_fullscreen(False)

    # ── 控制条回调 ──
    async def _toggle_play():
        v = video_ref.current
        if not v:
            return
        await v.play_or_pause()
        set_is_playing(not is_playing)

    async def _do_seek(pos: int):
        v = video_ref.current
        if v:
            await v.seek(ft.Duration(milliseconds=pos))
            set_position_ms(pos)

    def _on_slider_start(e):
        seeking_ref.current = True
        seek_pos_ref.current = position_ms

    def _on_slider_change(e):
        try:
            seek_pos_ref.current = int(float(e.data))
        except (TypeError, ValueError):
            pass

    def _on_slider_end(e):
        try:
            pos = int(float(e.data))
        except (TypeError, ValueError):
            pos = seek_pos_ref.current
        seeking_ref.current = False
        set_position_ms(pos)
        import asyncio
        asyncio.ensure_future(_do_seek(pos))

    async def _vol_change(e):
        try:
            val = float(e.data)
        except (TypeError, ValueError):
            return
        set_volume(val)
        if muted and val > 0:
            set_muted(False)

    async def _toggle_mute():
        set_muted(not muted)

    async def _toggle_fullscreen():
        set_is_fullscreen(not is_fullscreen)

    def _rate_label(r):
        return f"{r:g}x"

    # ── 当前视频信息 ──
    has_video = bool(playlist) and 0 <= current_index < len(playlist)
    title = playlist[current_index]["title"] if has_video else ""

    # ── Video 控件 ──
    video_playlist = (
        [VideoMedia(resource=to_uri(item["path"])) for item in playlist]
        if playlist
        else []
    )

    slider_max = max(duration_ms, 1)

    # ── 控制条按钮 ──
    def _icon_btn(icon, on_click, tooltip="", enabled=True, color=None):
        return ft.IconButton(
            icon=icon,
            icon_color=color or C_TEXT,
            on_click=on_click,
            tooltip=tooltip,
            disabled=not enabled,
            icon_size=20,
        )

    return ft.Column(
        controls=[
            # ── 视频画面 ──
            ft.Stack(
                controls=[
                    ft.GestureDetector(
                        content=ft.Container(
                            content=Video(
                                ref=video_ref,
                                playlist=video_playlist,
                                playlist_mode=PlaylistMode.NONE,
                                controls={
                                    VideoControlsMode.NORMAL: None,
                                    VideoControlsMode.FULLSCREEN: _fullscreen_controls(),
                                },
                                fullscreen=is_fullscreen,
                                volume=volume,
                                playback_rate=rate,
                                muted=muted,
                                fill_color=C_BG_DARK,
                                on_load=_on_load,
                                on_track_change=on_track_change,
                                on_complete=on_complete,
                                on_position_change=_on_pos,
                                on_duration_change=_on_dur,
                                on_enter_fullscreen=_on_enter_fs,
                                on_exit_fullscreen=_on_exit_fs,
                                expand=True,
                            ),
                            expand=True,
                            bgcolor=C_BG_DARK,
                        ),
                        on_double_tap=_toggle_fullscreen,
                        expand=True,
                    ),
                    # ── 空状态占位 ──
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(
                                    ft.Icons.VIDEO_LIBRARY_OUTLINED,
                                    size=56,
                                    color=C_TEXT_SUB,
                                ),
                                ft.Text("请打开视频文件", color=C_TEXT_SUB, size=15),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        expand=True,
                        alignment=ft.Alignment.CENTER,
                        visible=not has_video,
                    ),
                ],
                expand=True,
            ),

            # ── 控制条 ──
            ft.Container(
                content=ft.Column(
                    controls=[
                        # 标题
                        ft.Container(
                            content=ft.Text(
                                title,
                                color=C_TEXT,
                                size=13,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                weight=ft.FontWeight.W_500,
                            ),
                            padding=ft.Padding.only(left=12, right=12, top=8),
                            visible=has_video,
                        ),
                        # 进度条
                        ft.Row(
                            controls=[
                                ft.Text(
                                    fmt_time(position_ms),
                                    color=C_TEXT_SUB,
                                    size=11,
                                ),
                                ft.Slider(
                                    min=0,
                                    max=slider_max,
                                    value=position_ms,
                                    active_color=C_PRIMARY,
                                    inactive_color=C_BORDER,
                                    thumb_color=C_PRIMARY,
                                    expand=True,
                                    on_change_start=_on_slider_start,
                                    on_change=_on_slider_change,
                                    on_change_end=_on_slider_end,
                                ),
                                ft.Text(
                                    fmt_time(duration_ms),
                                    color=C_TEXT_SUB,
                                    size=11,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        # 按钮行
                        ft.Row(
                            controls=[
                                _icon_btn(
                                    ft.Icons.SKIP_PREVIOUS,
                                    lambda e: on_prev(),
                                    "上一个",
                                    enabled=current_index > 0,
                                ),
                                _icon_btn(
                                    ft.Icons.PAUSE if is_playing else ft.Icons.PLAY_ARROW,
                                    _toggle_play,
                                    "暂停/播放",
                                    enabled=has_video,
                                    color=C_PRIMARY,
                                ),
                                _icon_btn(
                                    ft.Icons.SKIP_NEXT,
                                    lambda e: on_next(),
                                    "下一个",
                                    enabled=current_index < len(playlist) - 1,
                                ),
                                ft.Container(width=12),
                                # 倍速
                                ft.PopupMenuButton(
                                    content=ft.Text(
                                        _rate_label(rate),
                                        color=C_PRIMARY,
                                        size=12,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    items=[
                                        ft.PopupMenuItem(
                                            content=ft.Text(
                                                _rate_label(s),
                                                color=C_PRIMARY if s == rate else C_TEXT,
                                                size=12,
                                            ),
                                            icon=ft.Icons.CHECK if s == rate else None,
                                            on_click=lambda e, s=s: set_rate(s),
                                        )
                                        for s in SPEEDS
                                    ],
                                    bgcolor=C_BG_ITEM,
                                    menu_position=ft.PopupMenuPosition.UNDER,
                                ),
                                ft.Container(expand=True),
                                # 音量
                                _icon_btn(
                                    ft.Icons.VOLUME_OFF if muted or volume == 0
                                    else ft.Icons.VOLUME_UP,
                                    _toggle_mute,
                                    "静音",
                                    color=C_TEXT_SUB,
                                ),
                                ft.Slider(
                                    min=0,
                                    max=100,
                                    value=0 if muted else volume,
                                    active_color=C_PRIMARY,
                                    inactive_color=C_BORDER,
                                    thumb_color=C_PRIMARY,
                                    width=90,
                                    on_change=_vol_change,
                                ),
                                ft.Container(width=8),
                                # 全屏
                                _icon_btn(
                                    ft.Icons.FULLSCREEN if not is_fullscreen
                                    else ft.Icons.FULLSCREEN_EXIT,
                                    _toggle_fullscreen,
                                    "全屏",
                                    color=C_TEXT_SUB,
                                ),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=4,
                ),
                bgcolor=C_BG_PANEL,
                border=ft.Border(top=ft.BorderSide(1, C_BORDER)),
                padding=ft.Padding.only(left=8, right=12, top=4, bottom=8),
            ),
        ],
        expand=True,
        spacing=0,
    )


# ═══════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════
async def main(page: ft.Page):
    page.title = "CS Video Player"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = C_BG_DARK
    page.window.width = 1200
    page.window.height = 750
    page.window.min_width = 900
    page.window.min_height = 600
    page.window.resizable = True
    await page.window.center()
    page.render(App)


if __name__ == "__main__":
    ft.run(main)
