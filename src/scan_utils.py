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


def detect_single_pressed_sensor(sensors: dict, sensor_objs: dict, prompt: str, 
                                  press_duration: float = 5, interval: float = 0.02) -> str:
    """
    检测用户按压的单个传感器，返回其序列号
    
    Args:
        sensors: {序列号: 相机ID} 的映射
        sensor_objs: {序列号: Sensor对象} 的映射（已初始化）
        prompt: 提示用户的信息
        press_duration: 检测持续时间
        interval: 采样间隔
    
    Returns:
        str: 被按压的传感器序列号
    """
    print(f"\n请准备：将在倒计时结束后 {prompt}")
    
    # 倒计时期间采集基准帧（此时用户未按压，环境稳定）
    # 累积所有帧并计算均值作为基准
    frame_accum = {serial: [] for serial in sensor_objs}
    for i in range(3, 0, -1):
        print(f"{i}...", end=" ", flush=True)
        # 在倒计时期间持续采集基准帧
        for serial, sensor in sensor_objs.items():
            img = sensor.selectSensorInfo(Sensor.OutputType.Rectify)
            if img is not None:
                frame_accum[serial].append(img.astype(np.float32))
        time.sleep(1)
    
    # 计算均值作为基准帧
    first_rectify = {}
    for serial in sensor_objs:
        if frame_accum[serial]:
            # 取所有采集帧的均值
            first_rectify[serial] = np.mean(frame_accum[serial], axis=0)
            print(f"[Scan] 传感器 {serial} 基准帧采集: {len(frame_accum[serial])} 帧")
        else:
            first_rectify[serial] = None
            print(f"[Scan] 警告: 无法获取传感器 {serial} 的基准图像")
    
    print(f"\n>>> 开始检测！请间断性按压传感器！ <<<")

    # 循环累计差异
    diff_sum = {serial: 0.0 for serial in sensors}
    t0 = time.time()
    
    while time.time() - t0 < press_duration:
        for serial, sensor in sensor_objs.items():
            if first_rectify[serial] is None:
                continue

            img = sensor.selectSensorInfo(Sensor.OutputType.Rectify)
            if img is not None:
                curr_img = img.astype(np.float32)
                diff = np.abs(curr_img - first_rectify[serial])
                diff_val = np.sum(diff)
                diff_sum[serial] += diff_val
        
        time.sleep(interval)

    # 找到变化量最大的传感器
    max_serial = max(diff_sum, key=diff_sum.get)
    max_diff = diff_sum[max_serial]
    
    print(f"检测到被按压的传感器: {max_serial} (变化量: {max_diff:.2f})")
    
    # 提示用户停止按压，等待2秒再进行下一次检测
    print(">>> 请停止按压，准备下一次检测... <<<")
    time.sleep(2)
    
    return max_serial


def detect_four_sensors_grouped(sensors: dict, press_duration: float = 5, interval: float = 0.02) -> list:
    """
    检测4个传感器并分成两组，每组包含左右两个传感器
    
    流程:
    1. 提示用户按压第一组的左侧传感器
    2. 提示用户按压第一组的右侧传感器
    3. 提示用户按压第二组的左侧传感器
    4. 剩下的传感器自动作为第二组的右侧
    
    Args:
        sensors: {序列号: 相机ID} 的映射（4个传感器）
        press_duration: 每次检测持续时间
        interval: 采样间隔
    
    Returns:
        list: 两个组的列表，每组格式为:
              {
                  "xv_serial": "",
                  "sensors": [
                      {"serial": xxx, "camera_id": xxx, "side": "left"},
                      {"serial": xxx, "camera_id": xxx, "side": "right"}
                  ]
              }
    """
    if len(sensors) != 4:
        raise ValueError(f"需要4个传感器，但检测到 {len(sensors)} 个")
    
    sensor_objs = {}
    remaining_serials = set(sensors.keys())
    
    try:
        # 初始化所有传感器
        print("[Scan] 初始化所有传感器...")
        for serial in sensors:
            sensor = Sensor.create(serial)
            sensor_objs[serial] = sensor
        
        groups = []
        
        # === 第一组 ===
        print("\n" + "=" * 50)
        print("【第一组传感器配置】")
        print("=" * 50)
        
        # 第一组左侧
        group1_left = detect_single_pressed_sensor(
            {s: sensors[s] for s in remaining_serials},
            {s: sensor_objs[s] for s in remaining_serials},
            "按压【第一组的左侧】传感器，持续 {} 秒".format(press_duration),
            press_duration, interval
        )
        remaining_serials.remove(group1_left)
        print(f"✓ 第一组左侧: {group1_left}")
        
        # 第一组右侧
        group1_right = detect_single_pressed_sensor(
            {s: sensors[s] for s in remaining_serials},
            {s: sensor_objs[s] for s in remaining_serials},
            "按压【第一组的右侧】传感器，持续 {} 秒".format(press_duration),
            press_duration, interval
        )
        remaining_serials.remove(group1_right)
        print(f"✓ 第一组右侧: {group1_right}")
        
        groups.append({
            "xv_serial": "",
            "sensors": [
                {"serial": group1_left, "camera_id": sensors[group1_left], "side": "left"},
                {"serial": group1_right, "camera_id": sensors[group1_right], "side": "right"}
            ]
        })
        
        # === 第二组 ===
        print("\n" + "=" * 50)
        print("【第二组传感器配置】")
        print("=" * 50)
        
        # 第二组左侧
        group2_left = detect_single_pressed_sensor(
            {s: sensors[s] for s in remaining_serials},
            {s: sensor_objs[s] for s in remaining_serials},
            "按压【第二组的左侧】传感器，持续 {} 秒".format(press_duration),
            press_duration, interval
        )
        remaining_serials.remove(group2_left)
        print(f"✓ 第二组左侧: {group2_left}")
        
        # 第二组右侧（剩下的最后一个）
        group2_right = remaining_serials.pop()
        print(f"✓ 第二组右侧（自动）: {group2_right}")
        
        groups.append({
            "xv_serial": "",
            "sensors": [
                {"serial": group2_left, "camera_id": sensors[group2_left], "side": "left"},
                {"serial": group2_right, "camera_id": sensors[group2_right], "side": "right"}
            ]
        })
        
        return groups
        
    finally:
        # 确保资源释放
        print("\n[Scan] 释放传感器资源...")
        for sensor in sensor_objs.values():
            try:
                if sensor:
                    sensor.release()
            except Exception as e:
                print(f"释放传感器失败: {e}")


def save_grouped_scan_result(groups: list, output_path: str = None):
    """
    将分组的传感器信息保存为单个 JSON 文件（包含多组）
    
    Args:
        groups: detect_four_sensors_grouped 返回的分组列表
        output_path: 保存路径，默认为 config/scan_result.json
    """
    if output_path is None:
        output_path = Path(__file__).resolve().parent / 'config' / 'scan_result.json'
    else:
        output_path = Path(output_path)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 构建结果数组，每组一个对象
    result = []
    for i, group in enumerate(groups, start=1):
        group_data = {
            "xv_serial": group["xv_serial"],
            "count": len(group["sensors"]),
            "sensors": group["sensors"]
        }
        result.append(group_data)
        print(f"[Scan] 第 {i} 组: 左侧={group['sensors'][0]['serial']}, 右侧={group['sensors'][1]['serial']}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n[Scan] 结果已保存到: {output_path}")
    print("\n" + "=" * 50)
    print("【重要提示】")
    print(f"请手动编辑 {output_path}，填写每组对应的 xv_serial")
    print("=" * 50)
    
    return output_path


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


def detect_sensor_side(sensors: dict, press_duration=5, interval=0.02):
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
        
        # 2. 倒计时期间采集基准帧（此时用户未按压，环境稳定）
        # 累积所有帧并计算均值作为基准
        frame_accum = {serial: [] for serial in serial_to_obj}
        for i in range(3, 0, -1):
            print(f"{i}...", end=" ", flush=True)
            # 在倒计时期间持续采集基准帧
            for serial, sensor in serial_to_obj.items():
                img = sensor.selectSensorInfo(Sensor.OutputType.Rectify)
                if img is not None:
                    frame_accum[serial].append(img.astype(np.float32))
            time.sleep(1)
        
        # 计算均值作为基准帧
        first_rectify = {}
        for serial in serial_to_obj:
            if frame_accum[serial]:
                # 取所有采集帧的均值
                first_rectify[serial] = np.mean(frame_accum[serial], axis=0)
                print(f"[Scan] 传感器 {serial} 基准帧采集: {len(frame_accum[serial])} 帧")
            else:
                first_rectify[serial] = None
                print(f"[Scan] 警告: 无法获取传感器 {serial} 的基准图像")
        
        print("\n>>> 开始检测！请间断性按压左边传感器！ <<<")

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