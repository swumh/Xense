#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
六维力数据发布器
功能：发布Xense传感器的六维合力数据
"""

import rospy
from geometry_msgs.msg import Wrench, WrenchStamped
from std_msgs.msg import Header
import sys
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from base_publisher import BaseDataPublisher
from xense_sensor import XenseSensor


class XenseForcePublisher(BaseDataPublisher):
    """
    六维力数据发布器
    
    发布Xense传感器的六维合力数据到ROS话题
    """
    
    def __init__(self, sensor: XenseSensor, publish_rate: float = 30.0,
                 topic_name: str = None, frame_id: str = None, 
                 use_stamped: bool = True, namespace: str = ""):
        """
        初始化六维力发布器
        
        参数:
            sensor: XenseSensor实例
            publish_rate: 发布频率（Hz），默认30Hz
            topic_name: ROS话题名称，如果为None则使用默认名称
            frame_id: 坐标系ID，如果为None则使用sensor.name
            use_stamped: 是否使用WrenchStamped消息（带时间戳），默认True
            namespace: ROS命名空间前缀，用于区分多个传感器
        """
        self.use_stamped = use_stamped
        
        # 设置默认话题名称
        if topic_name is None:
            if namespace:
                topic_name = f"/{namespace}/force"
            else:
                topic_name = f"/{sensor.name}/force"
        
        # 设置默认frame_id
        if frame_id is None:
            frame_id = sensor.name
        
        super().__init__(sensor, publish_rate, topic_name, frame_id)
    
    def _get_default_topic_name(self) -> str:
        """获取默认话题名称"""
        return f"/{self.sensor.name}/force"
    
    def _create_publisher(self):
        """创建ROS发布者"""
        if self.use_stamped:
            pub = rospy.Publisher(self.topic_name, WrenchStamped, queue_size=10)
            rospy.loginfo(f"[{self.sensor.name}] 发布话题: {self.topic_name} (WrenchStamped)")
        else:
            pub = rospy.Publisher(self.topic_name, Wrench, queue_size=10)
            rospy.loginfo(f"[{self.sensor.name}] 发布话题: {self.topic_name} (Wrench)")
        return pub
    
    def _read_data(self):
        """读取六维合力数据"""
        return self.sensor.get_force_resultant()
    
    def _create_message(self, data):
        """
        创建ROS消息
        
        参数:
            data: 六维合力数组 [Fx, Fy, Fz, Mx, My, Mz]
        
        返回:
            WrenchStamped或Wrench消息对象
        """
        if data is None or len(data) < 6:
            rospy.logwarn(f"[{self.sensor.name}] 数据格式错误，跳过本次发布")
            return None
        
        if self.use_stamped:
            msg = WrenchStamped()
            msg.header = Header()
            msg.header.stamp = rospy.Time.now()
            msg.header.frame_id = self.frame_id
            
            # 填充力和力矩数据
            # data格式: [Fx, Fy, Fz, Mx, My, Mz]
            msg.wrench.force.x = float(data[0])
            msg.wrench.force.y = float(data[1])
            msg.wrench.force.z = float(data[2])
            msg.wrench.torque.x = float(data[3])
            msg.wrench.torque.y = float(data[4])
            msg.wrench.torque.z = float(data[5])
        else:
            msg = Wrench()
            msg.force.x = float(data[0])
            msg.force.y = float(data[1])
            msg.force.z = float(data[2])
            msg.torque.x = float(data[3])
            msg.torque.y = float(data[4])
            msg.torque.z = float(data[5])
        
        return msg

