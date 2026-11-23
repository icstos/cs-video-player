# CS 视频播放器

[English](README.md) | 中文

基于 Python 3.12+、**cs-ui**（构建于 Flet 1.1.2 之上的声明式组件库）与
**flet-video** 开发的 Windows 桌面本地视频播放器。交互设计灵感来自 PotPlayer，
格式兼容性对标 VLC。

视频能力（原生播放器门面、时间轴 / 音量 / 倍速控制件、按品牌色推导的色表）收在
`src/cs_video_player/components/media/`：cs-ui 只做通用 UI，不再内置播放器组件，
也不会替所有使用者背上 `flet-video`。代码里仍不直接 `import flet` —— 控件与设计
令牌从 `ui` 门面取，`flet_video` 只出现在 `media/backend.py` 一处。

## 功能特性

- **全格式支持** — MP4、MKV、AVI、MOV、FLV、WebM、WMV、MPG、TS、RMVB 等
- **声明式 UI** — `@ui.component` hooks（`use_state`、`use_effect`、`use_memo`、`use_ref`、`use_context`）
- **设计只有一套** — 颜色、间距、字号、图标刻度全部由 `ui.core.tokens` 与 `cs_video_player.configs.theme.MediaPalette` 推导
- **播放列表管理** — 添加文件/文件夹，按名称/大小/日期排序，拖拽排序
- **多文件选择** — 一次选择多个文件或打开整个文件夹
- **播放模式** — 顺序播放、列表循环、单曲循环、随机播放
- **播放控制** — 播放/暂停、停止、上一曲/下一曲、快进/快退（默认 10 秒，Shift 加倍）
- **进度条** — 可拖拽跳转并实时显示时间标签，点击时间文字可切换剩余时间显示
- **音量系统** — 滑块调节、静音切换、鼠标滚轮调节音量，音量值持久化记忆
- **倍速播放** — 0.25x ~ 16x，紧凑下拉菜单一键切换
- **全屏模式** — 双击视频或按 `F`/`F11` 进入全屏，控制栏自动隐藏，鼠标移到底部时显示
- **键盘快捷键** — 空格、←/→、↑/↓、[/]、M、F、F11、N、P、S、T、Ctrl+O、Ctrl+Shift+O、Esc、Delete
- **最近文件** — 持久化保存最近 30 个打开的文件记录
- **设置持久化** — 音量、播放倍速、播放模式、侧栏宽度、时间显示模式
- **会话恢复** — 退出时自动保存播放列表、当前曲目与播放进度，下次启动时可选择继续播放
- **硬件加速** — 基于 mpv/libmpv 后端
- **截图** — 通过 `NativeVideo.take_screenshot()` 截取当前画面

## 项目结构

```
cs-video-player/
  main.py                      # 入口：sys.path 引导 → cs_video_player.bootstrap.run()
  pyproject.toml               # src 布局 + 依赖 cs-ui / flet-video
  assets/                      # 打包资源（图标等）
  src/
    cs_video_player/
      __init__.py              # 版本号
      _paths.py                # 资源路径唯一出口（assets_dir / project_root）
      bootstrap.py             # 启动：日志、主题、窗口、page.render
      configs/
        app_config.py          # 业务常量与配置
        theme.py               # 设计层：品牌色 → MediaPalette + cs-ui 令牌语义
      core/
        models.py              # 数据模型（PlaylistItem、PlayerState、枚举）
        video_engine.py        # NativeVideo 封装（异步安全、纯映射）
        player_controller.py   # 状态管理桥接层
      components/
        kit.py                 # 产品 UI 词汇层（纯控件工厂）
        media/
          backend.py           # 唯一 import flet_video 的地方（原生播放器门面）
          controls.py          # 无状态控制件（TimeSlider / VolumeControl / SpeedMenu）
        control_bar.py         # 紧凑控制栏（装配上面那几个控制件）
        app.py                 # 根组件（键盘、FileDialog、会话恢复）
        sidebar.py             # 播放列表、文件打开、最近文件、拖拽排序
        player_area.py         # 视频显示 + 播放事件编排
        ui_helpers.py          # 旧版兼容层 → kit
      utils/                   # 纯函数：格式化、持久化、扫描、错误处理
  scripts/
    test_logic.py              # 纯逻辑回归（21 项，无需窗口）
    verify_app.py              # 隐藏窗口渲染冒烟 + 可选截图
```

采样 **src 布局**：包实体在 `src/cs_video_player/` 下，仓库根只留入口与配置。
好处是 `python main.py`（源码直跑）、`pip install -e .`（可编辑安装）、隔离打包
三种情形用的是同一份模块路径，不会出现「本地能跑、装完就找不到包」的分裂。

`kit.py` 是唯一把 cs-ui 控件装配成本产品语汇的地方；视图只描述结构与文案，
不写颜色、字号或圆角。`components/media/` 是视频能力的边界：往上是纯控件树，
往下只有它认识 `flet-video`。

## 安装

```bash
pip install .          # 自动带入 cs-ui（>=0.2.0）与 flet-video（1.1.x）
pip install -e .       # 开发模式：装的是 src/cs_video_player，改代码即时生效
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

设计层是**可复算**的：唯一的自选色 `BRAND_PRIMARY` 交给
`cs_video_player.configs.theme.MediaPalette.derive(brand, mode="dark")`，算出的色表
同时下发给页面主题、自绘控制栏和原生全屏控件。
`cs_video_player.configs.theme.palette_snapshot()` 可打印
整张表，ui-mcp 索引里可查到 cs-ui 所有公共组件的签名。

```bash
python scripts/test_logic.py                                  # 21 项纯逻辑测试
python scripts/verify_app.py                                   # 隐藏窗口渲染冒烟
python scripts/verify_app.py --demo --shot output/app_with_list.png
```

`verify_app.py` 会在隐藏窗口里渲染真实组件树、检查文件对话框服务已挂载，
并可导出界面截图；验证期间不会改动用户 `~/.cs_video_player` 里的真实数据。

## 技术栈

- **Python 3.12+**
- **cs-ui ≥ 0.2.0** — 基于 Flet 1.1.2 的组件库：控件、设计令牌、hooks
- **flet-video 1.1.x** — 原生播放后端，只经 `src/cs_video_player/components/media/backend.py` 接入
- **`@ui.component` hooks** — 声明式状态、排序结果 memo、副作用清理
- **src 布局** — `package-dir = src`，开发 / editable 安装 / 打包共用一条模块路径
- **设计令牌** — `ui.core.tokens` + `cs_video_player.configs.theme.MediaPalette`（算出来的配色、4px 网格、排印律）
- **面向对象设计** — 控制器 / 引擎 / 模型分层，UI 是状态的纯投影
- **状态驱动 UI** — `PlayerState` 作为唯一数据源，通过监听回调实现响应式更新

## 架构

```
                    ┌──────────────────────┐
                    │ main.py → bootstrap   │
                    │ (ui.run / 主题)       │
                    └──────────┬───────────┘
                             │
                    ┌────────▼─────────┐
                    │   App 组件        │
                    │ (键盘、文件对话框) │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │                             │
    ┌─────────▼────────┐          ┌─────────▼─────────┐
    │   Sidebar        │          │   PlayerArea       │
    │ (播放列表、文件)   │          │ (视频 + 控制栏)     │
    └──────────────────┘          └───────────────────┘
              │                             │
              └──────────┬──────────────────┘
                         │
              ┌──────────▼──────────┐
              │ PlayerController     │
              │ (状态管理)           │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   VideoEngine        │
              │ (components.media)   │
              └─────────────────────┘
```
