#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取 Xense 离线处理生成的 force_data.npz 文件，打印内容结构和部分数据示例。
"""
import numpy as np
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="读取 Xense force_data.npz 文件")
    parser.add_argument('--npz', type=str, required=True, help="force_data.npz 文件路径")
    args = parser.parse_args()
    npz_path = Path(args.npz).resolve()
    if not npz_path.exists():
        print(f"[Error] 文件不存在: {npz_path}")
        return
    data = np.load(npz_path)
    print(f"[Info] 文件 keys: {list(data.keys())}")
    print(f"[Info] timestamps shape: {data['timestamps'].shape}")
    print(f"[Info] force shape: {data['force'].shape}")
    print(f"[Info] force_resultant shape: {data['force_resultant'].shape}")
    print(f"[Info] force_norm shape: {data['force_norm'].shape}")
    # 打印部分数据
    print("\n[Sample] timestamps:", data['timestamps'][:5])
    print("[Sample] force[0] (shape {}):".format(data['force'][0].shape))
    print(data['force'][0])
    print("[Sample] force_resultant[0]:", data['force_resultant'][0])
    print("[Sample] force_norm[0] (shape {}):".format(data['force_norm'][0].shape))
    print(data['force_norm'][0])

if __name__ == '__main__':
    main()
