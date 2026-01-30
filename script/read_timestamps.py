#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取timestamps.npy并打印内容
用法：python read_timestamps.py --npy <path/to/timestamps.npy>
"""
import numpy as np
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="读取timestamps.npy并打印内容")
    parser.add_argument('--npy', type=str, required=True, help='timestamps.npy 文件路径')
    args = parser.parse_args()
    arr = np.load(args.npy)
    print(f"shape: {arr.shape}")
    for i, v in enumerate(arr):
        print(f"{i}: {v}")
