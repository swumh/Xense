#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间戳数据发布器
功能：发布Xense传感器的时间戳数据，同时保存Rectify图像用于离线处理
"""

import rospy
import cv2
import numpy as np
from std_msgs.msg import Header, Float64
from pathlib import Path
import sys
import threading
import queue

# 添加src目录到路径
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from base_publisher import BaseDataPublisher
from xense_sensor import XenseSensor


class XenseTimestampPublisher(BaseDataPublisher):
    """
    时间戳数据发布器
    
    发布Xense传感器的时间戳数据到ROS话题，同时可选保存Rectify图像
    """
    
    def __init__(self, sensor: XenseSensor, publish_rate: float = 30.0,
                 topic_name: str = None, frame_id: str = None, 
                 namespace: str = "", save_rectify: bool = True,
                 save_dir: str = None):
        """
        初始化时间戳发布器
        
        参数:
            sensor: XenseSensor实例
            publish_rate: 发布频率（Hz），默认30Hz
            topic_name: ROS话题名称，如果为None则使用默认名称
            frame_id: 坐标系ID，如果为None则使用sensor.name
            namespace: ROS命名空间前缀，用于区分多个传感器
            save_rectify: 是否保存Rectify图像，默认True
            save_dir: 保存图像的目录，如果为None则使用默认目录
        """
        self.save_rectify = save_rectify
        self.namespace = namespace
        
        # 设置保存目录：使用sensor_id作为子目录名
        if save_dir is None:
            self.save_dir = Path(__file__).parent.parent / "data" / sensor.sensor_id
        else:
            self.save_dir = Path(save_dir) / sensor.sensor_id
        
        # 如果需要保存图像，创建保存目录
        if self.save_rectify:
            self.save_dir.mkdir(parents=True, exist_ok=True)
            rospy.loginfo(f"[{sensor.name}] 图像保存目录: {self.save_dir}")
        
        # 保存时间戳列表（用于导出）
        self.timestamps = []
        
        # 写盘队列和线程
        self.write_queue = queue.Queue()
        self.write_thread_running = True
        self.write_thread = threading.Thread(target=self._write_worker, daemon=True)
        self.write_thread.start()
        
        # 设置默认话题名称
        if topic_name is None:
            if namespace:
                topic_name = f"/{namespace}/timestamp"
            else:
                topic_name = f"/{sensor.name}/timestamp"
        
        # 设置默认frame_id
        if frame_id is None:
            frame_id = sensor.name
        
        super().__init__(sensor, publish_rate, topic_name, frame_id)
    
    def _get_default_topic_name(self) -> str:
        """获取默认话题名称"""
        return f"/{self.sensor.name}/timestamp"
    
    def _write_worker(self):
        """写盘工作线程"""
        while self.write_thread_running or not self.write_queue.empty():
            try:
                # 从队列获取任务，超时1秒
                task = self.write_queue.get(timeout=1.0)
                if task is None:  # 退出信号
                    break
                filename, img = task
                cv2.imwrite(str(filename), img)
                self.write_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                rospy.logwarn(f"[{self.sensor.name}] 写盘失败: {e}")
    
    def _create_publisher(self):
        """创建ROS发布者"""
        # 使用Header消息，包含时间戳和frame_id
        pub = rospy.Publisher(self.topic_name, Header, queue_size=10)
        rospy.loginfo(f"[{self.sensor.name}] 发布话题: {self.topic_name} (Header)")
        return pub
    
    def _read_data(self):
        """
        读取时间戳和Rectify图像
        
        返回:
            tuple: (timestamp, rectify_image) 或 None
        """
        return self.sensor.get_timestamp_and_rectify()
    
    def _create_message(self, data):
        """
        创建ROS消息
        
        参数:
            data: tuple (timestamp, rectify_image)
        
        返回:
            Header消息对象
        """
        if data is None:
            rospy.logwarn(f"[{self.sensor.name}] 数据为空，跳过本次发布")
            return None
        
        timestamp, rectify_img = data
        
        if timestamp is None:
            rospy.logwarn(f"[{self.sensor.name}] 时间戳为空，跳过本次发布")
            return None
        
        # 保存时间戳
        self.timestamps.append(timestamp)
        
        # 保存Rectify图像（异步写盘，SDK每次返回新帧，无需拷贝）
        if self.save_rectify and rectify_img is not None:
            filename = self.save_dir / f"{self.frame_count:06d}_{timestamp}.png"
            self.write_queue.put((filename, rectify_img))
        
        # 创建Header消息
        msg = Header()
        msg.stamp = rospy.Time.from_sec(timestamp)
        msg.frame_id = self.frame_id
        msg.seq = self.frame_count
        
        return msg
    
    def export_timestamps(self, filename: str = None):
        """
        导出时间戳到文件
        
        参数:
            filename: 文件名，如果为None则使用默认名称
        """
        if not self.timestamps:
            rospy.logwarn(f"[{self.sensor.name}] 没有时间戳数据可导出")
            return
        
        if filename is None:
            filename = self.save_dir / "timestamps.npy"
        
        np.save(str(filename), np.array(self.timestamps))
        rospy.loginfo(f"[{self.sensor.name}] 已导出 {len(self.timestamps)} 个时间戳到 {filename}")
    
    def export_runtime_config(self):
        """导出运行时配置"""
        self.sensor.export_runtime_config(self.save_dir)
    
    def get_statistics(self):
        """
        获取发布统计信息
        
        返回:
            dict: 统计信息字典
        """
        stats = super().get_statistics() if hasattr(super(), 'get_statistics') else {}
        stats.update({
            'topic_name': self.topic_name,
            'frame_id': self.frame_id,
            'publish_rate': self.publish_rate,
            'frame_count': self.frame_count,
            'sensor_name': self.sensor.name,
            'save_rectify': self.save_rectify,
            'save_dir': str(self.save_dir),
            'timestamps_count': len(self.timestamps)
        })
        return stats
    
    def shutdown(self):
        """关闭发布器，导出数据"""
        rospy.loginfo(f"[{self.sensor.name}] 正在关闭发布器...")
        
        # 停止写盘线程
        self.write_thread_running = False
        self.write_queue.put(None)  # 发送退出信号
        self.write_thread.join(timeout=5.0)  # 等待写盘线程完成
        
        # 导出时间戳
        self.export_timestamps()
        
        # 导出运行时配置
        if self.save_rectify:
            self.export_runtime_config()
        
        rospy.loginfo(f"[{self.sensor.name}] 发布器已关闭，共发布 {self.frame_count} 帧")
