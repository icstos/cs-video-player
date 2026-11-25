# CS 视频播放器

[English](README.md) | 中文

基于 Python 3.12+、**cs-ui**（构建于 Flet 1.1.2 之上的声明式组件库）与
**flet-video** 开发的 Windows 桌面本地视频播放器。交互设计灵感来自 PotPlayer，
格式兼容性对标 VLC。

代码采用 **MVVM + 五层依赖倒置**架构：`models → infra → service → viewmodel → view`，
单向依赖 `View → ViewModel → Service → Infra`。界面是状态的纯投影：`UI = f(AppState)`。
`flet_video` 只在 `view/native_video.py` 一处出现，应用代码不直接 `import flet`。

## 功能特性

- **全格式支持** — MP4、MKV、AVI、MOV、FLV、WebM、WMV、MPG、TS、RMVB 等
- **声明式 UI** — `@ui.component` hooks；每个像素都来自同一份不可变 `AppState`
- **设计只有一套** — 颜色、间距、字号、图标刻度由 `ui.core.tokens` 与 `view.theme.MediaPalette` 推导
- **播放列表管理** — 添加文件/文件夹，按名称/大小/日期排序，拖拽排序
- **多文件选择** — 一次选择多个文件或打开整个文件夹
- **播放模式** — 顺序播放、列表循环、单曲循环、随机播放
- **播放控制** — 播放/暂停、停止、上一曲/下一曲、快进/快退（默认 10 秒，Shift 加倍）
- **进度条** — 可拖拽跳转并实时显示时间标签，点击时间文字切换剩余时间显示
- **音量系统** — 滑块调节、静音切换、鼠标滚轮调节音量，音量值持久化记忆
- **倍速播放** — 0.25x ~ 16x，紧凑下拉菜单一键切换
- **全屏模式** — 双击视频或按 `F`/`F11` 进入全屏，控制栏自动隐藏，鼠标移到底部时显示
- **键盘快捷键** — 空格、←/→、↑/↓、[/]、M、F、F11、N、P、S、T、Ctrl+O、Ctrl+Shift+O、Esc、Delete
- **最近文件** — 持久化保存最近 30 个打开的文件记录
- **设置持久化** — 音量、播放倍速、播放模式、侧栏宽度、时间显示模式
- **会话恢复** — 退出时保存播放列表、当前曲目与播放进度，下次启动可选择继续播放
- **硬件加速** — 基于 mpv/libmpv 后端
- **截图** — 通过原生播放器句柄截取当前画面

## 项目结构

```
cs-video-player/
  main.py                        # 入口：sys.path 引导 → cs_video_player.bootstrap.run()
  pyproject.toml                 # src 布局 + cs-ui / flet-video 依赖
  assets/                        # 打包资源
  src/cs_video_player/
    __init__.py                  # 版本号
    _paths.py                    # 资源路径唯一出口
    bootstrap.py                 # 组合根：Infra → Service → ViewModel → View
    models/                      # ① 模型层：数据/枚举/常量，无业务逻辑
      config.py                    # 常量、快捷键、支持格式
      enums.py                     # PlayMode / SortKey / ListMode 等
      entities.py                  # PlaylistItem / MediaTrack / Notice / KeyInfo
      state.py                     # PlaybackState → AppState（frozen + slots）
    infra/                       # ② 基础设施层：抽象端口 + 技术实现
      ports.py                     # VideoControl / MediaPort / PreferencesPort / ScannerPort
      media.py                     # 异步安全的播放器适配（错误降级）
      preferences.py               # JSON 设置 / 近期记录 / 会话
      scanner.py                   # 文件系统 → 播放列表项 / file URI
    service/                     # ③ 服务层：业务规则 + 编排
      rules.py                     # 纯规则：排序、投影、倍速、索引、错误分类
      playback.py                  # PlaybackService：状态机 + 端口编排
    viewmodel/                   # ④ 视图模型层：纯 Python UI 状态适配器
      app_vm.py                    # AppViewModel：意图进、AppState 出，不 import UI
    view/                        # ⑤ 视图层：cs-ui 声明式渲染 + 事件分发
      app.py                       # 根视图：订阅、宿主事件、子树 memo
      sidebar.py                   # 播放列表、排序、近期记录、文件入口
      player_area.py               # 画面 + 控制栏，纯事件分发
      control_bar.py               # 紧凑控制栏（窗口 / 全屏共用）
      native_video.py              # 唯一 import flet_video 处；VideoHandle 适配器
      widgets.py                   # 无状态 TimeSlider / VolumeControl / SpeedMenu
      kit.py                       # 产品 UI 词汇层（视图不写色值/字号）
      theme.py                     # 设计层：品牌色 → MediaPalette + 令牌
      formatters.py                # 时间/大小/平台事件解析
  scripts/
    test_logic.py                # 23 项纯逻辑测试（无需窗口）
    verify_app.py                # 隐藏窗口渲染冒烟 + 可选截图
    check_architecture.py        # 可执行的架构与类型约束
```

**src 布局**让源码直跑、editable 安装与隔离打包共用同一模块路径，不会出现
「本地能跑、装完找不到包」的分裂。

## 依赖倒置

```
View ──调用意图──> ViewModel ──调用命令──> Service ──使用──> Infra 抽象端口
  │                    │                      │                    ▲
  └──渲染 AppState◄─────┘                      └──Models────────────┘
所有层都可依赖 Models；禁止反向依赖与跨层调用。
```

- **models** — 不可变数据、枚举与常量；无业务逻辑、无 I/O。
- **infra** — 用 Protocol 隔离存储、文件系统与原生播放；不含业务规则。
  View 注入 `VideoHandle`，因此 Infra 不反向依赖 View 或任何 UI 框架。
- **service** — 持有播放状态机，只依赖抽象端口与纯规则，不认识任何控件。
- **viewmodel** — 纯 Python，持有 UI 交互态（侧栏、拖动、自动隐藏、对话框请求、
  会话确认），订阅 Service，对外发布一帧扁平 `AppState`。
- **view** — `@ui.component` 函数：读状态、分发类型化事件、memo 高成本子树；
  不做业务判断，也不持有副作用定时器。

业务状态里的 `play_nonce` 是起播的唯一触发源：ViewModel 观察它并让 Service
驱动媒体端口。「何时播」属于业务，「怎么播」属于基础设施。

## 安装

```bash
pip install .          # 自动带入 cs-ui（>=0.2.0）与 flet-video（1.1.x）
pip install -e .       # 开发模式，改动即时生效
```

## 使用

```bash
python main.py         # 源码直跑（入口自动把 src 挂上 sys.path）
cs-video-player        # 安装后的命令行入口，指向同一个 run()
```

### 键盘快捷键

| 按键 | 功能 |
|------|------|
| `空格` | 播放 / 暂停 |
| `←` / `→` | 后退 / 前进 10 秒（Shift 加倍为 20 秒）|
| `↑` / `↓` | 音量 +5 / -5 |
| `[` / `]` | 减速 / 加速播放 |
| `M` | 切换静音 |
| `F` / `F11` | 切换全屏 |
| `N` / `P` | 下一首 / 上一首 |
| `S` | 停止播放 |
| `T` | 切换剩余时间显示 |
| `Ctrl+O` | 打开文件 |
| `Ctrl+Shift+O` | 打开文件夹 |
| `Esc` | 退出全屏 |
| `Delete` | 从播放列表中移除当前项 |

## 设计与验证

设计层是**可复算**的：唯一的自选色 `view.theme.BRAND_PRIMARY` 交给
`MediaPalette.derive(brand, mode="dark")`，算出的色表同时下发给页面主题、
自绘控制栏与原生全屏控件；`palette_snapshot()` 可打印整张表。ui-mcp 索引里
可查到 cs-ui 所有公共组件的签名。

```bash
python scripts/check_architecture.py                          # 分层与类型约束
python scripts/test_logic.py                                  # 23 项纯逻辑测试
python scripts/verify_app.py                                   # 隐藏窗口渲染冒烟
python scripts/verify_app.py --demo --shot output/app_with_list.png
```

`verify_app.py` 通过组合根注入临时数据目录，渲染真实组件树并检查服务挂载，
验证期间不会改动用户 `~/.cs_video_player` 里的真实数据。

## 技术栈

- **Python 3.12+**（兼容 3.13）— `@dataclass(slots=True)`、`match`、`X | None`、全程类型注解
- **cs-ui ≥ 0.2.0** — Flet 1.1.2 之上的控件、设计令牌与组件 hooks
- **flet-video 1.1.x** — 仅经 `view/native_video.py` 接入
- **MVVM + 五层** — 单向依赖、边界处用 Protocol
- **声明式状态** — 冻结 `AppState`；侧栏/排序做 memo，原生播放器每帧重建描述（由 Flet 按控件 ID 差分，不重载视频）
- **可复算设计** — 一个品牌色 + cs-ui 令牌，快照便于 Agent 与测试复算
