#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件管理
功能：管理传感器和发布器的配置参数
"""

import json
import rospy
from pathlib import Path
from typing import Dict, List, Optional


class XenseConfig:
    """
    Xense配置管理类
    
    支持从JSON文件、ROS参数服务器或代码中加载配置
    """
    
    DEFAULT_CONFIG = {
        "sensors": [
            {
                "name": "xense_1",
                "sensor_id": None,  # None表示自动检测
                "publishers": [
                    {
                        "type": "force",
                        "publish_rate": 30.0,
                        "topic_name": None,  # None表示使用默认名称
                        "frame_id": None,  # None表示使用sensor.name
                        "use_stamped": True,
                        "namespace": ""
                    }
                ]
            }
        ],
        "global": {
            "default_publish_rate": 30.0,
            "default_frame_id": "xense_sensor",
            "default_use_stamped": True
        }
    }
    
    @staticmethod
    def load_from_file(config_path: str) -> Dict:
        """
        从JSON文件加载配置
        
        参数:
            config_path: 配置文件路径
        
        返回:
            dict: 配置字典
        """
        config_file = Path(config_path)
        if not config_file.exists():
            rospy.logwarn(f"[Config] 配置文件不存在: {config_path}，使用默认配置")
            return XenseConfig.DEFAULT_CONFIG.copy()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            rospy.loginfo(f"[Config] 已加载配置文件: {config_path}")
            return config
        except Exception as e:
            rospy.logerr(f"[Config] 加载配置文件失败: {e}，使用默认配置")
            return XenseConfig.DEFAULT_CONFIG.copy()
    
    @staticmethod
    def load_from_rosparam(param_name: str = "~xense_config") -> Dict:
        """
        从ROS参数服务器加载配置
        
        参数:
            param_name: ROS参数名称
        
        返回:
            dict: 配置字典
        """
        try:
            if rospy.has_param(param_name):
                config = rospy.get_param(param_name)
                rospy.loginfo(f"[Config] 已从ROS参数服务器加载配置: {param_name}")
                return config
            else:
                rospy.logwarn(f"[Config] ROS参数 '{param_name}' 不存在，使用默认配置")
                return XenseConfig.DEFAULT_CONFIG.copy()
        except Exception as e:
            rospy.logerr(f"[Config] 从ROS参数服务器加载配置失败: {e}，使用默认配置")
            return XenseConfig.DEFAULT_CONFIG.copy()
    
    @staticmethod
    def merge_configs(*configs: Dict) -> Dict:
        """
        合并多个配置字典
        
        参数:
            *configs: 多个配置字典
        
        返回:
            dict: 合并后的配置字典
        """
        merged = XenseConfig.DEFAULT_CONFIG.copy()
        
        for config in configs:
            if 'sensors' in config:
                merged['sensors'] = config['sensors']
            if 'global' in config:
                merged['global'].update(config['global'])
        
        return merged
    
    @staticmethod
    def validate_config(config: Dict) -> bool:
        """
        验证配置的有效性
        
        参数:
            config: 配置字典
        
        返回:
            bool: 配置是否有效
        """
        if 'sensors' not in config:
            rospy.logerr("[Config] 配置缺少 'sensors' 字段")
            return False
        
        if not isinstance(config['sensors'], list):
            rospy.logerr("[Config] 'sensors' 必须是列表")
            return False
        
        for i, sensor_config in enumerate(config['sensors']):
            if 'name' not in sensor_config:
                rospy.logerr(f"[Config] 传感器配置 {i} 缺少 'name' 字段")
                return False
        
        return True
    
    @staticmethod
    def create_default_config_file(config_path: str):
        """
        创建默认配置文件
        
        参数:
            config_path: 配置文件保存路径
        """
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(XenseConfig.DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        
        rospy.loginfo(f"[Config] 已创建默认配置文件: {config_path}")

