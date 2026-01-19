#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据发布器基类
功能：定义数据发布器的通用接口和基础功能
"""

import rospy
from abc import ABC, abstractmethod
from typing import Optional
import sys
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from xense_sensor import XenseSensor


class BaseDataPublisher(ABC):
    """
    数据发布器基类（抽象类）
    
    所有具体的数据发布器都应该继承此类
    """
    
    def __init__(self, sensor: XenseSensor, publish_rate: float = 30.0, 
                 topic_name: str = None, frame_id: str = "xense_sensor"):
        """
        初始化发布器
        
        参数:
            sensor: XenseSensor实例
            publish_rate: 发布频率（Hz），默认30Hz
            topic_name: ROS话题名称，如果为None则由子类指定
            frame_id: 坐标系ID，默认"xense_sensor"
        """
        self.sensor = sensor
        self.publish_rate = publish_rate
        self.frame_id = frame_id
        self.topic_name = topic_name or self._get_default_topic_name()
        self.rate = rospy.Rate(publish_rate)
        self.frame_count = 0
        
        # 创建发布者（由子类实现）
        self.publisher = self._create_publisher()
        
        rospy.loginfo(f"[{self.sensor.name}] 初始化发布器: {self.topic_name}, 频率: {publish_rate} Hz")
    
    @abstractmethod
    def _get_default_topic_name(self) -> str:
        """
        获取默认话题名称（由子类实现）
        
        返回:
            str: 默认话题名称
        """
        pass
    
    @abstractmethod
    def _create_publisher(self):
        """
        创建ROS发布者（由子类实现）
        
        返回:
            rospy.Publisher: ROS发布者实例
        """
        pass
    
    @abstractmethod
    def _read_data(self):
        """
        读取传感器数据（由子类实现）
        
        返回:
            传感器数据，如果失败返回None
        """
        pass
    
    @abstractmethod
    def _create_message(self, data):
        """
        创建ROS消息（由子类实现）
        
        参数:
            data: 传感器数据
        
        返回:
            ROS消息对象
        """
        pass
    
    def publish_once(self):
        """
        发布一次数据
        
        返回:
            bool: 是否成功发布
        """
        try:
            # 读取数据
            data = self._read_data()
            if data is None:
                return False
            
            # 创建消息
            msg = self._create_message(data)
            if msg is None:
                return False
            
            # 发布消息
            self.publisher.publish(msg)
            self.frame_count += 1
            
            # 每100帧打印一次（调试用）
            if self.frame_count % 100 == 0:
                rospy.loginfo(f"[{self.sensor.name}] 已发布 {self.frame_count} 帧数据到 {self.topic_name}")
            
            return True
            
        except Exception as e:
            rospy.logerr(f"[{self.sensor.name}] 发布数据时出错: {e}")
            return False
    
    def publish_loop(self):
        """主发布循环"""
        rospy.loginfo(f"[{self.sensor.name}] 开始发布数据到 {self.topic_name}")
        rospy.loginfo(f"[{self.sensor.name}] 按 Ctrl+C 停止")
        
        while not rospy.is_shutdown():
            try:
                self.publish_once()
            except rospy.ROSInterruptException:
                break
            except Exception as e:
                rospy.logerr(f"[{self.sensor.name}] 发布循环出错: {e}")
            
            # 控制发布频率
            self.rate.sleep()
    
    def get_statistics(self):
        """
        获取发布统计信息
        
        返回:
            dict: 统计信息字典
        """
        return {
            'sensor_name': self.sensor.name,
            'sensor_id': self.sensor.sensor_id,
            'topic_name': self.topic_name,
            'frame_id': self.frame_id,
            'publish_rate': self.publish_rate,
            'frames_published': self.frame_count
        }

