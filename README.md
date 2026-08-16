# CS Video Player

[中文](README.zh-CN.md) | English

A Windows desktop local video player built with Python 3.12+, Flet 0.86.5, and flet-video.
Inspired by PotPlayer's interaction design and VLC's format versatility.

## Features

- **Full format support** — MP4, MKV, AVI, MOV, FLV, WebM, WMV, MPG, TS, RMVB, and more
- **Declarative UI** — Built with `@ft.component` hooks API (`use_state`, `use_effect`, `use_ref`)
- **Playlist management** — Add files/folders, sort by name/size/date, drag reorder
- **Playback modes** — Sequence, Loop All, Loop One, Shuffle
- **Playback controls** — Play/pause, seek, volume, mute, playback rate (0.25x–4.0x)
- **Fullscreen** — Double-click video area or press `F`
- **Keyboard shortcuts** — Space, arrows, M, F, N, P, Escape
- **Recent files** — Persistent history of last 30 opened files
- **Settings persistence** — Volume, playback rate, play mode, sidebar width
- **Playback position memory** — Resume from where you left off
- **Hardware acceleration** — Via mpv/libmpv backend
- **Screenshots** — Capture current frame via `Video.take_screenshot()`

## Project Structure

```
cs-video-player/
  main.py                    # Entry point
  pyproject.toml             # Project config & dependencies
  configs/
    app_config.py            # Constants & configuration
    theme.py                 # Color palette & typography
  core/
    models.py                # Data models (PlaylistItem, PlayerState, enums)
    video_engine.py          # flet-video wrapper (async-safe)
    player_controller.py     # State management bridge
  components/
    app.py                   # Root component (keyboard, FilePicker, layout)
    sidebar.py               # Playlist, file open, recents
    player_area.py           # Video display + control bar
    ui_helpers.py            # Reusable widget factories
  utils/
    formatters.py            # Time/size formatting, event data parsing
    storage.py               # JSON persistence (recents, settings, positions)
    file_scanner.py          # Folder scanning for video files
```

## Installation

```bash
pip install .
```

Or for development:

```bash
pip install -e .
```

## Usage

```bash
python main.py
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `←` / `→` | Seek -5s / +5s |
| `↑` / `↓` | Volume +5 / -5 |
| `M` | Toggle mute |
| `F` | Toggle fullscreen |
| `N` / `P` | Next / Previous track |
| `Esc` | Exit fullscreen |
| `Delete` | Remove current from playlist |

## Tech Stack

- **Python 3.12+**
- **Flet 0.86.5** — Declarative UI framework (`@ft.component`, hooks API)
- **flet-video 0.86.5** — Video playback control (mpv/libmpv backend)
- **OOP design** — Controller/Engine/Model separation
- **State-driven UI** — `PlayerState` as single source of truth, reactive updates via listener callbacks

## Architecture

```
                    ┌──────────────────┐
                    │   main.py        │
                    │   (entry point)  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   App component   │
                    │ (keyboard, picker)│
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
              │ (flet-video wrapper) │
              └─────────────────────┘
```
