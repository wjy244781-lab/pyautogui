# 点云可视化工具

一个基于 Open3D 和 Tkinter 的点云可视化工具，用于交互式查看和分析点云数据。

## 功能特性

- 🎨 **3D 点云可视化**：使用 Open3D 进行高质量的三维点云渲染
- 📊 **多帧切换**：支持在不同帧之间快速切换查看
- 🔄 **类型切换**：支持 frame 和 map 两种数据类型的切换
- 👁️ **显示控制**：可单独显示/隐藏 Ground、Plane、Dense Cloud 等不同类型的点云
- 🎯 **点云变换**：支持对点云进行 X/Y/Z 轴偏移变换
- 📝 **Debug 信息**：实时显示 debug.txt 和 match.json 文件内容
- ⌨️ **快捷键支持**：提供便捷的键盘快捷键操作
- 🖱️ **交互式操作**：支持鼠标旋转、缩放、平移视图

## 环境要求

- Python 3.8 或更高版本
- Open3D >= 0.18.0
- NumPy >= 1.21.0
- Tkinter（通常随 Python 一起安装）

## 安装步骤

### 方法一：使用 pip 安装依赖

```bash
# 克隆或下载项目到本地
cd pyguitool

# 安装依赖
pip install -r requirements.txt
```

### 方法二：使用 Conda 环境（推荐）

```bash
# 创建并激活 Conda 环境
conda env create -f environment.yml
conda activate env

# 如果环境已存在，只需激活
conda activate env
```

## 数据目录结构

确保你的数据按照以下结构组织：

```
data/
├── 0/                    # 帧 0
│   ├── frame/           # frame 类型数据
│   │   ├── dense_cloud.ply
│   │   ├── ground_0.ply
│   │   ├── ground_0.json
│   │   ├── plane_0.ply
│   │   ├── plane_0.json
│   │   └── ...
│   └── map/             # map 类型数据
│       ├── dense_cloud.ply
│       ├── ground_*.ply
│       ├── ground_*.json
│       ├── plane_*.ply
│       ├── plane_*.json
│       └── ...
├── 1/                    # 帧 1
│   ├── frame/
│   ├── map/
│   ├── debug.txt         # 可选的调试信息文件
│   └── match.json        # 可选的匹配信息文件
└── ...
```

## 启动程序

### 基本启动

```bash
python main.py
```

### 指定起始帧（在代码中）

如果需要从特定帧开始，可以修改 `main.py`：



## 使用说明

### 界面介绍

程序启动后会打开两个窗口：

1. **控制面板窗口**（Tkinter）：包含所有控制按钮和信息显示
2. **3D 可视化窗口**（Open3D）：显示点云的三维视图

### 基本操作

#### 帧切换

- **上一帧**：点击"上一帧 (←)"按钮，或按键盘 `←` 键
- **下一帧**：点击"下一帧 (→)"按钮，或按键盘 `→` 键

#### 视图控制

- **重置视图**：点击"重置视图"按钮，将视图恢复到初始状态
- **旋转视图**：在 3D 窗口中按住鼠标左键拖动
- **平移视图**：在 3D 窗口中按住鼠标中键（或 Shift + 左键）拖动
- **缩放视图**：在 3D 窗口中滚动鼠标滚轮

#### 点云显示控制

在"点云显示控制"区域，可以控制不同类型点云的显示/隐藏：

- **Ground 点云**：点击按钮切换 Ground 点云的显示/隐藏
- **Plane 点云**：点击按钮切换 Plane 点云的显示/隐藏
- **Dense Cloud 点云**：点击按钮切换 Dense Cloud 点云的显示/隐藏

#### 点云变换

在"变换点云控制"区域，可以调整点云的位置：

- **X 轴偏移**：调整点云在 X 轴方向的偏移量（范围：-1000.0 到 1000.0）
- **Y 轴偏移**：调整点云在 Y 轴方向的偏移量（范围：-1000.0 到 1000.0）
- **Z 轴偏移**：调整点云在 Z 轴方向的偏移量（范围：-1000.0 到 1000.0，默认 10.0）

**提示**：可以使用鼠标滚轮在输入框上滚动来快速调整数值。

#### Debug 信息查看

在右侧面板的"Debug 信息"标签页中，可以查看：

- **debug.txt**：如果当前帧目录下有 `debug.txt` 文件，会显示其内容
- **match.json**：如果当前帧目录下有 `match.json` 文件，会显示其内容

#### Match 信息查看

在右侧面板的"Match 信息"标签页中，可以查看匹配关系信息（如果存在 `match.json` 文件）。

### 快捷键

- `←`：切换到上一帧
- `→`：切换到下一帧
- `R` 或 `r`：重置视图（在 3D 窗口获得焦点时）

### 退出程序

- 点击控制面板中的"退出"按钮
- 或关闭控制面板窗口

## 配置说明

主要配置在 `src/config.py` 文件中，可以调整：

- **窗口大小**：`WINDOW_WIDTH` 和 `WINDOW_HEIGHT`
- **点云大小**：`POINT_SIZE`
- **背景颜色**：`BACKGROUND_COLOR`
- **坐标轴设置**：`COORDINATE_AXIS_ENABLED`、`COORDINATE_AXIS_LENGTH` 等
- **数据目录**：`DATA_DIR`（默认为项目根目录下的 `data` 文件夹）

## 打包成可执行文件

如果需要将项目打包成 Linux 可执行文件，请参考 [BUILD.md](BUILD.md) 文档。

快速开始：
```bash
# 安装打包工具
pip install pyinstaller

# 使用打包脚本（标准模式）
./build_executable.sh

# 或使用单文件模式
./build_executable_onefile.sh
```

打包后的可执行文件位于 `dist/` 目录下。

## 项目结构

```
pyguitool/
├── src/                    # 源代码目录
│   ├── __init__.py
│   ├── config.py          # 配置模块
│   ├── data_loader.py     # 数据加载模块
│   ├── data_classes.py    # 数据类定义
│   ├── dynamic_classes.py # 动态类定义
│   ├── gui.py             # GUI 界面模块
│   └── visualizer.py      # 可视化模块
├── data/                      # 数据目录（需要用户提供）
├── main.py                    # 主程序入口
├── requirements.txt           # Python 依赖
├── environment.yml            # Conda 环境配置
├── BUILD.md                   # 打包说明文档
├── pyguitool.spec             # PyInstaller 配置（单文件模式）
├── pyguitool_dir.spec         # PyInstaller 配置（标准模式）
├── build_executable.sh        # 打包脚本（标准模式）
├── build_executable_onefile.sh # 打包脚本（单文件模式）
└── README.md                  # 本文件
```
