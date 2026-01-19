#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xense传感器管理器
功能：管理多个传感器实例和对应的发布器
"""

import rospy
from typing import List, Dict, Optional
import sys
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from xense_sensor import XenseSensor
from base_publisher import BaseDataPublisher
from force_publisher import XenseForcePublisher


class XenseManager:
    """
    Xense传感器管理器
    
    负责管理多个传感器实例和对应的数据发布器
    支持动态添加传感器和发布器
    """
    
    def __init__(self):
        """初始化管理器"""
        self.sensors: Dict[str, XenseSensor] = {}
        self.publishers: Dict[str, BaseDataPublisher] = {}
        rospy.loginfo("[XenseManager] 初始化传感器管理器")
    
    def add_sensor(self, sensor_id: Optional[str] = None, name: str = None) -> XenseSensor:
        """
        添加传感器
        
        参数:
            sensor_id: 传感器序列号或ID，如果为None则自动检测
            name: 传感器名称，如果为None则使用sensor_id或自动生成
        
        返回:
            XenseSensor: 传感器实例
        """
        # 生成传感器名称
        if name is None:
            if sensor_id:
                name = f"xense_{sensor_id}"
            else:
                # 自动生成名称
                existing_count = len(self.sensors)
                name = f"xense_{existing_count + 1}"
        
        # 检查名称是否已存在
        if name in self.sensors:
            rospy.logwarn(f"[XenseManager] 传感器名称 '{name}' 已存在，将覆盖")
        
        # 创建传感器实例
        try:
            sensor = XenseSensor(sensor_id=sensor_id, name=name)
            self.sensors[name] = sensor
            rospy.loginfo(f"[XenseManager] 已添加传感器: {name} (ID: {sensor.sensor_id})")
            return sensor
        except Exception as e:
            rospy.logerr(f"[XenseManager] 添加传感器失败: {e}")
            raise
    
    def add_force_publisher(self, sensor_name: str, publish_rate: float = 30.0,
                           topic_name: str = None, frame_id: str = None,
                           use_stamped: bool = True, namespace: str = "") -> XenseForcePublisher:
        """
        为指定传感器添加六维力发布器
        
        参数:
            sensor_name: 传感器名称
            publish_rate: 发布频率（Hz），默认30Hz
            topic_name: ROS话题名称，如果为None则使用默认名称
            frame_id: 坐标系ID，如果为None则使用sensor.name
            use_stamped: 是否使用WrenchStamped消息，默认True
            namespace: ROS命名空间前缀
        
        返回:
            XenseForcePublisher: 发布器实例
        """
        if sensor_name not in self.sensors:
            raise ValueError(f"传感器 '{sensor_name}' 不存在，请先添加传感器")
        
        sensor = self.sensors[sensor_name]
        
        # 生成发布器名称
        publisher_name = f"{sensor_name}_force_publisher"
        
        # 检查是否已存在
        if publisher_name in self.publishers:
            rospy.logwarn(f"[XenseManager] 发布器 '{publisher_name}' 已存在，将覆盖")
        
        # 创建发布器
        try:
            publisher = XenseForcePublisher(
                sensor=sensor,
                publish_rate=publish_rate,
                topic_name=topic_name,
                frame_id=frame_id,
                use_stamped=use_stamped,
                namespace=namespace
            )
            self.publishers[publisher_name] = publisher
            rospy.loginfo(f"[XenseManager] 已添加发布器: {publisher_name}")
            return publisher
        except Exception as e:
            rospy.logerr(f"[XenseManager] 添加发布器失败: {e}")
            raise
    
    def add_custom_publisher(self, sensor_name: str, publisher: BaseDataPublisher,
                            publisher_name: str = None):
        """
        添加自定义发布器
        
        参数:
            sensor_name: 传感器名称
            publisher: 发布器实例（必须是BaseDataPublisher的子类）
            publisher_name: 发布器名称，如果为None则自动生成
        """
        if sensor_name not in self.sensors:
            raise ValueError(f"传感器 '{sensor_name}' 不存在，请先添加传感器")
        
        if not isinstance(publisher, BaseDataPublisher):
            raise TypeError("发布器必须是BaseDataPublisher的子类")
        
        if publisher_name is None:
            publisher_name = f"{sensor_name}_custom_publisher_{len(self.publishers)}"
        
        if publisher_name in self.publishers:
            rospy.logwarn(f"[XenseManager] 发布器 '{publisher_name}' 已存在，将覆盖")
        
        self.publishers[publisher_name] = publisher
        rospy.loginfo(f"[XenseManager] 已添加自定义发布器: {publisher_name}")
    
    def get_sensor(self, name: str) -> Optional[XenseSensor]:
        """获取传感器实例"""
        return self.sensors.get(name)
    
    def get_publisher(self, name: str) -> Optional[BaseDataPublisher]:
        """获取发布器实例"""
        return self.publishers.get(name)
    
    def start_all_publishers(self):
        """启动所有发布器（在单独的线程中）"""
        import threading
        
        if not self.publishers:
            rospy.logwarn("[XenseManager] 没有可启动的发布器")
            return
        
        rospy.loginfo(f"[XenseManager] 启动 {len(self.publishers)} 个发布器...")
        
        threads = []
        for name, publisher in self.publishers.items():
            thread = threading.Thread(
                target=publisher.publish_loop,
                name=f"publisher_{name}",
                daemon=True
            )
            thread.start()
            threads.append(thread)
            rospy.loginfo(f"[XenseManager] 已启动发布器: {name}")
        
        return threads
    
    def start_single_publisher(self, publisher_name: str):
        """启动单个发布器（阻塞）"""
        if publisher_name not in self.publishers:
            raise ValueError(f"发布器 '{publisher_name}' 不存在")
        
        publisher = self.publishers[publisher_name]
        publisher.publish_loop()
    
    def shutdown(self):
        """关闭所有传感器和发布器"""
        rospy.loginfo("[XenseManager] 正在关闭所有传感器...")
        
        # 释放所有传感器资源
        for name, sensor in self.sensors.items():
            try:
                sensor.release()
                rospy.loginfo(f"[XenseManager] 已关闭传感器: {name}")
            except Exception as e:
                rospy.logwarn(f"[XenseManager] 关闭传感器 {name} 时出错: {e}")
        
        self.sensors.clear()
        self.publishers.clear()
        rospy.loginfo("[XenseManager] 所有传感器已关闭")
    
    def get_statistics(self) -> Dict:
        """
        获取所有传感器和发布器的统计信息
        
        返回:
            dict: 统计信息字典
        """
        stats = {
            'sensors': {},
            'publishers': {}
        }
        
        for name, sensor in self.sensors.items():
            stats['sensors'][name] = {
                'sensor_id': sensor.sensor_id,
                'is_connected': sensor.is_connected
            }
        
        for name, publisher in self.publishers.items():
            stats['publishers'][name] = publisher.get_statistics()
        
        return stats
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()
        return False
    
    def __del__(self):
        """析构函数"""
        self.shutdown()

