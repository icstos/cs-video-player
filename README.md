# CS Video Player

[中文](README.zh-CN.md) | English

A Windows desktop local video player built with Python 3.12+, **cs-ui** (a
declarative component library on top of Flet 1.1.2) and **flet-video**. Inspired
by PotPlayer's interaction design and VLC's format versatility.

Everything video-specific — native player facade, timeline / volume / speed
controls, the derived color table — lives in `src/cs_video_player/components/media/`.
cs-ui stays a general UI toolkit: it ships no player component and no
`flet-video` dependency. The app still never imports `flet` directly;
`flet_video` appears in exactly one file, `media/backend.py`.

## Features

- **Full format support** — MP4, MKV, AVI, MOV, FLV, WebM, WMV, MPG, TS, RMVB, and more
- **Declarative UI** — `@ui.component` hooks (`use_state`, `use_effect`, `use_memo`, `use_ref`, `use_context`)
- **One source of design** — colors, spacing, type scale and icon sizes derive from `ui.core.tokens` + `cs_video_player.configs.theme.MediaPalette`
- **Playlist management** — Add files/folders, sort by name/size/date, drag reorder
- **Multi-file selection** — Pick multiple files at once or open an entire folder
- **Playback modes** — Sequence, Loop All, Loop One, Shuffle
- **Playback controls** — Play/pause, stop, prev/next, seek ±10s (Shift for ±20s)
- **Progress bar** — Drag to seek with live time label; click time to toggle remaining-time display
- **Volume system** — Slider, mute toggle, mouse wheel adjustment, persistent
- **Playback speed** — 0.25x–16x via a compact dropdown
- **Fullscreen** — Double-click video or press `F`/`F11`; control bar auto-hides, shows on mouse move to bottom
- **Keyboard shortcuts** — Space, ←/→, ↑/↓, [/], M, F, F11, N, P, S, T, Ctrl+O, Ctrl+Shift+O, Escape, Delete
- **Recent files** — Persistent history of last 30 opened files
- **Settings persistence** — Volume, playback rate, play mode, sidebar width, time display mode
- **Session restore** — Remembers playlist, current track, and playback position on exit; prompts to resume on next launch
- **Hardware acceleration** — Via mpv/libmpv backend
- **Screenshots** — Capture current frame via `NativeVideo.take_screenshot()`

## Project Structure

```
cs-video-player/
  main.py                      # Entry: sys.path bootstrap -> cs_video_player.bootstrap.run()
  pyproject.toml               # src layout + cs-ui / flet-video deps
  assets/                      # Packaging resources (icons)
  src/
    cs_video_player/
      __init__.py              # Version
      _paths.py                # Single source for asset paths (assets_dir / project_root)
      bootstrap.py             # Startup: logging, theme, window, page.render
      configs/
        app_config.py          # Business constants & configuration
        theme.py               # Design layer: brand color -> MediaPalette + cs-ui tokens
      core/
        models.py              # Data models (PlaylistItem, PlayerState, enums)
        video_engine.py        # NativeVideo wrapper (async-safe, pure mapping)
        player_controller.py   # State management bridge
      components/
        kit.py                 # Product UI vocabulary (pure widget factories)
        media/
          backend.py           # The only file importing flet_video (player facade)
          controls.py          # Stateless controls (TimeSlider / VolumeControl / SpeedMenu)
        control_bar.py         # Compact control bar (assembles those controls)
        app.py                 # Root component (keyboard, FileDialog, session restore)
        sidebar.py             # Playlist, file open, recents, drag reorder
        player_area.py         # Video display + playback event orchestration
        ui_helpers.py          # Legacy compatibility shim -> kit
      utils/                   # Pure functions: formatting, storage, scanner, errors
  scripts/
    test_logic.py              # Pure-logic regression (21 tests, no window)
    verify_app.py              # Hidden-window render smoke + optional screenshot
```

Why **src layout**: packages live under `src/cs_video_player/`, the repo root keeps
only the entry point and config. `python main.py`, `pip install -e .` and isolated
packaging all resolve the same module path — no more "works from source, broken
after install" split.

`kit.py` is the only place that assembles cs-ui widgets into this product's
vocabulary; views describe structure and copy, never colors or font sizes.
`components/media/` is the video seam: pure widget tree above, the only
`flet-video` knowledge below.

## Installation

```bash
pip install .          # pulls cs-ui (>=0.2.0) plus flet-video (1.1.x)
pip install -e .       # development: installs src/cs_video_player, edits apply live
```

## Usage

```bash
python main.py         # run from source (the entry adds src/ to sys.path)
cs-video-player        # installed console script, same run()
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `←` / `→` | Seek -10s / +10s (Shift for -20s / +20s) |
| `↑` / `↓` | Volume +5 / -5 |
| `[` / `]` | Speed down / up |
| `M` | Toggle mute |
| `F` / `F11` | Toggle fullscreen |
| `N` / `P` | Next / Previous track |
| `S` | Stop |
| `T` | Toggle remaining time display |
| `Ctrl+O` | Open file dialog |
| `Ctrl+Shift+O` | Open folder dialog |
| `Esc` | Exit fullscreen |
| `Delete` | Remove current from playlist |

## Design & Verification

The design layer is **recomputable**: one brand color (`BRAND_PRIMARY`) is fed to
`cs_video_player.configs.theme.MediaPalette.derive(brand, mode="dark")`; the resulting
scheme is shared by the page theme, the custom control bar and the native
fullscreen controls. `configs.theme.palette_snapshot()` prints the whole table, and ui-mcp
indexes every public cs-ui widget for lookup.

```bash
python scripts/test_logic.py                                  # 21 pure-logic tests
python scripts/verify_app.py                                   # hidden-window render smoke
python scripts/verify_app.py --demo --shot output/app_with_list.png
```

`verify_app.py` renders the real component tree in a hidden window, checks that
the file-dialog service is attached, and can export a UI screenshot. It never
writes to the user's `~/.cs_video_player` data.

## Tech Stack

- **Python 3.12+**
- **cs-ui ≥ 0.2.0** — component library on Flet 1.1.2: widgets, tokens, hooks
- **flet-video 1.1.x** — native playback backend, reached only via `src/cs_video_player/components/media/backend.py`
- **src layout** — `package-dir = src`: source runs, editable installs and packaged builds share one module path
- **`@ui.component` hooks** — declarative state, memoized sorting, effect cleanups
- **Design tokens** — `ui.core.tokens` + `cs_video_player.configs.theme.MediaPalette` (computed colors, 4px grid, type scale)
- **OOP design** — Controller / Engine / Model separation; UI is a pure projection of state
- **State-driven UI** — `PlayerState` as single source of truth, reactive updates via listener callbacks

## Architecture

```
                    ┌──────────────────────┐
                    │ main.py -> bootstrap │
                    │  (ui.run/theme)      │
                    └──────────┬───────────┘
                             │
                    ┌────────▼─────────┐
                    │   App component   │
                    │ (keyboard, dialog)│
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │                             │
    ┌─────────▼────────┐          ┌─────────▼─────────┐
    │   Sidebar        │          │   PlayerArea       │
    │ (playlist, files) │          │ (Video + controls) │
    └──────────────────┘          └───────────────────┘
              │                             │
              └──────────┬──────────────────┘
                         │
              ┌──────────▼──────────┐
              │ PlayerController     │
              │ (state management)   │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   VideoEngine        │
              │ (components.media)   │
              └─────────────────────┘
```
