#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xense 离线数据处理脚本
功能：处理单个 session 下各传感器的 .raw，使用 SDK 离线还原并直接保存 selectSensorInfo 原始数值

python script/process_raw.py --session-dir data/2026* --export-vis-png
"""

import numpy as np
import importlib
from pathlib import Path
from xensesdk import Sensor
import argparse

def process_session(session_dir: Path, export_vis_png: bool = False):
    """
    处理单个 session 目录下所有传感器的数据
    """
    cv2 = None
    if export_vis_png:
        try:
            cv2 = importlib.import_module("cv2")
        except ImportError:
            print("[Error] --export-vis-png 需要安装 opencv-python (cv2)")
            return

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

        # 直接保存 selectSensorInfo 原始输出（不做额外处理）
        direct_dir = sensor_dir / "SensorInfoRaw"
        rectify_raw_dir = direct_dir / "Rectify"
        diff_raw_dir = direct_dir / "Difference"
        depth_raw_dir = direct_dir / "Depth"
        rectify_raw_dir.mkdir(parents=True, exist_ok=True)
        diff_raw_dir.mkdir(parents=True, exist_ok=True)
        depth_raw_dir.mkdir(parents=True, exist_ok=True)

        # 可选：额外导出图像文件
        if export_vis_png:
            rectify_vis_dir = sensor_dir / "Rectify"
            diff_vis_dir = sensor_dir / "Difference"
            depth_vis_dir = sensor_dir / "Depth"
            rectify_vis_dir.mkdir(exist_ok=True)
            diff_vis_dir.mkdir(exist_ok=True)
            depth_vis_dir.mkdir(exist_ok=True)

        # 如果需要导出可视化PNG，先扫描全局深度范围（用于固定色标）
        depth_vmin, depth_vmax = 0.0, 1.0
        if export_vis_png and raw_files:
            print(f"[Info] 第一遍扫描：计算全局深度范围...")
            depth_samples = []
            # 均匀采样最多50帧来估算全局范围，避免全量扫描太慢
            sample_indices = np.linspace(0, len(raw_files) - 1, min(50, len(raw_files)), dtype=int)
            for si in sample_indices:
                with open(raw_files[si], 'rb') as f:
                    sample_img = np.frombuffer(f.read(), dtype=np.uint8).reshape(700, 400, 3)
                sample_depth = sensor_solver.selectSensorInfo(
                    Sensor.OutputType.Depth, rectify_image=sample_img
                )
                if sample_depth is not None:
                    depth_samples.append(sample_depth)
            if depth_samples:
                all_depth = np.concatenate([d.ravel() for d in depth_samples])
                # 用 P1-P99 分位数作为固定色标范围，排除极端值
                depth_vmin, depth_vmax = np.percentile(all_depth, [1, 99])
                if depth_vmin == depth_vmax:
                    depth_vmax = depth_vmin + 1.0
                print(f"[Info] 全局深度范围 (P1-P99): [{depth_vmin:.2f}, {depth_vmax:.2f}] mm")

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

            # ===== 直接保存原始数值 =====
            if rectify is not None:
                np.save(rectify_raw_dir / f"{stem}.npy", rectify)
            if diff is not None:
                np.save(diff_raw_dir / f"{stem}.npy", diff)
            if depth is not None:
                np.save(depth_raw_dir / f"{stem}.npy", depth)

            # ===== 可选导出显示图 =====
            if export_vis_png:
                if rectify is not None:
                    cv2.imwrite(str(rectify_vis_dir / f"{stem}.png"), rectify)
                if diff is not None:
                    cv2.imwrite(str(diff_vis_dir / f"{stem}.png"), diff)
                if depth is not None:
                    # 使用全局固定色标（P1-P99）归一化，跨帧颜色可直接比较
                    depth_clipped = np.clip(depth, depth_vmin, depth_vmax)
                    depth_norm = ((depth_clipped - depth_vmin) / (depth_vmax - depth_vmin) * 255).astype(np.uint8)
                    depth_vis = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)
                    cv2.imwrite(str(depth_vis_dir / f"{stem}.png"), depth_vis)

            ts_list.append(ts_str)
            force_list.append(force)
            force_resultant_list.append(force_resultant)
            force_norm_list.append(force_norm)

        # 直接保存力相关原始数值
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
    parser.add_argument('--export-vis-png', action='store_true',
                        help='可选：额外导出Rectify/Difference/Depth的PNG')
    args = parser.parse_args()
    session_dir = Path(args.session_dir).resolve()
    if not session_dir.is_dir():
        print(f"[Error] 指定的 session 目录不存在: {session_dir}")
        return
    print(f"[Session] 处理: {session_dir}")
    process_session(session_dir, export_vis_png=args.export_vis_png)

if __name__ == '__main__':
    main()
