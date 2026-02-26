# Xense ROS 时间戳发布模块

自动扫描并管理2或4个Xense传感器，发布时间戳并保存Rectify图像供离线处理，与数据采集代码解偶。

## 功能特点

| 功能 | 说明 |
|------|------|
|  **自动扫描** | 自动检测 USB 连接的 Xense 传感器（最多 4 个） |
|  **智能配对** | 支持 2/4 传感器自动配对，区分左右位置 |
|  **时间戳发布** | 通过 ROS 发布传感器时间戳（`std_msgs/Header`） |
|  **Rectify 图像保存** | 保存原始字节数据（.raw），高性能写盘 |
|  **Rectify 话题发布** | 可选发布 Rectify 图像到 ROS 话题（`--publish-rectify`） |
|  **异步写盘** | 阻塞队列 + 写盘线程，避免 IO 阻塞和轮询开销 |
|  **可配置队列缓冲** | 队列大小 = 发布频率 × 缓冲时间（默认 60 秒） |
|  **离线处理支持** | 自动导出时间戳和运行时配置，支持批量后处理 |
|  **可视化工具** | 提供力数据可视化脚本，支持导出视频 |

## 项目结构

```
XENSE_ROS/
├── src/
│   ├── __init__.py
│   ├── main.py                   # 主入口：扫描传感器，启动发布
│   ├── xense_manager.py          # 管理器：管理多个传感器和发布器
│   ├── xense_sensor.py           # 传感器封装：连接和数据读取
│   ├── base_publisher.py         # 发布器基类：定义发布接口
│   ├── timestamp_publisher.py    # 时间戳发布器：发布时间戳+保存图像
│   ├── scan_utils.py             # 扫描工具：传感器配对与检测
│   └── config/                   # 配置文件目录
│       └── scan_result.json      # 传感器配对结果
├── script/                       # 离线处理脚本
│   ├── process_raw.py            # 批量处理raw数据，导出原始.npy和力数据.npz（可选导出可视化PNG）
│   ├── visualize_force_video.py  # 可视化力数据并导出视频（全局固定色标）
│   ├── calc_raw_fps.py           # 帧率与数据质量检测（丢帧/时间戳异常）
│   ├── read_timestamps.py        # 读取并打印timestamps.npy
│   ├── read_force_npz.py         # 读取force_data.npz结构和示例
│   └── print_force_npz_timestamps.py  # 打印力数据时间戳
├── sdk_install/                  # SDK安装脚本
│   └── ubuntu_install.sh         # Ubuntu udev规则安装脚本
├── data/                         # 数据保存目录（自动创建）
│   └── YYYYMMDD_HHMMSS/          # 按session时间戳组织
│       └── {sensor_id}/          # 按传感器ID组织
├── README.md                     # 本文档
└── SDK_README.md                 # SDK官方文档
```

## 快速开始

**前提** ：严格按照 [xense sdk](SDK_README.md) 的安装文档进行安装，以官方文档为准。 <br> 单个FastUMI对应两个xense传感器，最多支持4个传感器（2个FastUMI），请确保已正确连接并配对传感器。
<br>**测试环境**：Ubuntu 20.04 + Python 3.9 + NVIDIA RTX 5060 + ros noetic， conda环境：xenseenv (环境来自于sdk安装文档， 测试环境中sdk版本为 1.7.0)

### 1. 安装依赖

```bash
# 首次使用需要配置udev规则（在ubuntu环境下初次安装 `>=1.6.7` 的xensesdk时，先执行下方脚本才能正常使用），此脚本来自于官方文档，若已配置过则可跳过
cd path/to/XENSE_ROS/sdk_install
sudo ./ubuntu_install.sh
# 重启电脑
```

### 2. 扫描传感器

```bash
conda activate xenseenv

# 仅扫描，查看连接的传感器，并根据提示完成配对，生成配对成功后的json文件，用于后续数采代码读取，若不需要采集，则可跳过此步骤
# 配对逻辑：
#       1）若扫描到两个xense传感器，在提示  “>>> 开始检测！请间断性按压左边传感器！ <<<”  后间断性按压传感器，自动判断变化量更大的一边为左边，另一个则为右边，完成配对
#       2）若扫描到四个xense传感器，则分为两组。先配对第一组，大致流程同上，按压顺序为：第一组左边、第一组右边、第二组左边，余下的一个则为第二组右边，即完成配对，后续手动填入 xv_serial 即可
python3 src/main.py --scan-only
```

### 3. 启动发布

```bash
# 终端1：启动roscore
roscore

# 终端2：启动传感器
conda activate xenseenv
source /opt/ros/noetic/setup.bash
# 进入至本项目目录
cd /path/to/XENSE_ROS

# 自动扫描并启动所有传感器
python3 src/main.py
```

## 命令行参数

| 参数 | 说明 | 用途 |
|------|------|------|
| `--scan-only` | 仅扫描传感器，不启动发布 | 扫描已连接的传感器 |
| `--rate` | 发布频率(Hz)，默认60 | 控制频率 |
| `--no-save-rectify` | 不保存Rectify图像 | 只发布时间戳 |
| `--publish-rectify` | 发布Rectify话题（包含图像和时间戳），自动禁用图像保存 | 发布rectify图像，但不保存在本地，用于 rviz 可视化 |
| `--save-dir` | 保存目录，默认为 `data/` | 设置目录 |

## 用法

性能最佳实践：只发布时间戳，用于多模态数采对齐；不发布图像，但图像保存在本地，用于后续离线处理

> 注意：当前实现中，时间戳和图像话题使用**传感器序列号**命名。

```
# 默认行为：只发布时间戳，不发布图像话题，且raw保存到本地，用于数采
python3 src/main.py
```

```
# 默认行为：发布图像话题，不保存到本地，用于 rviz 等可视化
python3 src/main.py --publish-rectify
```

```
# 默认行为：只发布时间戳，不发布图像不本地保存，用于在数采代码中调试时间戳对齐
python3 src/main.py --no-save-rectify
```

## 输出

### ROS话题

每个传感器发布话题：
- `/{sensor_id}/timestamp` (std_msgs/Header) - 时间戳
- `/{sensor_id}/rectify` (sensor_msgs/Image) - Rectify图像（仅 `--publish-rectify` 模式）
- 例如：`/OG000276/timestamp`、`/OG000276/rectify`
- ...最多4个传感器

### 保存的文件

程序关闭时自动保存到 `data/{session_timestamp}/{sensor_id}/` 目录：

```
data/
└── 20260121_143025/              # 本次采集的session目录（启动时间戳）
    ├── OG000276/                 # 设备ID命名的文件夹
    │   ├── 000000_1768981234.567890.raw  # Rectify原始数据 (帧号_时间戳)
    │   ├── 000001_1768981234.600123.raw
    │   ├── ...
    │   ├── timestamps.npy        # 时间戳数组
    │   └── runtime_OG000276      # 运行时配置
    ├── OG000277/                 # 另一个设备
    │   ├── 000000_1768981234.570000.raw
    │   └── ...
    └── ...
```

> 目录结构：`data/{session_YYYYMMDD_HHMMSS}/{sensor_id}/`
> 文件名格式：`{frame_count:06d}_{timestamp}.raw`
> 
> **.raw文件格式**：numpy原始字节，固定结构 shape=(700, 400, 3), dtype=uint8, BGR格式

## 离线处理

### 工作流程概览

```
采集 .raw  ──►  process_raw.py  ──►  原始 .npy + force_data.npz
                     │                       │
                     │ --export-vis-png       │
                     ▼                       ▼
              Rectify/Difference/Depth PNG   visualize_force_video.py ──► output.mp4
```

典型工作流：
1. **采集**：`python3 src/main.py` 获取 `.raw` 文件和 `timestamps.npy`
2. **离线处理**：`process_raw.py` 将 `.raw` 还原为各通道原始数据（`.npy` / `.npz`）
3. **可视化**（可选）：加 `--export-vis-png` 导出图片，再用 `visualize_force_video.py` 合成视频
4. **质检**：用 `calc_raw_fps.py` 检测丢帧/时间戳异常

---

### 脚本详细说明

#### 1. `process_raw.py` — 批量离线处理

将 `.raw` 文件通过 SDK solver 还原为 selectSensorInfo 各通道原始数值， 目前只实现了获取Rectify、Difference、Depth、Force、ForceResultant、ForceNorm 这六个数据，若要获取其余类型数据请查阅 SDK 手册后修改代码获取。

```bash
# 基本用法：只保存原始 .npy 和 force_data.npz
python script/process_raw.py --session-dir data/20260128_170658

# 同时导出可视化 PNG（Rectify/Difference/Depth 图片）
python script/process_raw.py --session-dir data/20260128_170658 --export-vis-png
```

| 参数 | 说明 |
|------|------|
| `--session-dir` | session 目录路径（必选） |
| `--export-vis-png` | 可选：额外导出 Rectify/Difference/Depth 的 PNG 图片 |

**输出文件结构：**

```
data/20260128_170658/OG000276/
├── SensorInfoRaw/                    # 原始数值（直接保存 selectSensorInfo 输出）
│   ├── Rectify/                      # shape=(700,400,3), uint8, BGR
│   │   ├── 000000_1769592964.2512070.npy
│   │   └── ...
│   ├── Difference/                   # shape=(700,400), float
│   │   └── ...
│   └── Depth/                        # shape=(700,400), float, 单位mm
│       └── ...
├── force_data.npz                    # 力数据（包含以下 key）
│   ├── timestamps                    # shape=(N,), 字符串格式的时间戳
│   ├── force                         # shape=(N,35,20,3), 力向量
│   ├── force_resultant               # shape=(N,6), 合力/力矩
│   └── force_norm                    # shape=(N,35,20,3), 归一化力
├── Rectify/                          # 仅 --export-vis-png 时生成
│   ├── 000000_1769592964.2512070.png
│   └── ...
├── Difference/                       # 仅 --export-vis-png 时生成
│   └── ...
└── Depth/                            # 仅 --export-vis-png 时生成（全局 P1-P99 固定色标 JET 伪彩色）
    └── ...
```

> **可视化最佳实践**：Depth PNG 使用全局 P1-P99 分位数固定色标（JET colormap），跨帧颜色可直接比较，避免逐帧归一化导致的跳变。

---

#### 2. `visualize_force_video.py` — 力数据可视化视频

将 Rectify/Difference/Depth 图片与 Force/ForceResultant/ForceNorm 数据合成为六通道并排可视化视频。

**前提**：已使用 `process_raw.py --export-vis-png` 处理过数据。

```bash
# 基本用法
python script/visualize_force_video.py --sensor-dir data/20260128_170658/OG000276

# 自定义输出文件和帧率
python script/visualize_force_video.py --sensor-dir data/20260128_170658/OG000276 --output my_video.mp4 --fps 30
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--sensor-dir` | 单个 sensor 目录路径（必选） | — |
| `--output` | 输出视频文件名 | `output.mp4` |
| `--fps` | 视频帧率 | `60` |

**视频内容**（从左到右六列）：

| 列 | 数据 | 可视化方式 |
|---|------|-----------|
| 1 | Rectify | 原始 BGR 图像 |
| 2 | Difference | 差分图像 |
| 3 | Depth | 深度伪彩色（来自 process_raw.py 的固定色标 PNG） |
| 4 | Force | 力模长 → JET 伪彩色（全局 P1-P99 固定色标） |
| 5 | ForceNorm | Z 分量 → JET 伪彩色（全局 P1-P99 固定色标） |
| 6 | ForceResultant | 6 维条形图（全局 P99 固定刻度） |

> **可视化最佳实践**：Force、ForceNorm、ForceResultant 均使用全局固定色标/刻度（P1-P99 分位数），跨帧可直接比较，避免逐帧归一化放大噪声。

---

#### 3. `calc_raw_fps.py` — 帧率与数据质量检测

分析 `.raw` 文件的时间戳，计算帧率并检测数据质量问题。

```bash
# 基本用法
python script/calc_raw_fps.py --sensor-dir data/20260128_170658/OG000276

# 指定期望帧率，估算丢帧数
python script/calc_raw_fps.py --sensor-dir data/20260128_170658/OG000276 --expected-fps 60

# 调整异常间隔检测灵敏度
python script/calc_raw_fps.py --sensor-dir data/20260128_170658/OG000276 --jitter-mult 3.0
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--sensor-dir` | 传感器文件夹路径（必选） | — |
| `--expected-fps` | 期望帧率，用于估算丢帧 | 不启用 |
| `--jitter-mult` | 异常间隔阈值倍数（interval > 中位数 × 该值） | `2.0` |

**检测项目：**

| 检测项 | 说明 |
|--------|------|
| 时间戳单调性 | 检测时间戳回退或重复 |
| 帧号连续性 | 检测文件名帧号序列是否有间断 |
| 异常大间隔 | 检测帧间隔超过中位数 × `jitter_mult` 的帧 |
| 丢帧估算 | 按 `--expected-fps` 估算丢失帧数 |

**统计输出**：文件总数、帧率、平均/中位/最小/最大/标准差间隔。

---

#### 4. `read_timestamps.py` — 读取时间戳

读取并打印 `timestamps.npy` 的内容。

```bash
python script/read_timestamps.py --npy data/20260128_170658/OG000276/timestamps.npy
```

| 参数 | 说明 |
|------|------|
| `--npy` | `timestamps.npy` 文件路径（必选） |

---

#### 5. `read_force_npz.py` — 查看力数据结构

读取 `force_data.npz` 并打印数据结构和示例值。

```bash
python script/read_force_npz.py --npz data/20260128_170658/OG000276/force_data.npz
```

| 参数 | 说明 |
|------|------|
| `--npz` | `force_data.npz` 文件路径（必选） |

**输出示例**：
```
[Info] 文件 keys: ['timestamps', 'force', 'force_resultant', 'force_norm']
[Info] timestamps shape: (1800,)
[Info] force shape: (1800, 35, 20, 3)
[Info] force_resultant shape: (1800, 6)
[Info] force_norm shape: (1800, 35, 20, 3)
```

---

#### 6. `print_force_npz_timestamps.py` — 打印力数据时间戳

快速查看 `force_data.npz` 中的时间戳列表。

```bash
python script/print_force_npz_timestamps.py
```

> 注：此脚本当前硬编码了文件路径，按需修改脚本中的 `npz_path`。

---

### 还原.raw图像

```python
import numpy as np

# Rectify图像固定格式：shape=(700, 400, 3), dtype=uint8, BGR格式
with open('000000_123456.789.raw', 'rb') as f:
    img = np.frombuffer(f.read(), dtype=np.uint8).reshape(700, 400, 3)
```

### 使用SDK离线处理（原始 API 示例）

```python
from xensesdk import Sensor
import numpy as np
from pathlib import Path

# 加载运行时配置
sensor_solver = Sensor.createSolver("data/20260121_143025/OG000276/runtime_OG000276")

# 处理保存的原始数据
for raw_file in sorted(Path("data/20260121_143025/OG000276").glob("*.raw")):
    # 还原图像
    with open(raw_file, 'rb') as f:
        img = np.frombuffer(f.read(), dtype=np.uint8).reshape(700, 400, 3)
    
    # 获取各种数据类型
    # Rectify、Difference、Depth、Force、ForceResultant、ForceNorm
    diff, depth, force, forceResultant, forceNorm = sensor_solver.selectSensorInfo(
        Sensor.OutputType.Difference,
        Sensor.OutputType.Depth,
        Sensor.OutputType.Force,
        Sensor.OutputType.ForceResultant,
        Sensor.OutputType.ForceNorm,
        rectify_image=img
    )

sensor_solver.release()
```

## SDK参考

详见 [SDK_README.md](SDK_README.md)

## 架构设计

### 启动流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              main.py                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. main()                                                                   │
│     │                                                                        │
│     ├──► 解析命令行参数 (--rate, --save-dir, --scan-only等)                   │
│     │                                                                        │
│     ├──► [--scan-only模式]                                                   │
│     │         │                                                              │
│     │         └──► scan_sensors() ──► Sensor.scanSerialNumber()              │
│     │                    │                                                   │
│     │                    └──► 打印传感器列表并退出                             │
│     │                                                                        │
│     └──► [正常模式]                                                          │
│               │                                                              │
│               ├──► rospy.init_node('xense_timestamp_publisher')              │
│               │                                                              │
│               └──► setup_auto_scan()                                         │
│                         │                                                    │
│                         ├──► scan_sensors()                                  │
│                         │         └──► Sensor.scanSerialNumber()             │
│                         │                                                    │
│                         ├──► XenseManager()  ◄─────────────────────┐         │
│                         │                                          │         │
│                         └──► 循环(1-4个传感器):                     │         │
│                                   │                                │         │
│                                   ├──► manager.add_sensor()        │         │
│                                   │         │                      │         │
│                                   │         └──► XenseSensor()     │         │
│                                   │                   │            │         │
│                                   │                   └──► Sensor.create()   │
│                                   │                                │         │
│                                   └──► manager.add_timestamp_publisher()     │
│                                             │                      │         │
│                                             └──► XenseTimestampPublisher()   │
│                                                                    │         │
│  2. 启动发布循环                                                    │         │
│     │                                                              │         │
│     ├──► [单传感器] manager.start_single_publisher()               │         │
│     │                     └──► publisher.publish_loop()            │         │
│     │                                                              │         │
│     └──► [多传感器] manager.start_all_publishers()                 │         │
│                       └──► 多线程启动每个publisher.publish_loop()   │         │
│                                                                              │
│  3. 关闭流程 (Ctrl+C 或 rospy.shutdown)                                      │
│     │                                                                        │
│     └──► manager.shutdown()                                                  │
│               │                                                              │
│               ├──► 每个publisher.shutdown()                                  │
│               │         ├──► export_timestamps()  ──► 保存 timestamps.npy    │
│               │         └──► export_runtime_config() ──► 保存 runtime_xxx    │
│               │                 (仅在开启Rectify本地保存时导出)               │
│               │                                                              │
│               └──► 每个sensor.release() ──► 释放传感器资源                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 数据流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              运行时数据流                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐                                                          │
│   │ Xense传感器   │ (USB连接，Vendor ID: 3938)                                │
│   │ (硬件设备)    │                                                          │
│   └──────┬───────┘                                                          │
│          │                                                                   │
│          │ USB数据                                                           │
│          ▼                                                                   │
│   ┌──────────────┐                                                          │
│   │  xensesdk    │  Sensor.create() / Sensor.selectSensorInfo()             │
│   │  (Python库)  │                                                          │
│   └──────┬───────┘                                                          │
│          │                                                                   │
│          │ (Rectify图像, TimeStamp)                                          │
│          ▼                                                                   │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                    XenseSensor                                    │      │
│   │  ┌─────────────────────────────────────────────────────────────┐ │      │
│   │  │ get_timestamp_and_rectify()                                  │ │      │
│   │  │   └──► sensor.selectSensorInfo(Rectify, TimeStamp)          │ │      │
│   │  │           └──► return (timestamp, rectify_image)             │ │      │
│   │  └─────────────────────────────────────────────────────────────┘ │      │
│   └──────────────────────────┬───────────────────────────────────────┘      │
│                              │                                               │
│          ┌───────────────────┴───────────────────┐                          │
│          │                                       │                          │
│          ▼                                       ▼                          │
│   ┌──────────────┐                       ┌──────────────┐                   │
│   │  timestamp   │                       │ rectify_img  │                   │
│   │   (float)    │                       │  (ndarray)   │                   │
│   └──────┬───────┘                       └──────┬───────┘                   │
│          │                                      │                           │
│          │                                      │                           │
│          ▼                                      ▼                           │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                  XenseTimestampPublisher                          │      │
│   │  ┌────────────────────────┐    ┌────────────────────────────────┐│      │
│   │  │ _create_message()      │    │ 异步保存图像(raw)                ││      │
│   │  │  └──► Header消息        │    │  └──► write_queue.put()        ││      │
│   │  │       ├─ stamp         │    │       ↓ (写盘线程)              ││      │
│   │  │       ├─ frame_id      │    │  └──► f.write(img.tobytes())   ││      │
│   │  │       └─ seq           │    │       data/{sensor_id}/*.raw    ││      │
│   │  └───────────┬────────────┘    └────────────────────────────────┘│      │
│   │              │                                                   │      │
│   │              │ timestamps列表 ──► shutdown时保存为.npy            │      │
│   │              │                                                   │      │
│   └──────────────┼───────────────────────────────────────────────────┘      │
│                  │                                                          │
│                  ▼                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                         ROS                                       │      │
│   │  ┌────────────────────────────────────────────────────────────┐  │      │
│   │  │ rospy.Publisher(topic_name, Header)                         │  │      │
│   │  │     └──► /{sensor_id}/timestamp                             │  │      │
│   │  │     └──► /{sensor_id}/rectify (可选)                        │  │      │
│   │  │     └──► ...                                                │  │      │
│   │  └────────────────────────────────────────────────────────────┘  │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 类关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              类结构                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │                       XenseManager                               │       │
│   │  ┌───────────────────────────────────────────────────────────┐  │       │
│   │  │ sensors: Dict[str, XenseSensor]     # 传感器字典           │  │       │
│   │  │ publishers: Dict[str, BaseDataPublisher]  # 发布器字典     │  │       │
│   │  ├───────────────────────────────────────────────────────────┤  │       │
│   │  │ + add_sensor(sensor_id, name) -> XenseSensor              │  │       │
│   │  │ + add_timestamp_publisher(...) -> XenseTimestampPublisher │  │       │
│   │  │ + start_all_publishers() -> List[Thread]                  │  │       │
│   │  │ + start_single_publisher(name)                            │  │       │
│   │  │ + shutdown()                                              │  │       │
│   │  │ + get_statistics() -> Dict                                │  │       │
│   │  └───────────────────────────────────────────────────────────┘  │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                    │                              │                         │
│                    │ 管理                         │ 管理                     │
│                    ▼                              ▼                         │
│   ┌────────────────────────┐      ┌────────────────────────────────────┐   │
│   │     XenseSensor        │      │       BaseDataPublisher (抽象类)    │   │
│   │  ┌──────────────────┐  │      │  ┌──────────────────────────────┐  │   │
│   │  │ sensor_id: str   │  │      │  │ sensor: XenseSensor          │  │   │
│   │  │ sensor: Sensor   │  │      │  │ publisher: rospy.Publisher   │  │   │
│   │  │ is_connected     │  │      │  │ publish_rate: float          │  │   │
│   │  ├──────────────────┤  │      │  ├──────────────────────────────┤  │   │
│   │  │ + get_timestamp_ │  │      │  │ + publish_loop()             │  │   │
│   │  │   and_rectify()  │◄─┼──────┼──│ + publish_once()             │  │   │
│   │  │ + release()      │  │      │  │ + _read_data() (抽象)         │  │   │
│   │  │ + export_runtime │  │      │  │ + _create_message() (抽象)    │  │   │
│   │  │   _config()      │  │      │  └──────────────────────────────┘  │   │
│   │  └──────────────────┘  │      └───────────────────┬────────────────┘   │
│   └────────────────────────┘                          │                     │
│                                                       │ 继承                │
│                                                       ▼                     │
│                              ┌────────────────────────────────────────────┐ │
│                              │       XenseTimestampPublisher              │ │
│                              │  ┌──────────────────────────────────────┐  │ │
│                              │  │ timestamps: List[float]              │  │ │
│                              │  │ save_dir: Path                       │  │ │
│                              │  │ save_rectify: bool                   │  │ │
│                              │  │ write_queue: Queue  # 异步写盘队列   │  │ │
│                              │  │ write_thread: Thread # 写盘线程      │  │ │
│                              │  ├──────────────────────────────────────┤  │ │
│                              │  │ + _read_data() -> (timestamp, img)   │  │ │
│                              │  │ + _create_message() -> Header        │  │ │
│                              │  │ + _write_worker()  # 写盘工作线程    │  │ │
│                              │  │ + export_timestamps()                │  │ │
│                              │  │ + shutdown()                         │  │ │
│                              │  └──────────────────────────────────────┘  │ │
│                              └────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

