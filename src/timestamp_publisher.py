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
from sensor_msgs.msg import Image
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
                 save_dir: str = None, publish_rectify: bool = False,
                 queue_buffer_seconds: float = 60.0):
        """
        初始化时间戳发布器
        
        参数:
            sensor: XenseSensor实例
            publish_rate: 发布频率（Hz），默认30Hz
            topic_name: ROS话题名称，如果为None则使用默认名称
            frame_id: 坐标系ID，如果为None则使用sensor.sensor_id
            namespace: ROS命名空间前缀，用于区分多个传感器
            save_rectify: 是否保存Rectify图像，默认True
            save_dir: 保存图像的目录，如果为None则使用默认目录
            publish_rectify: 是否发布Rectify图像，默认False
            queue_buffer_seconds: 写盘队列缓冲时间（秒），默认60秒
        """
        self.save_rectify = save_rectify
        self.publish_rectify = publish_rectify
        self.namespace = namespace

        # 如果开启发布Rectify，初始化相关资源
        if self.publish_rectify:
            # 强制关闭保存
            self.save_rectify = False 
            
            # 创建Rectify图像发布者
            if namespace:
                rectify_topic = f"/{namespace}/rectify"
            else:
                # 使用序列号作为话题名称
                rectify_topic = f"/{sensor.sensor_id}/rectify"
            # queue_size=1：优先传递最新帧，避免订阅侧堆积导致显示延迟
            self.rectify_pub = rospy.Publisher(rectify_topic, Image, queue_size=1, tcp_nodelay=True)
            rospy.loginfo(f"[{sensor.name}] Rectify发布话题: {rectify_topic}")
            
            # 预分配Image消息对象，避免每帧创建新对象
            self._img_msg = Image()
            self._img_msg.encoding = "bgr8"
            self._img_msg.is_bigendian = 0
            # height, width, step 在第一帧时设置（因为需要知道实际尺寸）
            self._img_msg_initialized = False

        
        # 设置保存目录：使用sensor_id作为子目录名
        if save_dir is None:
            self.save_dir = Path(__file__).parent.parent / "data" / sensor.sensor_id
        else:
            self.save_dir = Path(save_dir) / sensor.sensor_id
        
        # 如果需要保存图像，创建保存目录
        if self.save_rectify:
            self.save_dir.mkdir(parents=True, exist_ok=True)
            rospy.loginfo(f"[{sensor.sensor_id}] 图像保存目录: {self.save_dir}")
        
        # 保存时间戳列表（用于导出）
        self.timestamps = []
        
        # 写盘队列和线程
        # 队列大小为 publish_rate * queue_buffer_seconds，用于缓冲写盘任务
        queue_maxsize = int(publish_rate * queue_buffer_seconds)
        self.write_queue = queue.Queue(maxsize=queue_maxsize)
        self.write_thread_running = True
        self.write_thread = threading.Thread(target=self._write_worker, daemon=True)
        self.write_thread.start()
        
        rospy.loginfo(f"[{sensor.sensor_id}] 写盘队列大小: {queue_maxsize} (rate={publish_rate}Hz × {queue_buffer_seconds}s)")
        
        # 设置默认话题名称
        if topic_name is None:
            if namespace:
                topic_name = f"/{namespace}/timestamp"
            else:
                topic_name = f"/{sensor.sensor_id}/timestamp"
        
        # 设置默认frame_id
        if frame_id is None:
            frame_id = sensor.sensor_id
        
        super().__init__(sensor, publish_rate, topic_name, frame_id)
    
    def _get_default_topic_name(self) -> str:
        """获取默认话题名称"""
        return f"/{self.sensor.sensor_id}/timestamp"
    
    def _write_worker(self):
        """写盘工作线程：直接保存numpy原始数据，避免图像编码开销"""
        while True:
            task = self.write_queue.get()  # 阻塞等待，避免轮询开销
            try:
                if task is None:  # 退出信号
                    return
                filename, img = task
                # 直接保存numpy数组的原始字节，比np.save更快（无pickle开销）
                # 离线还原：np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)
                with open(str(filename), 'wb') as f:
                    f.write(img.tobytes())
            except Exception as e:
                rospy.logwarn(f"[{self.sensor.name}] 写盘失败: {e}")
            finally:
                self.write_queue.task_done()
    
    def _create_publisher(self):
        """创建ROS发布者"""
        # 使用Header消息，包含时间戳和frame_id
        pub = rospy.Publisher(self.topic_name, Header, queue_size=1, tcp_nodelay=True)
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
        
        # 创建Header消息
        msg = Header()
        msg.stamp = rospy.Time.from_sec(timestamp)
        msg.frame_id = self.frame_id
        msg.seq = self.frame_count
        
        return msg

    def publish_once(self):
        """
        发布一次数据（重写基类方法以支持同时发布Rectify图像）
        
        返回:
            bool: 是否成功发布
        """
        try:
            # 读取数据 (timestamp, rectify_img)
            data = self._read_data()
            if data is None:
                return False
            
            # 创建时间戳Header消息
            msg = self._create_message(data)
            if msg is None:
                return False
            
            # 发布时间戳Header（优先发布，保证低延迟）
            self.publisher.publish(msg)
            
            # 保存Rectify图像（异步写盘，在时间戳发布后执行）
            # 数据结构固定：shape=(700, 400, 3), dtype=uint8, BGR格式
            # 离线还原：np.frombuffer(data, dtype=np.uint8).reshape(700, 400, 3)
            if self.save_rectify and data[1] is not None:
                filename = self.save_dir / f"{self.frame_count:06d}_{data[0]}.raw"
                try:
                    self.write_queue.put_nowait((filename, data[1]))
                except queue.Full:
                    rospy.logwarn_throttle(5.0, f"[{self.sensor.name}] 写盘队列已满，丢弃本帧图像")
            
            # 如果需要发布Rectify图像
            if self.publish_rectify and data[1] is not None:
                rectify_data = data[1]
                
                # 首次发布时初始化固定字段
                if not self._img_msg_initialized:
                    self._img_msg.height = rectify_data.shape[0]
                    self._img_msg.width = rectify_data.shape[1]
                    self._img_msg.step = rectify_data.strides[0]
                    self._img_msg_initialized = True
                
                # 更新变化的字段
                self._img_msg.header.stamp = msg.stamp
                self._img_msg.header.frame_id = msg.frame_id
                self._img_msg.header.seq = msg.seq
                
                # 直接使用numpy数组的bytes，如果是C-contiguous可避免拷贝
                if rectify_data.flags['C_CONTIGUOUS']:
                    self._img_msg.data = rectify_data.data.tobytes()
                else:
                    self._img_msg.data = np.ascontiguousarray(rectify_data).data.tobytes()
                
                self.rectify_pub.publish(self._img_msg)

            self.frame_count += 1
            
            # 每100帧打印一次（调试用）
            if self.frame_count % 100 == 0:
                rospy.loginfo(f"[{self.sensor.sensor_id}] 已发布 {self.frame_count} 帧")
            
            return True

            
        except Exception as e:
            rospy.logerr(f"[{self.sensor.name}] 发布数据时出错: {e}")
            return False
    
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
        
        # 停止写盘线程：先等待队列清空，再发送退出信号，避免丢失已入队任务
        self.write_thread_running = False
        try:
            self.write_queue.join()
        except Exception as e:
            rospy.logwarn(f"[{self.sensor.name}] 等待写盘队列清空失败: {e}")
        
        try:
            self.write_queue.put_nowait(None)  # 发送退出信号
        except queue.Full:
            # 极端情况下队列满：阻塞放入退出信号，确保线程能退出
            self.write_queue.put(None)
        
        self.write_thread.join(timeout=5.0)  # 等待写盘线程完成
        
        # 导出时间戳
        self.export_timestamps()
        
        # 导出运行时配置
        if self.save_rectify:
            self.export_runtime_config()
        
        rospy.loginfo(f"[{self.sensor.name}] 发布器已关闭，共发布 {self.frame_count} 帧")
