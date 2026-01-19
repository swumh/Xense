#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xense ROS Force 主启动脚本
功能：根据配置启动传感器和发布器
"""

import rospy
import sys
import argparse
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from xense_manager import XenseManager
from config import XenseConfig
from force_publisher import XenseForcePublisher


def setup_from_config(config_path: str = None, use_rosparam: bool = False) -> XenseManager:
    """
    根据配置文件或ROS参数设置传感器和发布器
    
    参数:
        config_path: 配置文件路径，如果为None则使用默认路径
        use_rosparam: 是否从ROS参数服务器加载配置
    
    返回:
        XenseManager: 配置好的管理器实例
    """
    manager = XenseManager()
    
    # 加载配置
    config = None
    if use_rosparam:
        config = XenseConfig.load_from_rosparam()
    elif config_path:
        config = XenseConfig.load_from_file(config_path)
    else:
        # 尝试从默认路径加载
        default_config_path = Path(__file__).parent.parent / "config" / "xense_config.json"
        if default_config_path.exists():
            config = XenseConfig.load_from_file(str(default_config_path))
        else:
            rospy.loginfo("[Main] 未找到配置文件，使用默认配置")
            config = XenseConfig.DEFAULT_CONFIG.copy()
    
    # 验证配置
    if not XenseConfig.validate_config(config):
        rospy.logerr("[Main] 配置验证失败，退出")
        sys.exit(1)
    
    # 获取全局默认值
    global_config = config.get('global', {})
    default_rate = global_config.get('default_publish_rate', 30.0)
    default_frame_id = global_config.get('default_frame_id', 'xense_sensor')
    default_use_stamped = global_config.get('default_use_stamped', True)
    
    # 根据配置添加传感器和发布器
    for sensor_config in config['sensors']:
        sensor_name = sensor_config['name']
        sensor_id = sensor_config.get('sensor_id', None)
        
        try:
            # 添加传感器
            sensor = manager.add_sensor(sensor_id=sensor_id, name=sensor_name)
            
            # 添加发布器
            publishers_config = sensor_config.get('publishers', [])
            if not publishers_config:
                rospy.logwarn(f"[Main] 传感器 '{sensor_name}' 没有配置发布器")
                continue
            
            for pub_config in publishers_config:
                pub_type = pub_config.get('type', 'force')
                
                if pub_type == 'force':
                    # 六维力发布器
                    publisher = manager.add_force_publisher(
                        sensor_name=sensor_name,
                        publish_rate=pub_config.get('publish_rate', default_rate),
                        topic_name=pub_config.get('topic_name', None),
                        frame_id=pub_config.get('frame_id', None),
                        use_stamped=pub_config.get('use_stamped', default_use_stamped),
                        namespace=pub_config.get('namespace', '')
                    )
                else:
                    rospy.logwarn(f"[Main] 未知的发布器类型: {pub_type}，跳过")
        
        except Exception as e:
            rospy.logerr(f"[Main] 配置传感器 '{sensor_name}' 失败: {e}")
            continue
    
    return manager


def setup_single_sensor(sensor_id: str = None, publish_rate: float = 30.0,
                        topic_name: str = None, frame_id: str = None,
                        use_stamped: bool = True) -> XenseManager:
    """
    设置单个传感器（简单模式）
    
    参数:
        sensor_id: 传感器ID，如果为None则自动检测
        publish_rate: 发布频率（Hz）
        topic_name: ROS话题名称
        frame_id: 坐标系ID
        use_stamped: 是否使用WrenchStamped消息
    
    返回:
        XenseManager: 配置好的管理器实例
    """
    manager = XenseManager()
    
    # 添加传感器
    sensor = manager.add_sensor(sensor_id=sensor_id, name="xense_1")
    
    # 添加六维力发布器
    manager.add_force_publisher(
        sensor_name="xense_1",
        publish_rate=publish_rate,
        topic_name=topic_name,
        frame_id=frame_id,
        use_stamped=use_stamped
    )
    
    return manager


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Xense六维力ROS发布节点')
    
    # 配置相关参数
    parser.add_argument('--config', type=str, default=None,
                       help='配置文件路径（JSON格式）')
    parser.add_argument('--use-rosparam', action='store_true',
                       help='从ROS参数服务器加载配置')
    
    # 单传感器模式参数（简单模式）
    parser.add_argument('--sensor-id', type=str, default=None,
                       help='传感器序列号或ID（简单模式），如果不指定则自动检测')
    parser.add_argument('--rate', type=float, default=30.0,
                       help='发布频率（Hz），默认30Hz')
    parser.add_argument('--frame-id', type=str, default=None,
                       help='坐标系ID，默认使用传感器名称')
    parser.add_argument('--topic-name', type=str, default=None,
                       help='ROS话题名称，默认使用 /{sensor_name}/force')
    parser.add_argument('--no-stamped', action='store_true',
                       help='使用Wrench消息而不是WrenchStamped（不带时间戳）')
    
    # 解析命令行参数
    args, unknown = parser.parse_known_args()
    
    # 初始化ROS节点
    rospy.init_node('xense_force_publisher', anonymous=True)
    
    # 从ROS参数服务器获取参数（优先级高于命令行参数）
    config_path = rospy.get_param('~config', args.config)
    use_rosparam = rospy.get_param('~use_rosparam', args.use_rosparam)
    sensor_id = rospy.get_param('~sensor_id', args.sensor_id)
    publish_rate = rospy.get_param('~rate', args.rate)
    frame_id = rospy.get_param('~frame_id', args.frame_id)
    topic_name = rospy.get_param('~topic_name', args.topic_name)
    use_stamped = not rospy.get_param('~no_stamped', args.no_stamped)
    
    # 设置传感器和发布器
    try:
        if config_path or use_rosparam:
            # 使用配置文件模式
            rospy.loginfo("[Main] 使用配置文件模式")
            manager = setup_from_config(config_path=config_path, use_rosparam=use_rosparam)
        else:
            # 使用简单模式（单传感器）
            rospy.loginfo("[Main] 使用简单模式（单传感器）")
            manager = setup_single_sensor(
                sensor_id=sensor_id,
                publish_rate=publish_rate,
                topic_name=topic_name,
                frame_id=frame_id,
                use_stamped=use_stamped
            )
        
        # 打印统计信息
        stats = manager.get_statistics()
        rospy.loginfo(f"[Main] 配置完成:")
        rospy.loginfo(f"  - 传感器数量: {len(stats['sensors'])}")
        rospy.loginfo(f"  - 发布器数量: {len(stats['publishers'])}")
        
        # 注册关闭回调
        rospy.on_shutdown(manager.shutdown)
        
        # 启动发布器（阻塞）
        if len(manager.publishers) == 1:
            # 单个发布器，直接运行
            publisher_name = list(manager.publishers.keys())[0]
            manager.start_single_publisher(publisher_name)
        else:
            # 多个发布器，使用多线程
            threads = manager.start_all_publishers()
            # 主线程等待ROS关闭信号
            rospy.spin()
            # 等待所有线程结束
            for thread in threads:
                thread.join(timeout=1.0)
    
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

