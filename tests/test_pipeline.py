import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.pipeline import process, read_bin


class PipelineTests(unittest.TestCase):
    def test_missing_invalid_range_duplicates_and_split(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            rows = [
                ['scene_a', 'frame_1', 1, 2, 3, 0.4],
                ['scene_a', 'frame_1', 1, 2, 3, 0.4],  # duplicate
                ['scene_a', 'frame_1', None, 2, 3, 0.4],  # missing
                ['scene_b', 'frame_2', 1, 2, 3, 1.7],  # intensity
                ['scene_b', 'frame_2', 200, 2, 3, 0.4],  # range
                ['scene_b', 'frame_2', 1, 2, 3, 0.4],
                ['scene_c', 'frame_3', 1, 2, 3, 0.4],  # same coordinate, other frame valid
            ]
            csv = base / 'points.csv'
            pd.DataFrame(rows, columns=['scene_id', 'frame_id', 'x', 'y', 'z', 'intensity']).to_csv(csv, index=False)
            out = base / 'processed'
            report = process(csv, out)
            self.assertEqual(report['raw_points'], 7)
            self.assertEqual(report['clean_points'], 3)
            self.assertEqual(report['removed_points'], 4)
            self.assertEqual(report['duplicate_points'], 1)
            self.assertEqual(report['invalid_nonfinite_or_missing'], 1)
            self.assertEqual(report['invalid_intensity'], 1)
            self.assertEqual(report['out_of_range'], 1)
            self.assertEqual(set(pd.read_csv(out / 'dataset_splits.csv')['split']), {'train', 'val', 'test'})
            self.assertEqual(sum(report['split_frames'].values()), 3)
            manifest = json.loads((out / 'dataset_manifest.json').read_text())
            self.assertEqual(len(manifest['dataset_version']), 12)
            with closing(sqlite3.connect(out / 'lidar_metadata.db')) as conn:
                self.assertEqual(conn.execute('select sum(clean_points) from frame_metrics').fetchone()[0], 3)

    def test_kitti_binary_reader(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'frame_001.bin'
            np.array([[1, 2, 3, 0.5], [4, 5, 6, 0.8]], dtype='<f4').tofile(path)
            df = read_bin(path)
            self.assertEqual(len(df), 2)
            self.assertEqual(df['frame_id'].iloc[0], 'frame_001')
            self.assertEqual(df['label'].iloc[0], 'unlabeled')
            self.assertAlmostEqual(float(df['intensity'].iloc[0]), .5, places=5)

    def test_kitti_binary_rejects_invalid_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'broken.bin'
            np.array([1, 2, 3], dtype='<f4').tofile(path)
            with self.assertRaises(ValueError):
                read_bin(path)


if __name__ == '__main__':
    unittest.main()
