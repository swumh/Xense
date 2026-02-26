#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计传感器文件夹下raw文件的时间戳并计算帧率
用法：python calc_raw_fps.py --sensor-dir <path/to/sensor_dir>
"""
import argparse
from pathlib import Path
import re
import statistics


def parse_raw_meta(stem: str):
    """
    解析文件名中的帧号与时间戳
    期望格式：000000_1769592964.2512070

    返回:
        (index, timestamp) 或 (None, None)
    """
    m = re.match(r"(\d+)_(\d+\.\d+)$", stem)
    if not m:
        return None, None
    try:
        return int(m.group(1)), float(m.group(2))
    except ValueError:
        return None, None

def extract_timestamp(stem):
    # 假设文件名格式为 000000_1769592964.2512070
    m = re.match(r"\d+_(\d+\.\d+)", stem)
    if m:
        return float(m.group(1))
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="统计raw文件时间戳并计算帧率")
    parser.add_argument('--sensor-dir', type=str, required=True, help='传感器文件夹路径')
    parser.add_argument('--expected-fps', type=float, default=None,
                        help='可选：期望帧率，用于检测异常帧间隔和估算丢帧')
    parser.add_argument('--jitter-mult', type=float, default=2.0,
                        help='抖动异常阈值倍数，默认2.0（interval > 中位数*该值判为异常）')
    args = parser.parse_args()

    sensor_dir = Path(args.sensor_dir)
    raw_files = sorted(sensor_dir.glob("*.raw"))
    if not raw_files:
        print("未找到raw文件")
        raise SystemExit(0)

    timestamps = []
    indexes = []
    invalid_name_count = 0

    for f in raw_files:
        idx, ts = parse_raw_meta(f.stem)
        if idx is None or ts is None:
            invalid_name_count += 1
            ts = extract_timestamp(f.stem)
            if ts is None:
                continue
        else:
            indexes.append(idx)

        if ts is not None:
            timestamps.append(ts)

    if len(timestamps) < 2:
        print("raw文件不足两帧，无法计算帧率")
    else:
        # 统计信息按文件名排序后的顺序进行，避免掩盖时间戳回退问题
        intervals = [t2 - t1 for t1, t2 in zip(timestamps[:-1], timestamps[1:])]
        avg_interval = sum(intervals) / len(intervals)
        fps = 1.0 / avg_interval if avg_interval > 0 else 0

        median_interval = statistics.median(intervals)
        min_interval = min(intervals)
        max_interval = max(intervals)
        std_interval = statistics.pstdev(intervals) if len(intervals) > 1 else 0.0

        # 检测1：时间戳非单调（回退或重复）
        non_monotonic = [i for i, dt in enumerate(intervals, start=1) if dt <= 0]

        # 检测2：帧号连续性（如果文件名可解析出索引）
        seq_gaps = []
        if len(indexes) >= 2:
            for prev_i, cur_i in zip(indexes[:-1], indexes[1:]):
                d = cur_i - prev_i
                if d != 1:
                    seq_gaps.append((prev_i, cur_i, d))

        # 检测3：异常大间隔（疑似延迟/丢帧）
        # 使用中位数作为稳健基准
        if median_interval > 0:
            abnormal_threshold = median_interval * max(args.jitter_mult, 1.0)
        else:
            abnormal_threshold = float('inf')
        abnormal_gaps = [(i, dt) for i, dt in enumerate(intervals, start=1) if dt > abnormal_threshold]

        # 检测4：按期望FPS估算丢帧
        estimated_drop_count = None
        expected_interval = None
        if args.expected_fps and args.expected_fps > 0:
            expected_interval = 1.0 / args.expected_fps
            estimated_drop_count = 0
            for dt in intervals:
                if dt > 1.5 * expected_interval:
                    # 例如 dt≈3*expected_interval，则估算丢了2帧
                    estimated_drop_count += max(0, int(round(dt / expected_interval)) - 1)

        print(f"文件总数: {len(raw_files)}")
        print(f"可解析时间戳帧数: {len(timestamps)}")
        print(f"文件名格式异常数: {invalid_name_count}")
        print(f"帧数: {len(timestamps)}")
        print(f"平均间隔: {avg_interval:.6f} 秒")
        print(f"中位间隔: {median_interval:.6f} 秒")
        print(f"最小间隔: {min_interval:.6f} 秒")
        print(f"最大间隔: {max_interval:.6f} 秒")
        print(f"间隔标准差: {std_interval:.6f} 秒")
        print(f"估算帧率: {fps:.2f} FPS")

        print("\n[检测结果]")
        if non_monotonic:
            print(f"❌ 检测到非单调时间戳（回退/重复）次数: {len(non_monotonic)}")
            print(f"   首次发生在第 {non_monotonic[0]} -> {non_monotonic[0]+1} 帧")
        else:
            print(" 时间戳单调递增")

        if seq_gaps:
            print(f" 检测到帧号不连续次数: {len(seq_gaps)}")
            p, c, d = seq_gaps[0]
            print(f"   示例: {p} -> {c} (差值 {d})")
        else:
            print(" 帧号连续（基于文件名索引）")

        if abnormal_gaps:
            print(f" 检测到异常大间隔次数: {len(abnormal_gaps)} (阈值>{abnormal_threshold:.6f}s)")
            i, dt = abnormal_gaps[0]
            print(f"   示例: 第 {i} -> {i+1} 帧间隔 {dt:.6f}s")
        else:
            print(" 未发现明显异常大间隔")

        if estimated_drop_count is not None:
            print(f"期望帧率: {args.expected_fps:.2f} FPS (期望间隔 {expected_interval:.6f}s)")
            print(f"估算丢帧数: {estimated_drop_count}")
