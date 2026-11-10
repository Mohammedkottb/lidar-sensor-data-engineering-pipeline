"""Generate explicitly synthetic, KITTI-like point records for a reproducible demo."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def generate(output_path: Path, seed: int = 42, frames: int = 12, points_per_frame: int = 100) -> int:
    rng = np.random.default_rng(seed)
    rows = []
    for frame_no in range(frames):
        positions = rng.normal(loc=[10.0, 0.0, 1.0], scale=[9.0, 6.0, 1.5], size=(points_per_frame, 3))
        intensities = rng.random(points_per_frame)
        labels = rng.choice(['vehicle_simulated', 'pedestrian_simulated', 'background_simulated'], size=points_per_frame)
        for i in range(points_per_frame):
            rows.append({
                'scene_id': f'scene_{frame_no // 2:02d}',
                'frame_id': f'frame_{frame_no:03d}',
                'timestamp_ms': 1730000000000 + frame_no * 100,
                'x': float(positions[i, 0]),
                'y': float(positions[i, 1]),
                'z': float(positions[i, 2]),
                'intensity': float(intensities[i]),
                'label': str(labels[i]),
            })
    df = pd.DataFrame(rows)
    # Intentionally insert invalid samples and repeated observations for demo/testing.
    df.loc[0, 'x'] = np.nan
    df.loc[1, 'intensity'] = 1.5
    df.loc[2, 'z'] = np.inf
    df.loc[3, 'x'] = 200.0
    df = pd.concat([df, df.iloc[[4, 305]]], ignore_index=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    meta = {
        'provenance': 'synthetic',
        'description': 'Generated with NumPy; not real sensor measurements. Labels are simulated, not verified annotations.',
        'random_seed': seed,
        'frames': frames,
        'points_per_frame_before_injections': points_per_frame,
    }
    output_path.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(f'Generated {len(df)} synthetic point records in {output_path}')
    return len(df)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate synthetic LiDAR-style CSV input')
    parser.add_argument('--output', type=Path, default=Path('data/raw/sample_points.csv'))
    args = parser.parse_args()
    generate(args.output)
