#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化 Xense 离线处理结果：Rectify、Difference、Depth（图片），Force、ForceResultant、ForceNorm（npz），并合成视频。
前提：已使用 script/process_raw.py --export-vis-png 处理原始数据，并生成对应的可视化 Rectify、Difference、Depth 图片和 force_data.npz 文件。
输入：单个 sensor 目录（如 data/20260128_170658/OG000276）
输出：output.mp4

python script/visualize_force_video.py --sensor-dir data/2026*/OG000*
"""
import cv2
import numpy as np
from pathlib import Path
import argparse


def visualize_force(force, vmin=None, vmax=None):
    # force: (35, 20, 3) -> 取模长后用固定色标可视化
    mag = np.linalg.norm(force, axis=2)
    if vmin is not None and vmax is not None:
        mag_clipped = np.clip(mag, vmin, vmax)
        mag_norm = ((mag_clipped - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    else:
        mag_norm = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    img = cv2.applyColorMap(mag_norm, cv2.COLORMAP_JET)
    return img

def visualize_force_norm(force_norm, vmin=None, vmax=None):
    # force_norm: (35, 20, 3) -> 取第三维的第3个分量，用固定色标可视化
    norm = force_norm[..., 2] if force_norm.ndim == 3 and force_norm.shape[2] == 3 else force_norm
    if vmin is not None and vmax is not None:
        norm_clipped = np.clip(norm, vmin, vmax)
        norm_img = ((norm_clipped - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    else:
        norm_img = cv2.normalize(norm, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    img = cv2.applyColorMap(norm_img, cv2.COLORMAP_JET)
    return img

def visualize_force_resultant(force_resultant, global_maxv=None):
    # force_resultant: (6,) -> 绘制条形图（使用全局固定尺度）
    h, w = 100, 200
    img = np.ones((h, w, 3), dtype=np.uint8) * 255
    if global_maxv is not None and global_maxv > 0:
        maxv = global_maxv
    else:
        maxv = np.max(np.abs(force_resultant))
        if maxv == 0:
            maxv = 1
    bar_w = w // 6
    for i, v in enumerate(force_resultant):
        x = i * bar_w + bar_w // 2
        y0 = h // 2
        y1 = int(y0 - (v / maxv) * (h // 2 - 10))
        color = (0, 0, 255) if i < 3 else (0, 128, 0)
        cv2.line(img, (x, y0), (x, y1), color, bar_w // 2)
        cv2.putText(img, f"{v:.1f}", (x - 15, y0 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,0), 1)
    return img

def main():
    parser = argparse.ArgumentParser(description="Xense 六数据可视化并导出视频")
    parser.add_argument('--sensor-dir', type=str, required=True, help="单个 sensor 目录 (如 data/20260128_170658/OG000276)")
    parser.add_argument('--output', type=str, default="output.mp4", help="输出视频文件名")
    parser.add_argument('--fps', type=int, default=60, help="视频帧率")
    args = parser.parse_args()
    sensor_dir = Path(args.sensor_dir).resolve()
    force_npz = sensor_dir / "force_data.npz"
    rectify_dir = sensor_dir / "Rectify"
    diff_dir = sensor_dir / "Difference"
    depth_dir = sensor_dir / "Depth"
    # 加载力数据
    data = np.load(force_npz)
    timestamps = data['timestamps']
    force = data['force']
    force_resultant = data['force_resultant']
    force_norm = data['force_norm']
    # ===== 计算全局固定色标范围（P1-P99）=====
    # Force 模长
    all_force_mag = np.linalg.norm(force.reshape(len(force), -1, 3), axis=2)
    force_vmin, force_vmax = np.percentile(all_force_mag, [1, 99])
    if force_vmin == force_vmax:
        force_vmax = force_vmin + 1.0
    print(f"[Info] Force 模长全局范围 (P1-P99): [{force_vmin:.4f}, {force_vmax:.4f}]")

    # ForceNorm Z分量
    if force_norm.ndim == 4 and force_norm.shape[-1] == 3:
        all_fn_z = force_norm[..., 2].ravel()
    else:
        all_fn_z = force_norm.ravel()
    fn_vmin, fn_vmax = np.percentile(all_fn_z, [1, 99])
    if fn_vmin == fn_vmax:
        fn_vmax = fn_vmin + 1.0
    print(f"[Info] ForceNorm Z 全局范围 (P1-P99): [{fn_vmin:.4f}, {fn_vmax:.4f}]")

    # ForceResultant 全局最大绝对值（P99）
    fr_global_maxv = np.percentile(np.abs(force_resultant), 99)
    if fr_global_maxv == 0:
        fr_global_maxv = 1.0
    print(f"[Info] ForceResultant 全局最大绝对值 (P99): {fr_global_maxv:.4f}")

    # 获取所有帧名
    def possible_stems(idx, ts):
        s = str(ts)
        # 支持严格7位和去除末尾0的两种情况
        if '_' in s:
            # 兼容已带编号的情况
            parts = s.split('_', 1)
            idx_str, ts_str = parts[0], parts[1]
        else:
            idx_str, ts_str = f"{idx:06d}", s
        # 保留原始和去除末尾0的版本
        stems = [f"{idx_str}_{ts_str}"]
        if '.' in ts_str:
            ts_trim = ts_str.rstrip('0').rstrip('.') if ts_str.rstrip('0').rstrip('.') else '0'
            if ts_trim != ts_str:
                stems.append(f"{idx_str}_{ts_trim}")
        return stems

    frame_names = []
    for i in range(len(timestamps)):
        for stem in possible_stems(i, timestamps[i]):
            frame_names.append(stem)
    # 读取图片，合成可视化帧
    frames = []
    for i in range(len(timestamps)):
        found = False
        for stem in possible_stems(i, timestamps[i]):
            rectify_path = rectify_dir / f"{stem}.png"
            diff_path = diff_dir / f"{stem}.png"
            depth_path = depth_dir / f"{stem}.png"
            if rectify_path.exists() and diff_path.exists() and depth_path.exists():
                rectify = cv2.imread(str(rectify_path))
                diff = cv2.imread(str(diff_path))
                depth = cv2.imread(str(depth_path))
                h, w = rectify.shape[:2]
                diff = cv2.resize(diff, (w, h))
                depth = cv2.resize(depth, (w, h))
                force_img = visualize_force(force[i], vmin=force_vmin, vmax=force_vmax)
                force_img = cv2.resize(force_img, (w, h))
                force_norm_img = visualize_force_norm(force_norm[i], vmin=fn_vmin, vmax=fn_vmax)
                force_norm_img = cv2.resize(force_norm_img, (w, h))
                force_resultant_img = visualize_force_resultant(force_resultant[i], global_maxv=fr_global_maxv)
                force_resultant_img = cv2.resize(force_resultant_img, (w, h))
                vis = np.concatenate([rectify, diff, depth, force_img, force_norm_img, force_resultant_img], axis=1)
                frames.append(vis)
                found = True
                break
        if not found:
            print(f"[Warn] 缺少图片: {timestamps[i]}")
    if not frames:
        print("[Error] 没有可用帧，无法生成视频")
        return
    # 写视频
    h, w = frames[0].shape[:2]
    out = cv2.VideoWriter(args.output, cv2.VideoWriter_fourcc(*'mp4v'), args.fps, (w, h))
    for frame in frames:
        out.write(frame)
    out.release()
    print(f"[Done] 视频已保存: {args.output}")

if __name__ == '__main__':
    main()
