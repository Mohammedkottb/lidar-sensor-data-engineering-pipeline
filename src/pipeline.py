"""Ingest, validate, deduplicate, report, split and version LiDAR-style point records.

Supports synthetic CSV demo and KITTI-style .bin files of float32 [x,y,z,intensity].
This is an educational data pipeline, not sensor calibration or model training.
"""
import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = {'frame_id', 'x', 'y', 'z', 'intensity'}
COORDS = ['x', 'y', 'z']


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_bin(path: Path) -> pd.DataFrame:
    """KITTI-style point cloud: little-endian float32 xyz + intensity per point."""
    binary = np.fromfile(path, dtype='<f4')
    if binary.size % 4:
        raise ValueError(f'{path}: expected 4 float32 values per point (x,y,z,intensity)')
    points = binary.reshape(-1, 4)
    result = pd.DataFrame(points, columns=['x', 'y', 'z', 'intensity'])
    result.insert(0, 'frame_id', path.stem)
    result.insert(0, 'scene_id', path.parent.name)
    result['label'] = 'unlabeled'
    return result


def read_input(path: Path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Input does not exist: {path}')
    if path.is_dir():
        files = sorted(path.rglob('*.bin'))
        if not files:
            raise ValueError(f'No .bin files found in {path}')
        frames = [read_bin(file) for file in files]
        return pd.concat(frames, ignore_index=True), files, 'KITTI-style BIN (source unverified)'
    if path.suffix.lower() == '.bin':
        return read_bin(path), [path], 'KITTI-style BIN (source unverified)'
    if path.suffix.lower() == '.csv':
        meta_path = path.with_suffix('.meta.json')
        provenance = 'CSV (source unspecified)'
        if meta_path.exists():
            provenance = json.loads(meta_path.read_text(encoding='utf-8')).get('provenance', provenance)
        return pd.read_csv(path), [path], provenance
    raise ValueError('Supported input: .csv, .bin, or a directory of .bin files')


def assign_splits(frame_metrics: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Split by scene_id, not by individual points, to reduce intra-scene leakage."""
    result = frame_metrics.copy()
    scenes = sorted(result['scene_id'].astype(str).unique().tolist())
    rng = np.random.default_rng(seed)
    shuffled = list(rng.permutation(scenes))
    n = len(shuffled)
    if n >= 3:
        n_train = max(1, int(round(n * 0.7)))
        n_train = min(n_train, n - 2)
        n_val = max(1, int(round(n * 0.15)))
        n_val = min(n_val, n - n_train - 1)
    else:
        n_train = n
        n_val = 0
    mapping = {scene: 'train' for scene in shuffled[:n_train]}
    mapping.update({scene: 'val' for scene in shuffled[n_train:n_train + n_val]})
    mapping.update({scene: 'test' for scene in shuffled[n_train + n_val:]})
    result['split'] = result['scene_id'].astype(str).map(mapping)
    return result


def process(input_path: Path, output_dir: Path, max_distance: float = 120.0,
            max_intensity: float = 1.0, split_seed: int = 42) -> dict:
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    if max_distance <= 0 or max_intensity <= 0:
        raise ValueError('max-distance and max-intensity must be positive')
    output_dir.mkdir(parents=True, exist_ok=True)
    raw, input_files, provenance = read_input(input_path)
    missing = REQUIRED - set(raw.columns)
    if missing:
        raise ValueError(f'Missing CSV columns: {sorted(missing)}')
    if raw.empty:
        raise ValueError('Input contains no point records')
    data = raw.copy()
    if 'scene_id' not in data.columns:
        data['scene_id'] = data['frame_id'].astype('string')
    if 'label' not in data.columns:
        data['label'] = 'unlabeled'
    for col in ['x', 'y', 'z', 'intensity']:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    # All four numeric values and identifiers must exist and be finite.
    valid_numeric = np.isfinite(data[['x', 'y', 'z', 'intensity']].to_numpy(dtype=float)).all(axis=1)
    valid_ids = data[['scene_id', 'frame_id']].notna().all(axis=1).to_numpy()
    invalid_numeric_or_id = ~(valid_numeric & valid_ids)
    invalid_count = int(invalid_numeric_or_id.sum())
    data = data.loc[~invalid_numeric_or_id].copy()

    intensity_ok = data['intensity'].between(0, max_intensity)
    invalid_intensity = int((~intensity_ok).sum())
    data = data.loc[intensity_ok].copy()

    data['distance_m'] = np.linalg.norm(data[COORDS].to_numpy(dtype=float), axis=1)
    distance_ok = data['distance_m'].le(max_distance)
    out_of_range = int((~distance_ok).sum())
    data = data.loc[distance_ok].copy()

    # Same coordinate within different frames is NOT automatically a duplicate.
    duplicates = data.duplicated(subset=['scene_id', 'frame_id', 'x', 'y', 'z', 'intensity'])
    duplicate_points = int(duplicates.sum())
    data = data.loc[~duplicates].copy().reset_index(drop=True)
    data.to_csv(output_dir / 'clean_points.csv', index=False)

    original_frames = raw.copy()
    if 'scene_id' not in original_frames.columns:
        original_frames['scene_id'] = original_frames['frame_id'].astype('string')
    original_frames = original_frames.dropna(subset=['scene_id', 'frame_id'])
    raw_counts = original_frames.groupby(['scene_id', 'frame_id'], as_index=False).size().rename(columns={'size': 'raw_points'})
    if data.empty:
        metrics = raw_counts.copy()
        metrics['clean_points'] = 0
        metrics['mean_distance_m'] = np.nan
        metrics['mean_intensity'] = np.nan
    else:
        clean_metrics = data.groupby(['scene_id', 'frame_id'], as_index=False).agg(
            clean_points=('x', 'size'),
            mean_distance_m=('distance_m', 'mean'),
            mean_intensity=('intensity', 'mean'),
        )
        metrics = raw_counts.merge(clean_metrics, how='left', on=['scene_id', 'frame_id'])
        metrics['clean_points'] = metrics['clean_points'].fillna(0).astype(int)
    metrics['removed_points'] = metrics['raw_points'] - metrics['clean_points']
    metrics = assign_splits(metrics, split_seed)
    metrics.to_csv(output_dir / 'frame_metrics.csv', index=False)
    metrics[['scene_id', 'frame_id', 'split']].to_csv(output_dir / 'dataset_splits.csv', index=False)

    split_map = metrics.set_index(['scene_id', 'frame_id'])['split']
    if data.empty:
        data['split'] = pd.Series(dtype=str)
    else:
        data['split'] = [split_map[(s, f)] for s, f in zip(data['scene_id'], data['frame_id'])]
    for group in ['train', 'val', 'test']:
        data.loc[data['split'].eq(group)].drop(columns=['split']).to_csv(output_dir / f'{group}.csv', index=False)

    cleaned_hash = sha256_file(output_dir / 'clean_points.csv')
    quality = {
        'raw_points': int(len(raw)),
        'invalid_nonfinite_or_missing': invalid_count,
        'invalid_intensity': invalid_intensity,
        'out_of_range': out_of_range,
        'duplicate_points': duplicate_points,
        'clean_points': int(len(data)),
        'removed_points': int(len(raw) - len(data)),
        'retention_pct': round(100 * len(data) / len(raw), 2),
        'frames': int(len(metrics)),
        'scenes': int(metrics['scene_id'].nunique()),
        'split_frames': {name: int((metrics['split'] == name).sum()) for name in ['train', 'val', 'test']},
    }
    (output_dir / 'quality_report.json').write_text(json.dumps(quality, indent=2), encoding='utf-8')
    manifest = {
        'project': 'LiDAR & Sensor Data Processing Pipeline',
        'provenance': provenance,
        'sensor_format': '.csv or KITTI-style float32 .bin (xyz and intensity)',
        'input_files_sha256': {str(file): sha256_file(file) for file in input_files},
        'clean_dataset_sha256': cleaned_hash,
        'dataset_version': cleaned_hash[:12],
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'validation_rules': {'max_distance_m': max_distance, 'intensity_min': 0, 'intensity_max': max_intensity},
        'annotations_note': 'Any labels in the bundled demo are synthetic, not verified human annotations.',
        'split_method': 'By scene_id where 3 or more scenes exist; too few scenes produce train-only split.',
    }
    (output_dir / 'dataset_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    # sqlite3's context manager commits/rolls back but does not close the connection.
    # closing() releases the DB file handle so Windows can remove test temp folders.
    with closing(sqlite3.connect(output_dir / 'lidar_metadata.db')) as conn:
        with conn:
            metrics.to_sql('frame_metrics', conn, if_exists='replace', index=False)
            pd.DataFrame([{
                **{k: v for k, v in quality.items() if k != 'split_frames'},
                'dataset_version': manifest['dataset_version'],
                'provenance': provenance,
            }]).to_sql('quality_summary', conn, if_exists='replace', index=False)
            metrics[['scene_id', 'frame_id', 'split']].to_sql('dataset_splits', conn, if_exists='replace', index=False)
    return quality


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process LiDAR-style CSV or KITTI-style .bin data')
    parser.add_argument('--input', type=Path, default=Path('data/raw/sample_points.csv'))
    parser.add_argument('--output', type=Path, default=Path('data/processed'))
    parser.add_argument('--max-distance', type=float, default=120.0)
    parser.add_argument('--max-intensity', type=float, default=1.0)
    args = parser.parse_args()
    print(json.dumps(process(args.input, args.output, args.max_distance, args.max_intensity), indent=2))
