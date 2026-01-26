#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xense ROS 时间戳发布 主启动脚本
功能：自动扫描传感器，发布时间戳并保存Rectify图像
"""

import rospy
import sys
import argparse
from pathlib import Path
from datetime import datetime
from xensesdk import Sensor

# 添加src目录到路径
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from xense_manager import XenseManager

# 最大支持的传感器数量
MAX_SENSORS = 4


def scan_sensors() -> dict:
    """
    扫描所有已连接的Xense传感器
    
    返回:
        dict: {序列号: 相机ID} 的映射
    """
    try:
        available_sensors = Sensor.scanSerialNumber()
        return available_sensors if available_sensors else {}
    except Exception as e:
        print(f"[Scan] 扫描传感器失败: {e}")
        return {}


def setup_auto_scan(publish_rate: float = 30.0, save_rectify: bool = True, 
                    save_dir: str = None, publish_rectify: bool = False) -> XenseManager:
    """
    自动扫描并配置所有检测到的传感器（最多4个）
    
    参数:
        publish_rate: 发布频率（Hz）
        save_rectify: 是否保存Rectify图像
        save_dir: 保存图像的目录
        publish_rectify: 是否发布Rectify图像话题
    
    返回:
        XenseManager: 配置好的管理器实例
    """
    # 扫描传感器
    rospy.loginfo("[Main] 正在扫描Xense传感器...")
    available_sensors = scan_sensors()
    
    if not available_sensors:
        rospy.logerr("[Main] 未检测到任何Xense传感器！")
        rospy.logerr("[Main] 请检查：")
        rospy.logerr("[Main]   1. 传感器是否已连接USB")
        rospy.logerr("[Main]   2. 是否已执行 sdk_install/ubuntu_install.sh")
        rospy.logerr("[Main]   3. 运行 lsusb | grep 3938 检查设备")
        sys.exit(1)
    
    # 限制传感器数量
    sensor_count = min(len(available_sensors), MAX_SENSORS)
    sensor_list = list(available_sensors.keys())[:sensor_count]
    
    rospy.loginfo(f"[Main] 检测到 {len(available_sensors)} 个传感器，将使用 {sensor_count} 个")
    for i, sensor_id in enumerate(sensor_list):
        rospy.loginfo(f"[Main]   传感器 {i+1}: {sensor_id}")
    
    # 创建管理器
    manager = XenseManager()
    
    # 为每个传感器创建实例和发布器
    for i, sensor_id in enumerate(sensor_list):
        sensor_name = f"xense_{i+1}"
        
        try:
            # 添加传感器
            sensor = manager.add_sensor(sensor_id=sensor_id, name=sensor_name)
            
            # 添加时间戳发布器
            # 使用序列号作为话题名称
            topic_name = f"/{sensor_id}/timestamp"
            
            manager.add_timestamp_publisher(
                sensor_name=sensor_name,
                publish_rate=publish_rate,
                topic_name=topic_name,
                frame_id=sensor_id,
                save_rectify=save_rectify,
                save_dir=save_dir,
                publish_rectify=publish_rectify
            )
            
            rospy.loginfo(f"[Main] 已配置传感器: {sensor_name} ({sensor_id})")
            
        except Exception as e:
            rospy.logerr(f"[Main] 配置传感器 {sensor_id} 失败: {e}")
            continue
    
    return manager


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Xense时间戳ROS发布节点（自动扫描模式）')
    
    # 参数
    parser.add_argument('--rate', type=float, default=60.0,
                       help='发布频率（Hz），默认60Hz')
    parser.add_argument('--no-save-rectify', action='store_true',
                       help='不保存Rectify图像')
    parser.add_argument('--publish-rectify', action='store_true',
                       help='发布Rectify话题 (包含图像和时间戳)，且不保存图像')
    parser.add_argument('--save-dir', type=str, default=None,
                       help='保存图像的目录，默认为 data/')
    parser.add_argument('--scan-only', action='store_true',
                       help='仅扫描传感器，不启动发布')
    
    # 解析命令行参数
    args, unknown = parser.parse_known_args()
    
    # 仅扫描模式
    if args.scan_only:
        print("\n[Scan] 正在扫描Xense传感器...")
        sensors = scan_sensors()
        if sensors:
            print(f"[Scan] 检测到 {len(sensors)} 个传感器:")
            for i, (serial, cam_id) in enumerate(sensors.items()):
                print(f"  {i+1}. 序列号: {serial}, 相机ID: {cam_id}")
        else:
            print("[Scan] 未检测到任何传感器")
            print("[Scan] 请检查USB连接，或运行: lsusb | grep 3938")
        # 保存为 json 文件
        from scan_utils import save_scan_result_to_json
        save_scan_result_to_json(sensors)
        return
    
    # 初始化ROS节点
    rospy.init_node('xense_timestamp_publisher', anonymous=True)
    
    publish_rate = rospy.get_param('~rate', args.rate)
    publish_rectify = rospy.get_param('~publish_rectify', args.publish_rectify)
    
    # 如果开启发布Rectify，则强制不保存图像
    if publish_rectify:
        save_rectify = False
        rospy.loginfo("[Main] 开启Rectify话题发布，自动禁用图像保存")
    else:
        save_rectify = not rospy.get_param('~no_save_rectify', args.no_save_rectify)
        
    save_dir_base = rospy.get_param('~save_dir', args.save_dir)
    
    # 创建以时间戳命名的session目录
    session_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    if save_dir_base is None:
        save_dir = Path(__file__).parent.parent / "data" / session_time
    else:
        save_dir = Path(save_dir_base) / session_time
    
    rospy.loginfo(f"[Main] 本次采集session目录: {save_dir}")
    
    # 自动扫描并配置传感器
    try:
        manager = setup_auto_scan(
            publish_rate=publish_rate,
            save_rectify=save_rectify,
            save_dir=save_dir,
            publish_rectify=publish_rectify
        )
        
        # 检查是否有可用的传感器
        if not manager.sensors:
            rospy.logerr("[Main] 没有成功配置任何传感器，退出")
            sys.exit(1)
        
        # 打印统计信息
        stats = manager.get_statistics()
        rospy.loginfo(f"[Main] 配置完成:")
        rospy.loginfo(f"  - 传感器数量: {len(stats['sensors'])}")
        rospy.loginfo(f"  - 发布器数量: {len(stats['publishers'])}")
        for name, info in stats['sensors'].items():
            rospy.loginfo(f"  - {name}: {info['sensor_id']}")
            
            # map (xense_id -> sensor_serial)
            # map.append((name, info['sensor_id']))
                
        # 启动发布器
        if len(manager.publishers) == 1:
            # 单个发布器，直接运行
            publisher_name = list(manager.publishers.keys())[0]
            manager.start_single_publisher(publisher_name)
        else:
            # 多个发布器，使用多线程
            threads = manager.start_all_publishers()
            # 主线程等待ROS关闭信号
            rospy.spin()
            
            rospy.loginfo("[Main] 正在停止所有线程...")
            # 等待所有线程结束
            for thread in threads:
                thread.join(timeout=2.0)
    
    except KeyboardInterrupt:
        rospy.loginfo("[Main] 收到停止信号")
    except Exception as e:
        rospy.logerr(f"[Main] 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'manager' in locals():
            manager.shutdown()


if __name__ == '__main__':
    main()

