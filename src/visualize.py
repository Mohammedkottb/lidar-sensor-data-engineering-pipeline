"""Make a static 3D preview image for the project README/portfolio."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


def visualize(input_file: Path, output_image: Path, max_points: int = 2500) -> None:
    df = pd.read_csv(input_file)
    if df.empty:
        raise ValueError('No cleaned data to visualize')
    sample = df.sample(n=min(max_points, len(df)), random_state=42)
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111, projection='3d')
    scatter = ax.scatter(sample['x'], sample['y'], sample['z'], c=sample['intensity'], cmap='viridis', s=5, alpha=0.75)
    ax.set_xlabel('X (meters)')
    ax.set_ylabel('Y (meters)')
    ax.set_zlabel('Z (meters)')
    ax.set_title('Processed 3D point cloud (see dataset manifest for provenance)')
    fig.colorbar(scatter, ax=ax, pad=0.08, shrink=0.65, label='Intensity')
    output_image.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_image, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved visualization: {output_image}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=Path('data/processed/clean_points.csv'))
    parser.add_argument('--output', type=Path, default=Path('data/processed/point_cloud_preview.png'))
    args = parser.parse_args()
    visualize(args.input, args.output)
