# Xense ROS Force 发布模块

一个规范的、可扩展的ROS模块，用于发布Xense传感器的六维力数据。

## 📋 目录

- [功能特点](#功能特点)
- [项目结构](#项目结构)
- [架构设计](#架构设计)
- [快速开始](#快速开始)
- [配置文件说明](#配置文件说明)
- [编程接口](#编程接口)
- [ROS话题和消息](#ros话题和消息)
- [参数说明](#参数说明)
- [依赖要求](#依赖要求)
- [故障排除](#故障排除)
- [代码示例](#代码示例)
- [扩展指南](#扩展指南)
- [未来扩展计划](#未来扩展计划)

## 📋 功能特点

- ✅ **模块化设计**：清晰的类层次结构，易于维护和扩展
- ✅ **多传感器支持**：可同时管理多个传感器实例（目前支持1个，未来可扩展到4个或更多）
- ✅ **可扩展架构**：方便添加其他数据类型（深度、图像、标记等）
- ✅ **配置灵活**：支持JSON配置文件、ROS参数服务器或命令行参数
- ✅ **资源管理**：自动管理传感器连接和资源释放
- ✅ **上下文管理器**：支持Python上下文管理器，确保资源正确释放
- ✅ **多线程支持**：支持多传感器多发布器的并发发布

## 📁 项目结构

```
XENSE_ROS/
├── src/                          # 源代码目录
│   ├── __init__.py              # 包初始化文件
│   ├── xense_sensor.py          # 传感器基础封装类
│   ├── base_publisher.py        # 数据发布器基类（抽象类）
│   ├── force_publisher.py       # 六维力数据发布器
│   ├── xense_manager.py         # 传感器管理器（管理多个传感器）
│   ├── config.py                # 配置管理模块
│   └── main.py                  # 主启动脚本
├── config/                       # 配置文件目录
│   └── xense_config.json        # 默认配置文件
├── launch/                       # ROS launch文件目录
│   └── xense_force.launch       # ROS launch文件
├── start_xense_launch.sh        # 启动脚本（自动环境配置）
├── example_usage.py             # 使用示例脚本
├── QUICKSTART.md                # 快速开始指南
└── README.md                    # 本文档
```

## 🏗️ 架构设计

### 类层次结构

```
XenseSensor (传感器封装)
    └── 负责传感器连接、数据读取、资源管理
        ├── 自动传感器扫描和连接
        ├── 六维力数据读取
        ├── 传感器校准功能
        └── 资源自动释放

BaseDataPublisher (抽象基类)
    └── 定义发布器的通用接口
        ├── 发布循环管理
        ├── 消息创建接口
        └── 统计信息收集
        ├── XenseForcePublisher (六维力发布器)
        │   └── 发布 geometry_msgs/WrenchStamped 或 Wrench
        └── [未来可添加] XenseDepthPublisher
        └── [未来可添加] XenseImagePublisher
        └── [未来可添加] 其他数据发布器...

XenseManager (管理器)
    └── 管理多个传感器和发布器实例
        ├── 传感器生命周期管理
        ├── 发布器注册和管理
        ├── 多线程发布支持
        └── 统一资源释放
```

### 设计原则

1. **单一职责**：每个类只负责一个明确的功能
2. **开闭原则**：对扩展开放，对修改关闭（通过基类和接口）
3. **依赖倒置**：高层模块不依赖低层模块，都依赖抽象
4. **资源管理**：使用上下文管理器确保资源正确释放
5. **配置驱动**：通过配置文件灵活配置传感器和发布器

## 🚀 快速开始

### 前置要求

1. **ROS环境**：确保已安装ROS（Noetic/Melodic/Foxy等）
2. **Python环境**：Python 3.6+，推荐使用conda环境
3. **Xense SDK**：已安装xensesdk Python包
4. **传感器连接**：Xense传感器已通过USB连接

### 方式1：使用启动脚本（推荐）

启动脚本会自动处理环境配置，是最简单的使用方式：

```bash
cd /home/lumos/XENSE_TESE/XENSE_ROS

# 在新终端窗口中启动（自动激活conda环境）
./start_xense_launch.sh

# 指定传感器ID
./start_xense_launch.sh --sensor-id OG000266

# 指定发布频率
./start_xense_launch.sh --rate 50

# 在当前终端运行（不在新窗口）
./start_xense_launch.sh --no-new-terminal

# 在后台运行
./start_xense_launch.sh --background

# 查看帮助
./start_xense_launch.sh --help
```

**启动脚本功能**：
- ✅ 自动在新终端窗口中启动
- ✅ 自动激活conda环境 `xenseenv39`
- ✅ 自动设置ROS环境
- ✅ 自动检查并安装ROS Python依赖
- ✅ 自动检查roscore状态
- ✅ 彩色输出，易于查看

### 方式2：直接运行Python脚本

```bash
# 终端1：启动ROS核心（如果还没有运行）
roscore

# 终端2：激活环境并运行
conda activate xenseenv39
source /opt/ros/noetic/setup.bash  # 根据你的ROS版本调整

cd /home/lumos/XENSE_TESE/XENSE_ROS
python3 src/main.py
```

### 方式3：使用ROS Launch文件

```bash
# 使用默认配置
roslaunch launch/xense_force.launch

# 指定传感器ID
roslaunch launch/xense_force.launch sensor_id:=OG000266

# 指定发布频率
roslaunch launch/xense_force.launch rate:=50.0

# 使用配置文件
roslaunch launch/xense_force.launch config:=$(rospack find xense_ros)/config/xense_config.json
```

### 查看发布的数据

在另一个终端中：

```bash
# 查看话题列表
rostopic list

# 查看话题信息
rostopic info /xense_1/force

# 实时查看数据
rostopic echo /xense_1/force

# 查看发布频率
rostopic hz /xense_1/force

# 查看消息类型
rostopic type /xense_1/force
```

## 📝 配置文件说明

### 配置文件格式（JSON）

配置文件位于 `config/xense_config.json`，格式如下：

```json
{
    "sensors": [
        {
            "name": "xense_1",
            "sensor_id": null,
            "publishers": [
                {
                    "type": "force",
                    "publish_rate": 30.0,
                    "topic_name": null,
                    "frame_id": null,
                    "use_stamped": true,
                    "namespace": ""
                }
            ]
        }
    ],
    "global": {
        "default_publish_rate": 30.0,
        "default_frame_id": "xense_sensor",
        "default_use_stamped": true
    }
}
```

### 配置字段说明

#### 传感器配置 (`sensors`)

- `name` (必需): 传感器名称，用于标识和日志输出
- `sensor_id` (可选): 传感器序列号或ID，`null` 表示自动检测第一个可用传感器
- `publishers` (必需): 发布器配置列表

#### 发布器配置 (`publishers`)

- `type` (必需): 发布器类型，目前支持 `"force"`
- `publish_rate` (可选): 发布频率（Hz），默认30Hz
- `topic_name` (可选): ROS话题名称，`null` 表示使用默认名称 `/{sensor_name}/force`
- `frame_id` (可选): 坐标系ID，`null` 表示使用传感器名称
- `use_stamped` (可选): 是否使用WrenchStamped消息（带时间戳），默认true
- `namespace` (可选): ROS命名空间前缀，用于区分多个传感器

#### 全局配置 (`global`)

- `default_publish_rate`: 默认发布频率（Hz）
- `default_frame_id`: 默认坐标系ID
- `default_use_stamped`: 默认是否使用时间戳

### 多传感器配置示例

```json
{
    "sensors": [
        {
            "name": "xense_1",
            "sensor_id": "OG000266",
            "publishers": [
                {
                    "type": "force",
                    "publish_rate": 30.0,
                    "topic_name": "/sensor1/force",
                    "frame_id": "sensor1_frame",
                    "use_stamped": true,
                    "namespace": "sensor1"
                }
            ]
        },
        {
            "name": "xense_2",
            "sensor_id": "OG000267",
            "publishers": [
                {
                    "type": "force",
                    "publish_rate": 50.0,
                    "topic_name": "/sensor2/force",
                    "frame_id": "sensor2_frame",
                    "use_stamped": true,
                    "namespace": "sensor2"
                }
            ]
        }
    ],
    "global": {
        "default_publish_rate": 30.0,
        "default_frame_id": "xense_sensor",
        "default_use_stamped": true
    }
}
```

### 使用配置文件

```bash
# 使用指定配置文件
python3 src/main.py --config config/xense_config.json

# 从ROS参数服务器加载
python3 src/main.py --use-rosparam
```

## 💻 编程接口

### 方式1：使用管理器（推荐）

管理器提供了统一的接口来管理多个传感器和发布器：

```python
#!/usr/bin/env python3
import rospy
import sys
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from xense_manager import XenseManager

rospy.init_node('my_xense_node')

# 创建管理器
manager = XenseManager()

# 添加传感器
sensor1 = manager.add_sensor(sensor_id="OG000266", name="xense_1")

# 添加六维力发布器
publisher1 = manager.add_force_publisher(
    sensor_name="xense_1",
    publish_rate=30.0,
    topic_name="/sensor1/force",
    frame_id="sensor1_frame"
)

# 启动发布（阻塞）
manager.start_single_publisher("xense_1_force_publisher")
```

### 方式2：使用上下文管理器（推荐）

使用上下文管理器可以确保资源正确释放：

```python
#!/usr/bin/env python3
import rospy
from xense_manager import XenseManager

rospy.init_node('my_xense_node')

# 使用上下文管理器
with XenseManager() as manager:
    manager.add_sensor(name="xense_1")
    manager.add_force_publisher("xense_1")
    manager.start_single_publisher("xense_1_force_publisher")
```

### 方式3：直接使用类（简单场景）

对于简单的单传感器场景，可以直接使用类：

```python
#!/usr/bin/env python3
import rospy
from xense_sensor import XenseSensor
from force_publisher import XenseForcePublisher

rospy.init_node('my_xense_node')

# 创建传感器
sensor = XenseSensor(sensor_id="OG000266", name="xense_1")

# 创建发布器
publisher = XenseForcePublisher(
    sensor=sensor,
    publish_rate=30.0,
    topic_name="/xense/force"
)

# 启动发布循环
publisher.publish_loop()
```

### 方式4：多传感器多线程发布

```python
#!/usr/bin/env python3
import rospy
from xense_manager import XenseManager

rospy.init_node('multi_xense_node')

manager = XenseManager()

# 添加多个传感器
for i in range(1, 3):
    sensor_name = f"xense_{i}"
    manager.add_sensor(name=sensor_name)
    manager.add_force_publisher(
        sensor_name=sensor_name,
        topic_name=f"/sensor{i}/force",
        namespace=f"sensor{i}"
    )

# 启动所有发布器（多线程）
threads = manager.start_all_publishers()

# 主线程等待ROS关闭信号
rospy.spin()

# 清理资源
manager.shutdown()
```

## 📊 ROS话题和消息

### 六维力数据

- **话题名称**: `/{sensor_name}/force` (默认: `/xense_1/force`)
- **消息类型**: `geometry_msgs/WrenchStamped` 或 `geometry_msgs/Wrench`
- **数据内容**:
  - `force.x, force.y, force.z`: 力分量 (N)
  - `torque.x, torque.y, torque.z`: 力矩分量 (N·m)

### WrenchStamped消息结构

```python
std_msgs/Header header
  uint32 seq
  time stamp
  string frame_id
geometry_msgs/Wrench wrench
  geometry_msgs/Vector3 force
    float64 x  # Fx (N)
    float64 y  # Fy (N)
    float64 z  # Fz (N)
  geometry_msgs/Vector3 torque
    float64 x  # Mx (N·m)
    float64 y  # My (N·m)
    float64 z  # Mz (N·m)
```

### Wrench消息结构（无时间戳）

```python
geometry_msgs/Wrench wrench
  geometry_msgs/Vector3 force
    float64 x  # Fx (N)
    float64 y  # Fy (N)
    float64 z  # Fz (N)
  geometry_msgs/Vector3 torque
    float64 x  # Mx (N·m)
    float64 y  # My (N·m)
    float64 z  # Mz (N·m)
```

### 查看数据

```bash
# 查看话题列表
rostopic list

# 查看话题信息
rostopic info /xense_1/force

# 实时查看数据
rostopic echo /xense_1/force

# 查看发布频率
rostopic hz /xense_1/force

# 查看消息类型
rostopic type /xense_1/force

# 查看消息定义
rosmsg show geometry_msgs/WrenchStamped
```

## 🛠️ 参数说明

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--config` | string | None | 配置文件路径（JSON格式） |
| `--use-rosparam` | flag | False | 从ROS参数服务器加载配置 |
| `--sensor-id` | string | None | 传感器序列号或ID（简单模式），如果不指定则自动检测 |
| `--rate` | float | 30.0 | 发布频率（Hz） |
| `--frame-id` | string | None | 坐标系ID，默认使用传感器名称 |
| `--topic-name` | string | None | ROS话题名称，默认使用 `/{sensor_name}/force` |
| `--no-stamped` | flag | False | 使用Wrench消息而不是WrenchStamped（不带时间戳） |

### ROS参数（通过launch文件或rosparam设置）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `~config` | string | None | 配置文件路径 |
| `~use_rosparam` | bool | False | 是否从ROS参数服务器加载 |
| `~sensor_id` | string | None | 传感器ID |
| `~rate` | float | 30.0 | 发布频率 |
| `~frame_id` | string | None | 坐标系ID |
| `~topic_name` | string | None | 话题名称 |
| `~no_stamped` | bool | False | 是否不使用时间戳 |

### 参数优先级

1. ROS参数服务器（最高优先级）
2. 命令行参数
3. 配置文件
4. 默认值（最低优先级）

## 📦 依赖要求

### Python依赖

- Python 3.6+
- xensesdk（Xense传感器SDK）
- rospy（ROS Python客户端库）
- geometry_msgs（ROS消息包）
- std_msgs（ROS标准消息包）

### 系统依赖

- ROS（Noetic/Melodic/Foxy等）
- Linux系统（推荐Ubuntu）

### 安装依赖

```bash
# 激活conda环境
conda activate xenseenv39

# 安装ROS Python依赖
pip install pyyaml rospkg catkin_pkg

# 安装Xense SDK（根据实际情况）
# pip install xensesdk
```

## 🔍 故障排除

### 1. 找不到传感器

**错误信息**：
```
错误：未找到可用的传感器！
```

**解决方案**:
- 检查传感器是否已通过USB连接
- 检查USB连接是否稳定
- 运行以下代码查看可用传感器：
  ```python
  from xensesdk import Sensor
  sensors = Sensor.scanSerialNumber()
  print(sensors)
  ```
- 检查USB权限（可能需要添加用户到dialout组）

### 2. 导入错误

**错误信息**：
```
ModuleNotFoundError: No module named 'xense_sensor'
```

**解决方案**:
- 确保在正确的Python环境中运行
- 检查PYTHONPATH是否包含src目录：
  ```bash
  export PYTHONPATH=$PYTHONPATH:/home/lumos/XENSE_TESE/XENSE_ROS/src
  ```
- 或使用绝对导入路径（代码中已自动处理）

### 3. ROS话题没有数据

**解决方案**:
- 检查节点是否正在运行: `rosnode list`
- 检查话题是否存在: `rostopic list`
- 检查话题是否有订阅者: `rostopic info /xense_1/force`
- 查看节点日志输出: `rosnode info xense_force_publisher`
- 检查roscore是否运行: `rostopic list`

### 4. ROS环境问题

**错误信息**：
```
ImportError: No module named 'rospy'
```

**解决方案**:
- 确保已source ROS环境：
  ```bash
  source /opt/ros/noetic/setup.bash
  ```
- 在conda环境中安装ROS Python包：
  ```bash
  pip install pyyaml rospkg catkin_pkg
  ```

### 5. 传感器连接失败

**错误信息**：
```
错误：无法连接传感器
```

**解决方案**:
- 检查传感器是否被其他程序占用
- 重启传感器（拔插USB）
- 检查传感器驱动是否正确安装
- 查看系统日志: `dmesg | tail`

### 6. 发布频率不稳定

**解决方案**:
- 降低发布频率（如果设置过高）
- 检查系统负载
- 检查USB带宽是否足够
- 使用 `rostopic hz` 监控实际发布频率

## 📚 代码示例

### 示例1：单传感器简单使用

```python
#!/usr/bin/env python3
import rospy
from xense_manager import XenseManager

rospy.init_node('xense_node')
manager = XenseManager()
manager.add_sensor(name="xense_1")
manager.add_force_publisher("xense_1")
manager.start_single_publisher("xense_1_force_publisher")
```

### 示例2：指定传感器ID和参数

```python
#!/usr/bin/env python3
import rospy
from xense_manager import XenseManager

rospy.init_node('xense_node')
manager = XenseManager()

# 添加传感器并指定ID
manager.add_sensor(sensor_id="OG000266", name="xense_1")

# 添加发布器并指定参数
manager.add_force_publisher(
    sensor_name="xense_1",
    publish_rate=50.0,
    topic_name="/my_force",
    frame_id="base_link"
)

manager.start_single_publisher("xense_1_force_publisher")
```

### 示例3：多传感器配置

```python
#!/usr/bin/env python3
import rospy
from xense_manager import XenseManager

rospy.init_node('multi_xense_node')
manager = XenseManager()

# 添加多个传感器
sensor_ids = ["OG000266", "OG000267"]
for i, sensor_id in enumerate(sensor_ids, 1):
    sensor_name = f"xense_{i}"
    manager.add_sensor(sensor_id=sensor_id, name=sensor_name)
    manager.add_force_publisher(
        sensor_name=sensor_name,
        topic_name=f"/sensor{i}/force",
        namespace=f"sensor{i}",
        frame_id=f"sensor{i}_frame"
    )

# 启动所有发布器（多线程）
threads = manager.start_all_publishers()
rospy.spin()
```

### 示例4：使用上下文管理器

```python
#!/usr/bin/env python3
import rospy
from xense_manager import XenseManager

rospy.init_node('xense_node')

with XenseManager() as manager:
    manager.add_sensor(name="xense_1")
    manager.add_force_publisher("xense_1")
    manager.start_single_publisher("xense_1_force_publisher")
```

### 示例5：直接使用类

```python
#!/usr/bin/env python3
import rospy
from xense_sensor import XenseSensor
from force_publisher import XenseForcePublisher

rospy.init_node('xense_node')

# 使用上下文管理器确保资源释放
with XenseSensor(sensor_id="OG000266", name="xense_1") as sensor:
    publisher = XenseForcePublisher(
        sensor=sensor,
        publish_rate=30.0,
        topic_name="/xense/force"
    )
    publisher.publish_loop()
```

### 示例6：获取统计信息

```python
#!/usr/bin/env python3
import rospy
from xense_manager import XenseManager

rospy.init_node('xense_node')
manager = XenseManager()
manager.add_sensor(name="xense_1")
manager.add_force_publisher("xense_1")

# 获取统计信息
stats = manager.get_statistics()
print("传感器统计:", stats['sensors'])
print("发布器统计:", stats['publishers'])

# 获取单个发布器统计
publisher = manager.get_publisher("xense_1_force_publisher")
if publisher:
    pub_stats = publisher.get_statistics()
    print("发布器详情:", pub_stats)
```

## 🔧 扩展指南

### 添加新的数据类型发布器

#### 1. 创建新的发布器类（继承 `BaseDataPublisher`）

创建文件 `src/depth_publisher.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度数据发布器
"""

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from base_publisher import BaseDataPublisher
from xense_sensor import XenseSensor
from xensesdk import Sensor

class XenseDepthPublisher(BaseDataPublisher):
    """深度数据发布器"""
    
    def __init__(self, sensor: XenseSensor, publish_rate: float = 30.0,
                 topic_name: str = None, frame_id: str = None):
        self.bridge = CvBridge()
        super().__init__(sensor, publish_rate, topic_name, frame_id)
    
    def _get_default_topic_name(self) -> str:
        return f"/{self.sensor.name}/depth"
    
    def _create_publisher(self):
        return rospy.Publisher(self.topic_name, Image, queue_size=10)
    
    def _read_data(self):
        return self.sensor.get_data(Sensor.OutputType.Depth)
    
    def _create_message(self, data):
        if data is None:
            return None
        return self.bridge.cv2_to_imgmsg(data, "mono16")
```

#### 2. 在管理器中添加支持

在 `xense_manager.py` 中添加方法：

```python
def add_depth_publisher(self, sensor_name: str, publish_rate: float = 30.0,
                       topic_name: str = None, frame_id: str = None):
    """添加深度数据发布器"""
    if sensor_name not in self.sensors:
        raise ValueError(f"传感器 '{sensor_name}' 不存在")
    
    sensor = self.sensors[sensor_name]
    publisher_name = f"{sensor_name}_depth_publisher"
    
    from depth_publisher import XenseDepthPublisher
    publisher = XenseDepthPublisher(
        sensor=sensor,
        publish_rate=publish_rate,
        topic_name=topic_name,
        frame_id=frame_id
    )
    
    self.publishers[publisher_name] = publisher
    return publisher
```

#### 3. 更新配置文件

在配置文件中添加新的发布器类型：

```json
{
    "sensors": [
        {
            "name": "xense_1",
            "sensor_id": null,
            "publishers": [
                {
                    "type": "force",
                    "publish_rate": 30.0
                },
                {
                    "type": "depth",
                    "publish_rate": 30.0
                }
            ]
        }
    ]
}
```

#### 4. 更新main.py支持新类型

在 `main.py` 的 `setup_from_config` 函数中添加：

```python
if pub_type == 'force':
    # 六维力发布器
    publisher = manager.add_force_publisher(...)
elif pub_type == 'depth':
    # 深度数据发布器
    publisher = manager.add_depth_publisher(...)
else:
    rospy.logwarn(f"[Main] 未知的发布器类型: {pub_type}，跳过")
```

## 📝 注意事项

1. **资源管理**：使用上下文管理器或确保调用 `shutdown()` 方法释放资源
2. **多传感器**：每个传感器需要不同的名称和话题名称
3. **发布频率**：建议设置为30Hz（传感器默认采样频率），过高可能导致数据丢失
4. **线程安全**：多发布器模式下使用多线程，注意线程安全
5. **传感器校准**：在无物理接触时调用 `sensor.calibrate()` 进行校准
6. **USB连接**：确保USB连接稳定，避免频繁拔插

## 🔮 未来扩展计划

- [ ] 添加深度数据发布器
- [ ] 添加图像数据发布器
- [ ] 添加标记数据发布器
- [ ] 添加3D网格数据发布器
- [ ] 支持ROS2
- [ ] 添加数据记录功能（rosbag）
- [ ] 添加可视化工具（RViz配置）
- [ ] 添加传感器校准工具
- [ ] 添加性能监控和统计
- [ ] 添加单元测试和集成测试

## 📄 许可证

（根据项目实际情况填写）

## 👥 维护者

（根据项目实际情况填写）

## 📞 支持

如有问题或建议，请提交Issue或联系维护者。
