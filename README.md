# CS Video Player

声明式本地视频播放器，基于 Python 3.12 + Flet 0.85.3 + flet-video 构建。

专业蓝色主色调，高级科技风暗色主题，界面简洁专业。

## 功能

- **菜单**：打开文件（直接播放）、打开文件夹（批量导入并播放第一个）、打开近期视频（最近 10 条记录）
- **播放列表**：文件信息展示，支持按默认 / 名称 / 大小排序，右键菜单播放 / 移除
- **播放器**：上一个 / 下一个、播放 / 暂停、进度条拖拽 seek、倍速播放（0.5x ~ 2.0x）、音量控制、静音、全屏
- **双击全屏**：双击视频画面快速切换全屏 / 窗口模式
- **动态标题**：切换视频时窗口标题显示当前文件名
- **近期记录**：自动保存最近打开的 10 个视频到 `~/.cs_video_player_recent.json`

## 技术栈

| 依赖 | 版本 |
|------|------|
| Python | 3.12+ |
| flet | 0.85.3 |
| flet-video | 0.85.3 |

## 安装

```bash
pip install flet==0.85.3 flet-video==0.85.3
```

## 运行

```bash
python main.py
```

## 架构

采用 Flet 声明式范式（`@ft.component` + `ft.use_state`），三个核心组件：

```
App（根组件）
├── Sidebar（左侧：菜单 + 排序 + 播放列表）
└── PlayerArea（右侧：Video + 自定义控制条）
```

### App

- 持有 `playlist / current_index / recents / sort_key / play_nonce` 状态
- `FilePicker` 通过 `use_ref(lambda: ft.FilePicker())` 创建，Service 自动注册
- 排序显示用 `sorted(enumerate(playlist), ...)` 保留原始索引，Video playlist 始终用原始顺序

### Sidebar

- 菜单按钮 + 排序栏 + ListView 播放列表
- 每项用 `ContextMenu` 包裹（右键播放 / 移除）

### PlayerArea

- 高频状态（`position_ms / duration_ms / is_playing` 等）隔离在此组件，避免 App 级重绘
- `use_effect(_do_play, deps=[play_nonce])` 在 render commit 后触发 `jump_to + play`
- `seeking_ref` 隔离拖拽与播放更新，防止位置回调覆盖拖拽中的滑块
- Video `controls` 分模式配置：正常模式隐藏内置控件用自定义控制条，全屏用蓝色主题的 `MaterialDesktopVideoControls`

## 配色

| 常量 | 色值 | 用途 |
|------|------|------|
| `C_PRIMARY` | `#2F80ED` | 主色（按钮、进度条、选中态） |
| `C_HOVER` | `#4A90F5` | 悬停色 |
| `C_BG_DARK` | `#0E131B` | 最深背景（播放区） |
| `C_BG_PANEL` | `#161E2E` | 面板背景（侧栏） |
| `C_BG_ITEM` | `#1E283A` | 列表项背景 |
| `C_BG_ACTIVE` | `#1C3A5E` | 选中项背景 |
| `C_BORDER` | `#2A3548` | 描边色 |
| `C_TEXT` | `#E8EDF5` | 主文字 |
| `C_TEXT_SUB` | `#8B95A8` | 次文字 |

## 支持的视频格式

`.mp4` `.avi` `.mkv` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpg` `.mpeg` `.ts` `.3gp` `.m2ts`
