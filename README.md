# CS Video Player

[中文](README.zh-CN.md) | English

A Windows desktop local video player built with Python 3.12+, **cs-ui** (a
declarative component library on Flet 1.1.2) and **flet-video**. Inspired by
PotPlayer's interaction design and VLC's format versatility.

The code is organised as **MVVM + five-layer dependency inversion**:
`models → infra → service → viewmodel → view`, with a one-way dependency
`View → ViewModel → Service → Infra`. The UI is a pure projection of
`AppState`: `UI = f(state)`. `flet_video` is imported in exactly one file,
`view/native_video.py`; application code never imports `flet` directly.

## Features

- **Full format support** — MP4, MKV, AVI, MOV, FLV, WebM, WMV, MPG, TS, RMVB, and more
- **Declarative UI** — `@ui.component` hooks; every pixel derived from one immutable `AppState`
- **One source of design** — colors, spacing, type scale and icon sizes derive from `ui.core.tokens` + `view.theme.MediaPalette`
- **Playlist management** — Add files/folders, sort by name/size/date, drag reorder
- **Multi-file selection** — Pick multiple files at once or open an entire folder
- **Playback modes** — Sequence, Loop All, Loop One, Shuffle
- **Playback controls** — Play/pause, stop, prev/next, seek ±10s (Shift for ±20s)
- **Progress bar** — Drag to seek with live time label; click time to toggle remaining-time display
- **Volume system** — Slider, mute toggle, mouse wheel adjustment, persistent
- **Playback speed** — 0.25x–16x via a compact dropdown
- **Fullscreen** — Double-click video or press `F`/`F11`; control bar auto-hides, shows on mouse move
- **Keyboard shortcuts** — Space, ←/→, ↑/↓, [/], M, F, F11, N, P, S, T, Ctrl+O, Ctrl+Shift+O, Escape, Delete
- **Recent files** — Persistent history of last 30 opened files
- **Settings persistence** — Volume, playback rate, play mode, sidebar width, time display mode
- **Session restore** — Remembers playlist, current track and position; prompts to resume on next launch
- **Hardware acceleration** — Via mpv/libmpv backend
- **Screenshots** — Capture current frame via the native player handle

## Project Structure

```
cs-video-player/
  main.py                        # sys.path bootstrap -> cs_video_player.bootstrap.run()
  pyproject.toml                 # src layout + cs-ui / flet-video deps
  assets/                        # Packaging resources
  src/cs_video_player/
    __init__.py                  # Version
    _paths.py                    # Single source for asset paths
    bootstrap.py                 # Composition root: Infra -> Service -> ViewModel -> View
    models/                      # ① Data, enums, constants; no business logic
      config.py                    # Constants, shortcuts, supported formats
      enums.py                     # PlayMode / SortKey / ListMode / NoticeTone / FileRequestKind
      entities.py                  # PlaylistItem / MediaTrack / Notice / KeyInfo / FileRequest
      state.py                     # PlaybackState -> AppState (frozen, slots)
    infra/                       # ② Abstract ports + technical adapters
      ports.py                     # VideoControl / MediaPort / PreferencesPort / ScannerPort
      media.py                     # Async-safe player adapter (errors downgraded)
      preferences.py               # JSON settings / recents / session
      scanner.py                   # File system -> playlist items / file URIs
    service/                     # ③ Business rules and orchestration
      rules.py                     # Pure rules: sorting, projection, speed, index, errors
      playback.py                  # PlaybackService: state machine + port orchestration
    viewmodel/                   # ④ Pure Python UI state adapter
      app_vm.py                    # AppViewModel: intents in, AppState out; no UI imports
    view/                        # ⑤ cs-ui declarative rendering + event dispatch
      app.py                       # Root view: subscriptions, host events, memoized subtrees
      sidebar.py                   # Playlist, sorting, recents, file entries
      player_area.py               # Video + control bar, pure event dispatch
      control_bar.py               # Compact control bar (window / fullscreen)
      native_video.py              # ONLY flet_video import; VideoHandle adapter
      widgets.py                   # Stateless TimeSlider / VolumeControl / SpeedMenu
      kit.py                       # Product UI vocabulary (no raw colors/fonts in views)
      theme.py                     # Design layer: brand color -> MediaPalette + tokens
      formatters.py                # Time / size / platform event parsing
  scripts/
    test_logic.py                # 23 pure-logic tests (no window)
    verify_app.py                # Hidden-window render smoke + optional screenshot
    check_architecture.py        # Executable architecture / typing constraints
```

Why **src layout**: packages live under `src/cs_video_player/`; the repository
root keeps only the entry point and config. Source runs, editable installs and
packaged builds all share one module path.

## Dependency Inversion

```
View ──calls intents──> ViewModel ──calls commands──> Service ──uses──> Infra ports
  │                         │                           │                  ▲
  └──renders AppState◄──────┘                           └──models──────────┘
All layers may depend on models. No upward or skip-level calls.
```

- **models** — immutable data, enums and constants. No business logic, no I/O.
- **infra** — abstracts storage / file system / native playback behind protocols;
  contains no business rules. The View injects a `VideoHandle` into the port,
  so Infra never imports the View or a UI framework.
- **service** — owns the playback state machine; depends only on abstraction
  ports and pure rules. It never touches a widget.
- **viewmodel** — plain Python. Owns UI interaction state (sidebar, seek drag,
  auto-hide, dialog requests, session prompt), subscribes to Service, and
  publishes one flat `AppState` snapshot.
- **view** — `@ui.component` functions. Reads state, dispatches typed events,
  memoizes expensive subtrees; no business decisions, no side-effect timers.

`play_nonce` in the business state is the single trigger for starting playback;
the ViewModel observes it and asks the Service to drive the media port. This
keeps "when to play" in the domain and "how to play" in infrastructure.

## Installation

```bash
pip install .          # pulls cs-ui (>=0.2.0) plus flet-video (1.1.x)
pip install -e .       # development: edits apply live
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

The design layer is **recomputable**: one brand color
(`view.theme.BRAND_PRIMARY`) feeds `MediaPalette.derive(brand, mode="dark")`;
the resulting scheme drives the page theme, the custom control bar and the
native fullscreen controls. `palette_snapshot()` prints the whole table.
ui-mcp indexes every public cs-ui widget for lookup.

```bash
python scripts/check_architecture.py                          # layer + typing constraints
python scripts/test_logic.py                                  # 23 pure-logic tests
python scripts/verify_app.py                                  # hidden-window render smoke
python scripts/verify_app.py --demo --shot output/app_with_list.png
```

`verify_app.py` injects a temporary preferences directory through the
composition root: it renders the real tree, checks service attachment, and
never writes to the user's `~/.cs_video_player`.

## Tech Stack

- **Python 3.12+** — 3.13 compatible; `@dataclass(slots=True)`, `match`, `X | None`, full annotations
- **cs-ui ≥ 0.2.0** — widgets, design tokens and component hooks on Flet 1.1.2
- **flet-video 1.1.x** — reached only through `view/native_video.py`
- **MVVM + five layers** — one-way dependency, protocols at the boundaries
- **Declarative state** — frozen `AppState`; sorting / sidebar memoized, native player rebuilt each frame (Flet reconciles by control ID, no reload)
- **Recomputable design** — one brand color + cs-ui tokens, snapshots for agents and tests
