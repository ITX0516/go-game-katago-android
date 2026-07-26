# 围棋对弈软件 (Go Game with Katago)

一款支持 **桌面端** 和 **安卓端** 的围棋对弈软件，可以本地与 Katago AI 对弈。

- 🖥️ 桌面版：Python + Tkinter
- 📱 安卓版：Python + Kivy（可打包为 APK）

---

## 功能特点

- 🎮 完整围棋规则（落子、提子、劫争、禁着点、双停终局）
- 🤖 集成 Katago 引擎，支持 AI 对弈
- 🎨 精美棋盘界面，坐标显示、最后落子标记
- ⏪ 悔棋功能（连接 AI 时一次悔两步）
- 📊 实时显示提子数、手数、当前执子方
- ⚖️ 数目法计算胜负
- 🔄 切换执子颜色
- ⚙️ 可配置棋盘大小（9/13/19路）、贴目、分析线程数

---

## 文件结构

```
.
├── main.py              # 桌面版入口 (Tkinter)
├── main_kivy.py         # 安卓版入口 (Kivy)
├── go_board.py          # 围棋核心规则（通用）
├── katago_engine.py     # Katago GTP 协议通信（通用）
├── gui.py               # 桌面版 GUI (Tkinter)
├── config.py            # 配置管理（通用）
├── android_utils.py     # 安卓平台工具函数
├── buildozer.spec       # 安卓打包配置
├── test_go_board.py     # 单元测试
├── config.json          # 用户配置（自动生成）
└── README.md
```

---

## 📱 安卓版使用说明

### 方式一：直接运行（需安装 Kivy）

```bash
pip install kivy
python3 main_kivy.py
```

### 方式二：打包为 APK（推荐）

使用 Buildozer 打包成安卓 APK：

#### 1. 安装 Buildozer

```bash
pip install buildozer
```

Linux 环境还需要安装依赖：
```bash
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf \
    libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev
```

#### 2. 准备 Katago 安卓二进制文件

Katago 需要 Android 版本的二进制文件才能在手机上运行。

**获取 Katago 安卓版本：**
- 从 Katago 官方 release 下载 Android 版本：https://github.com/lightvector/KataGo/releases
- 或自行使用 Android NDK 交叉编译

**放置文件：**
在项目目录下创建 `assets/katago/` 文件夹，放入：
```
assets/katago/
├── katago              # Katago 可执行文件 (arm64-v8a)
├── model.bin.gz        # 神经网络权重文件
└── default_gtp.cfg     # 配置文件（可选）
```

**修改 `buildozer.spec`：**
```
source.include_patterns = assets/*
```

#### 3. 打包 APK

```bash
buildozer android debug
```

首次打包需要下载 Android SDK/NDK，耗时较长。打包完成后，APK 文件在 `bin/` 目录下。

#### 4. 安装到手机

```bash
adb install bin/gogame-1.0-arm64-v8a-debug.apk
```

### 安卓版设置 Katago 路径

1. 安装并打开 APP
2. 点击右下角「设置」按钮
3. 在「Katago 路径」中填入 Katago 二进制文件的绝对路径
   - 如果已打包到 assets 中，APP 启动时会自动复制到内部存储
   - 通常路径为：`/data/data/org.example.gogame/files/katago/katago`
4. 填入模型路径和配置路径
5. 点击「保存」
6. 点击「连接AI」按钮开始对弈

---

## 🖥️ 桌面版使用说明

### 运行

```bash
python3 main.py
```

### 配置 Katago

1. 点击右侧「引擎设置」
2. 设置 Katago 可执行文件路径
3. （可选）设置配置文件和权重模型路径
4. 点击「确定」
5. 点击「连接引擎」

---

## 操作说明

| 按钮 | 功能 |
|------|------|
| 新局 | 重新开始对局 |
| 悔棋 | 悔一步棋（连AI时悔两步） |
| 停一手 | 弃权一手 |
| 认输 | 投降认输 |
| 计算 | 计算当前比分 |
| 换边 | 交换黑白方 |
| 连接AI | 连接/断开 Katago 引擎 |
| 设置 | 配置路径、棋盘大小等 |

---

## 运行测试

```bash
python3 test_go_board.py -v
```

---

## 技术栈

| 模块 | 技术 |
|------|------|
| 核心规则 | 纯 Python 实现 |
| 桌面 GUI | Tkinter（标准库） |
| 安卓 GUI | Kivy 2.x |
| 引擎通信 | GTP (Go Text Protocol) |
| 打包工具 | Buildozer |
| 规则 | 中国规则（数目法） |

---

## 常见问题

### Q: 安卓上连接 Katago 失败？

A: 请检查：
1. Katago 二进制是 arm64-v8a 架构的
2. 文件有可执行权限
3. 路径填写正确
4. 模型文件路径正确

### Q: AI 思考太慢？

A: 手机端建议：
- 使用较小的权重模型（如 20 块网络）
- 分析线程数设为 2-4
- 使用 9 路或 13 路棋盘

### Q: 支持让子棋吗？

A: 当前版本暂不支持，后续更新中会加入。

---

## License

MIT License
