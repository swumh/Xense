import numpy as np
from pathlib import Path

def main():
    npz_path = Path('./data/20260128_170658/OG000724/force_data.npz')
    data = np.load(npz_path)
    print('timestamps:', data['timestamps'][:10])
    print('force_data.npz keys:', list(data.keys()))
    print('force_data.npz timestamps shape:', data['timestamps'].shape)
    print('force_data.npz force shape:', data['force'].shape)

if __name__ == '__main__':
    main()
