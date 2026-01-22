# Xense ROS 时间戳发布模块

自动扫描并管理1-4个Xense传感器，发布时间戳并保存Rectify图像供离线处理。

## 功能特点

- ✅ **自动扫描**：自动检测USB连接的Xense传感器（最多4个）
- ✅ **时间戳发布**：通过ROS发布传感器时间戳（`std_msgs/Header`）
- ✅ **Rectify图像保存**：保存原始字节数据（.raw），高性能写盘
- ✅ **Rectify话题发布**：可选发布Rectify图像到ROS话题（`--publish-rectify`）
- ✅ **异步写盘**：阻塞队列+写盘线程，避免IO阻塞和轮询开销
- ✅ **可配置队列缓冲**：队列大小 = 发布频率 × 缓冲时间（默认60秒）
- ✅ **离线处理支持**：自动导出时间戳和运行时配置

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
│   │  │ _create_message()      │    │ 异步保存图像                     ││      │
│   │  │  └──► Header消息        │    │  └──► write_queue.put()        ││      │
│   │  │       ├─ stamp         │    │       ↓ (写盘线程)              ││      │
│   │  │       ├─ frame_id      │    │  └──► cv2.imwrite()            ││      │
│   │  │       └─ seq           │    │       data/{name}/xxx_ts.png   ││      │
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
│   │  │     └──► /xense_1/timestamp                                 │  │      │
│   │  │     └──► /xense_2/timestamp                                 │  │      │
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

## 项目结构

```
XENSE_ROS/
├── src/
│   ├── __init__.py
│   ├── main.py                  # 主入口：扫描传感器，启动发布
│   ├── xense_manager.py         # 管理器：管理多个传感器和发布器
│   ├── xense_sensor.py          # 传感器封装：连接和数据读取
│   ├── base_publisher.py        # 发布器基类：定义发布接口
│   └── timestamp_publisher.py   # 时间戳发布器：发布时间戳+保存图像
├── sdk_install/                  # SDK安装脚本
├── data/                         # 数据保存目录（自动创建）
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
# 首次使用需要配置udev规则
cd sdk_install
sudo ./ubuntu_install.sh
# 重启电脑
```

### 2. 扫描传感器

```bash
conda activate xenseenv

# 仅扫描，查看连接的传感器
python3 src/main.py --scan-only
```

### 3. 启动发布

```bash
# 终端1：启动roscore
roscore

# 终端2：启动传感器
conda activate xenseenv
source /opt/ros/noetic/setup.bash
cd /home/sumaohuan/Desktop/XENSE_ROS

# 自动扫描并启动所有传感器
python3 src/main.py
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--scan-only` | 仅扫描传感器，不启动发布 |
| `--rate` | 发布频率(Hz)，默认60 |
| `--no-save-rectify` | 不保存Rectify图像 |
| `--publish-rectify` | 发布Rectify话题（包含图像和时间戳），自动禁用图像保存 |
| `--save-dir` | 保存目录，默认为 `data/` |

## 输出

### ROS话题

每个传感器发布话题：
- `/xense_1/timestamp` (std_msgs/Header) - 时间戳
- `/xense_1/rectify` (sensor_msgs/Image) - Rectify图像（仅 `--publish-rectify` 模式）
- `/xense_2/timestamp` ...
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

### 还原.raw图像

```python
import numpy as np

# Rectify图像固定格式：shape=(700, 400, 3), dtype=uint8, BGR格式
with open('000000_123456.789.raw', 'rb') as f:
    img = np.frombuffer(f.read(), dtype=np.uint8).reshape(700, 400, 3)
```

### 使用SDK离线处理

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
    depth, force, diff = sensor_solver.selectSensorInfo(
        Sensor.OutputType.Depth,
        Sensor.OutputType.Force,
        Sensor.OutputType.Difference,
        rectify_image=img
    )

sensor_solver.release()
```

## 依赖

```bash
pip install xensesdk opencv-python numpy
```

## SDK参考

详见 [SDK_README.md](SDK_README.md)