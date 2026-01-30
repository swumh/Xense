#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xense 离线数据处理脚本
功能：批量处理 data/2026* 路径下所有 session 的原始数据，使用 SDK 离线还原并导出多种数据类型
"""

import numpy as np
import cv2
from pathlib import Path
from xensesdk import Sensor
import os
import argparse
import json

def process_session(session_dir: Path):
    """
    处理单个 session 目录下所有传感器的数据
    """
    for sensor_dir in session_dir.iterdir():
        if not sensor_dir.is_dir():
            continue
        runtime_path = sensor_dir / f"runtime_{sensor_dir.name}"
        timestamps_path = sensor_dir / "timestamps.npy"
        if not runtime_path.exists() or not timestamps_path.exists():
            print(f"[Skip] 缺少 runtime 或 timestamps: {sensor_dir}")
            continue
        print(f"[Info] 处理传感器: {sensor_dir.name}")
        sensor_solver = Sensor.createSolver(str(runtime_path))
        raw_files = sorted(sensor_dir.glob("*.raw"))
        rectify_dir = sensor_dir / "Rectify"
        diff_dir = sensor_dir / "Difference"
        depth_dir = sensor_dir / "Depth"
        rectify_dir.mkdir(exist_ok=True)
        diff_dir.mkdir(exist_ok=True)
        depth_dir.mkdir(exist_ok=True)
        force_list = []
        force_resultant_list = []
        force_norm_list = []
        ts_list = []
        for raw_file in raw_files:
            with open(raw_file, 'rb') as f:
                img = np.frombuffer(f.read(), dtype=np.uint8).reshape(700, 400, 3)
            rectify, diff, depth, force, force_resultant, force_norm = sensor_solver.selectSensorInfo(
                Sensor.OutputType.Rectify,
                Sensor.OutputType.Difference,
                Sensor.OutputType.Depth,
                Sensor.OutputType.Force,
                Sensor.OutputType.ForceResultant,
                Sensor.OutputType.ForceNorm,
                rectify_image=img
            )
            stem = raw_file.stem
            # 保证小数点后7位，假设stem格式为 '000000_1769592964.2512070' 或类似
            if '_' in stem:
                idx, ts = stem.split('_', 1)
                try:
                    # 保证小数点后7位且保留末尾0
                    if '.' in ts:
                        int_part, dec_part = ts.split('.', 1)
                        dec_part = (dec_part + '0000000')[:7]
                        ts_str = f"{int(idx):06d}_{int_part}.{dec_part}"
                    else:
                        ts_str = f"{int(idx):06d}_{ts}.0000000"[:7]
                except Exception:
                    ts_str = stem
            else:
                ts_str = stem
            if rectify is not None:
                cv2.imwrite(str(rectify_dir / f"{stem}.png"), rectify)
            if diff is not None:
                cv2.imwrite(str(diff_dir / f"{stem}.png"), diff)
            if depth is not None:
                depth_vis = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
                depth_vis = np.uint8(depth_vis)
                cv2.imwrite(str(depth_dir / f"{stem}.png"), depth_vis)
            ts_list.append(ts_str)
            force_list.append(force)
            force_resultant_list.append(force_resultant)
            force_norm_list.append(force_norm)
        np.savez(sensor_dir / "force_data.npz",
                 timestamps=np.array(ts_list, dtype='U'),
                 force=np.array(force_list),
                 force_resultant=np.array(force_resultant_list),
                 force_norm=np.array(force_norm_list))
        sensor_solver.release()
        print(f"[Done] {sensor_dir.name} 处理完成")

def main():
    parser = argparse.ArgumentParser(description="Xense 离线单文件夹数据处理")
    parser.add_argument('--session-dir', type=str, required=True, help="单个 session 目录 (如 data/20260126_160940)")
    args = parser.parse_args()
    session_dir = Path(args.session_dir).resolve()
    if not session_dir.is_dir():
        print(f"[Error] 指定的 session 目录不存在: {session_dir}")
        return
    print(f"[Session] 处理: {session_dir}")
    process_session(session_dir)

if __name__ == '__main__':
    main()
