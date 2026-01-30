#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计传感器文件夹下raw文件的时间戳并计算帧率
用法：python calc_raw_fps.py --sensor-dir <path/to/sensor_dir>
"""
import argparse
from pathlib import Path
import re

def extract_timestamp(stem):
    # 假设文件名格式为 000000_1769592964.2512070
    m = re.match(r"\d+_(\d+\.\d+)", stem)
    if m:
        return float(m.group(1))
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="统计raw文件时间戳并计算帧率")
    parser.add_argument('--sensor-dir', type=str, required=True, help='传感器文件夹路径')
    args = parser.parse_args()
    sensor_dir = Path(args.sensor_dir)
    raw_files = sorted(sensor_dir.glob("*.raw"))
    timestamps = []
    for f in raw_files:
        ts = extract_timestamp(f.stem)
        if ts is not None:
            timestamps.append(ts)
    if len(timestamps) < 2:
        print("raw文件不足两帧，无法计算帧率")
    else:
        timestamps.sort()
        intervals = [t2 - t1 for t1, t2 in zip(timestamps[:-1], timestamps[1:])]
        avg_interval = sum(intervals) / len(intervals)
        fps = 1.0 / avg_interval if avg_interval > 0 else 0
        print(f"帧数: {len(timestamps)}")
        print(f"平均间隔: {avg_interval:.6f} 秒")
        print(f"估算帧率: {fps:.2f} FPS")
