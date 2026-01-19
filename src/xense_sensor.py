#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xense传感器基础封装类
功能：封装传感器连接、数据读取等基础操作
"""

import rospy
import sys
from typing import Optional
from xensesdk import Sensor


class XenseSensor:
    """
    Xense传感器封装类
    
    负责传感器的连接、数据读取和资源管理
    """
    
    def __init__(self, sensor_id: Optional[str] = None, name: str = "xense_sensor"):
        """
        初始化传感器
        
        参数:
            sensor_id: 传感器序列号或ID，如果为None则自动检测第一个可用传感器
            name: 传感器名称，用于日志标识
        """
        self.name = name
        self.sensor_id = sensor_id
        self.sensor = None
        self.is_connected = False
        
        # 如果没有指定传感器ID，尝试扫描可用的传感器
        if sensor_id is None:
            rospy.loginfo(f"[{self.name}] 正在扫描可用传感器...")
            try:
                available_sensors = Sensor.scanSerialNumber()
                if not available_sensors:
                    rospy.logerr(f"[{self.name}] 错误：未找到可用的传感器！")
                    raise RuntimeError("未找到可用的传感器")
                self.sensor_id = list(available_sensors.keys())[0]
                rospy.loginfo(f"[{self.name}] 使用传感器: {self.sensor_id}")
            except Exception as e:
                rospy.logerr(f"[{self.name}] 扫描传感器失败: {e}")
                raise
        
        # 创建传感器实例
        self._connect()
    
    def _connect(self):
        """连接传感器"""
        rospy.loginfo(f"[{self.name}] 正在连接传感器 {self.sensor_id}...")
        try:
            self.sensor = Sensor.create(self.sensor_id)
            self.is_connected = True
            rospy.loginfo(f"[{self.name}] 传感器连接成功！")
        except Exception as e:
            rospy.logerr(f"[{self.name}] 错误：无法连接传感器 - {e}")
            self.is_connected = False
            raise
    
    def get_force_resultant(self):
        """
        获取六维合力数据
        
        返回:
            numpy.ndarray: 六维合力数组 [Fx, Fy, Fz, Mx, My, Mz]，如果失败返回None
        """
        if not self.is_connected or self.sensor is None:
            rospy.logwarn(f"[{self.name}] 传感器未连接，无法获取数据")
            return None
        
        try:
            force_resultant = self.sensor.selectSensorInfo(Sensor.OutputType.ForceResultant)
            return force_resultant
        except Exception as e:
            rospy.logerr(f"[{self.name}] 获取六维合力数据失败: {e}")
            return None
    
    def get_data(self, *output_types):
        """
        获取指定类型的传感器数据
        
        参数:
            *output_types: Sensor.OutputType枚举值，可以指定多个类型
        
        返回:
            返回的数据，数量和顺序与输入参数一致
        """
        if not self.is_connected or self.sensor is None:
            rospy.logwarn(f"[{self.name}] 传感器未连接，无法获取数据")
            return None
        
        try:
            return self.sensor.selectSensorInfo(*output_types)
        except Exception as e:
            rospy.logerr(f"[{self.name}] 获取传感器数据失败: {e}")
            return None
    
    def calibrate(self):
        """
        校准传感器（需在无物理接触时调用）
        """
        if not self.is_connected or self.sensor is None:
            rospy.logwarn(f"[{self.name}] 传感器未连接，无法校准")
            return False
        
        try:
            self.sensor.calibrateSensor()
            rospy.loginfo(f"[{self.name}] 传感器校准完成")
            return True
        except Exception as e:
            rospy.logerr(f"[{self.name}] 传感器校准失败: {e}")
            return False
    
    def release(self):
        """释放传感器资源"""
        if self.sensor is not None:
            try:
                self.sensor.release()
                rospy.loginfo(f"[{self.name}] 传感器已断开连接")
            except Exception as e:
                rospy.logwarn(f"[{self.name}] 释放传感器资源时出错: {e}")
            finally:
                self.sensor = None
                self.is_connected = False
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
        return False
    
    def __del__(self):
        """析构函数"""
        self.release()

