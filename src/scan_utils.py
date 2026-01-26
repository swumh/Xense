import json
from pathlib import Path
import time
import datetime
import numpy as np

# 假设 xensesdk 已经正确安装
try:
    from xensesdk import Sensor
except ImportError:
    # 仅用于演示，如果没有SDK防止报错
    Sensor = None 

def save_scan_result_to_json(sensors: dict, output_path: str = None):
    """
    将扫描到的传感器信息保存为 json 文件
    Args:
        sensors (dict): {序列号: 相机ID}
        output_path (str): 保存路径，默认为 data/scan_result.json
    """
    if output_path is None:
        # 使用当前脚本父级目录的 config 文件夹
        output_path = Path(__file__).resolve().parent / 'config' / 'scan_result.json'
    else:
        output_path = Path(output_path)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 检测左右
    side_map = {serial: "unknown" for serial in sensors}
    if len(sensors) == 2:
        try:
            print("-" * 30)
            print("[Scan] 检测到双目，开始左右位置识别...")
            side_map = detect_sensor_side(sensors)
        except Exception as e:
            print(f"[Scan] 警告: 检测左右位置失败 ({e})，将标记为 unknown")
    
    result = {
        "xv_serial": "",
        "count": len(sensors),
        "sensors": [
            {
                "serial": serial, 
                "camera_id": cam_id, 
                "side": side_map.get(serial, "unknown")
            } for serial, cam_id in sensors.items()
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[Scan] 结果已保存到: {output_path}")


def detect_sensor_side(sensors: dict, press_duration=5, interval=0.1):
    """
    通过图像变化区分左右，提示用户按压左边sensor
    返回: {serial: "left"/"right"}
    """
    if not sensors:
        return {}

    sensor_objs = []
    # 存储序列号到对象的映射，方便后续访问
    serial_to_obj = {} 

    try:
        # 1. 初始化所有传感器
        for serial in sensors:
            sensor = Sensor.create(serial)
            sensor_objs.append(sensor)
            serial_to_obj[serial] = sensor

        print(f"请准备：将在倒计时结束后按压【左边】传感器持续 {press_duration} 秒。")
        
        # 2. 倒计时
        for i in range(3, 0, -1):
            print(f"{i}...", end=" ", flush=True)
            time.sleep(1)
        print("\n>>> 开始检测！请间断性按压左边传感器！ <<<")

        # 3. 采集基准帧 (倒计时结束后立即采集，减少环境干扰)
        first_rectify = {}
        for serial, sensor in serial_to_obj.items():
            img = sensor.selectSensorInfo(Sensor.OutputType.Rectify)
            # 确保拿到了图像，如果拿不到可能需要重试机制，这里简单处理
            if img is not None:
                first_rectify[serial] = img.astype(np.float32)
            else:
                first_rectify[serial] = None
                print(f"[Scan] 警告: 无法获取传感器 {serial} 的基准图像")

        # 4. 循环累计差异
        diff_sum = {serial: 0.0 for serial in sensors}
        t0 = time.time()
        
        while time.time() - t0 < press_duration:
            for serial, sensor in serial_to_obj.items():
                if first_rectify[serial] is None:
                    continue

                img = sensor.selectSensorInfo(Sensor.OutputType.Rectify)
                if img is not None:
                    # 计算当前帧与基准帧的绝对差
                    curr_img = img.astype(np.float32)
                    diff = np.abs(curr_img - first_rectify[serial])
                    diff_val = np.sum(diff)
                    diff_sum[serial] += diff_val
            
            time.sleep(interval)

        # 5. 分析结果
        # 按累计变化量降序排列，变化最大的是左边
        sorted_serials = sorted(diff_sum, key=diff_sum.get, reverse=True)
        
        side_map = {}
        # 假设变化量最大的确实发生了显著变化（可以加个阈值判断防止误判，这里先略过）
        if len(sorted_serials) > 0:
            side_map[sorted_serials[0]] = "left"
            print(f"检测到左侧: {sorted_serials[0]} (变化量: {diff_sum[sorted_serials[0]]:.2f})")
        
        if len(sorted_serials) > 1:
            # 剩下的那个是右边
            side_map[sorted_serials[1]] = "right"
            print(f"推断为右侧: {sorted_serials[1]} (变化量: {diff_sum[sorted_serials[1]]:.2f})")

        return side_map

    finally:
        # 6. 确保资源释放 (无论是否出错都会执行)
        print("[Scan] 释放传感器资源...")
        for sensor in sensor_objs:
            try:
                if sensor:
                    sensor.release()
            except Exception as e:
                print(f"释放传感器失败: {e}")