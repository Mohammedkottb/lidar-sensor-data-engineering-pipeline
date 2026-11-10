# LiDAR & Sensor Data Engineering Pipeline

A reproducible **Python portfolio project** inspired by the data-engineering needs of teams working with LiDAR/3D sensor data. It ingests, cleans, validates, documents, and prepares point-record datasets for downstream analytics and model development.

> **Data honesty:** Bundled sample data is **synthetic**, not real LiDAR sensor measurements. Its labels are **simulated annotations**, not verified ground truth. This is a portfolio prototype, not a production sensor-processing stack or trained AI model. It is not affiliated with Electronic Photonics.

## Pipeline

```
Synthetic CSV sample OR KITTI-style .bin (x,y,z,intensity)
    -> input validation -> finite/required values
    -> intensity filter -> distance filter
    -> frame-local duplicate removal
    -> point-level clean CSV + quality KPIs
    -> scene-level train/val/test splits
    -> SHA-256 dataset fingerprint + manifest
    -> SQLite metadata + 3D visualization
```

## Tech stack

- **Python, NumPy, Pandas:** data ingestion, cleaning, 3D distances, statistics
- **SQLite / SQL:** persist frame metrics, split metadata, quality summary
- **SHA-256 dataset manifests:** reproducible fingerprints to identify dataset versions
- **matplotlib:** point-cloud-like 3D visualization
- **unittest:** automated validation of expected behavior
- **Git:** source version control (DVC integration is an optional next milestone)

## Quick start (Windows PowerShell / VS Code terminal)

Run these commands **from the project folder**:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe src/generate_sample.py
.venv\Scripts\python.exe src/pipeline.py
.venv\Scripts\python.exe src/visualize.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

If Python is already installed with NumPy/Pandas/matplotlib, these commands also work after dependencies are installed:

```powershell
python src/generate_sample.py
python src/pipeline.py
python src/visualize.py
python -m unittest discover -s tests -v
```

## Input formats

1. **CSV:** required `frame_id,x,y,z,intensity`. Optional: `scene_id,timestamp_ms,label`. If `scene_id` is missing, each frame becomes its own scene for splitting. Input provenance is `unspecified` unless paired with a `.meta.json` file.
2. **KITTI-style `.bin`:** each point stores four **little-endian float32** values (`x,y,z,intensity`). All points from the same file are a frame; the directory name supplies `scene_id`. No labels are assumed.

Process a `.bin` file:

```powershell
.venv\Scripts\python.exe src/pipeline.py --input data/raw/example.bin
```

Or a directory recursively containing `.bin` files:

```powershell
.venv\Scripts\python.exe src/pipeline.py --input data/raw/kitti_frames
```

**Important:** binary point formats differ among sensors. Do not interpret arbitrary `.bin` files as KITTI format. Intensity filtering defaults to `0..1`; adjust via `--max-intensity` if the real sensor has a different known scale. The range threshold defaults to 120 m (`--max-distance`). Calibration, timestamps, coordinate transforms, semantic labels and sensor synchronization are outside the scope of this prototype.

## Outputs (`data/processed/`)

| File | Purpose |
|---|---|
| `clean_points.csv` | Cleaned points with `distance_m` |
| `frame_metrics.csv` | Per-frame raw/clean counts and mean intensity/range |
| `quality_report.json` | Count of each rejection reason and retention percentage |
| `dataset_splits.csv` | Assigned train/validation/test split for each frame |
| `train.csv`, `val.csv`, `test.csv` | Prepared clean datasets grouped by `scene_id` |
| `dataset_manifest.json` | Source checksums, cleaning rules, provenance, output fingerprint, dataset version |
| `lidar_metadata.db` | SQL tables `frame_metrics`, `quality_summary`, `dataset_splits` |
| `point_cloud_preview.png` | Static 3D preview colored by intensity |

### Split method / limitation

All points from the same `scene_id` go to the same split. For 3+ scenes the pipeline assigns training, validation and test groups; for fewer than 3, it leaves all frames in training rather than pretend to produce meaningful splits. Scenes from the **same real drive/recording** may still be correlated, so production evaluation needs session/vehicle/geography-level separation and verified labels.

### Dataset versioning

The manifest records SHA-256 hashes for each input and for the cleaned CSV, plus a short `dataset_version`. This detects changes but is **not** a substitute for DVC storage, reproducible environments or data lineage. Optional next step to learn DVC:

```powershell
python -m pip install dvc
# After initializing a Git repository:
dvc init
dvc add data/raw/sample_points.csv
# git add .dvc .dvcignore data/raw/sample_points.csv.dvc
```

Do **not** claim DVC was used until you actually run and commit the DVC steps.

## Quality rules

1. Reject null/non-numeric/non-finite X/Y/Z/intensity or missing scene/frame IDs.
2. Reject intensity outside `[0, max_intensity]`.
3. Reject points farther than `max_distance` meters from origin.
4. Drop exact repeats of X/Y/Z/intensity **within the same scene and frame only**.
5. Report per-stage rejection counts, overall point retention and frame-level KPIs.

These are simplified engineering rules, not universal sensor-validity standards.

## Folder structure

```
EP_LiDAR_Data_Engineering/
├── src/
│   ├── generate_sample.py
│   ├── pipeline.py
│   └── visualize.py
├── tests/
│   └── test_pipeline.py
├── data/
│   ├── raw/sample_points.csv
│   └── processed/ (generated outputs)
├── requirements.txt
└── README.md
```

## Resume bullet — use only after you run and understand the project

**LiDAR & Sensor Data Processing Pipeline | Personal Project**  
Developed a Python-based prototype for point-cloud-style data ingestion and validation using NumPy and Pandas; generated quality reports and frame metrics, persisted metadata in SQLite, prepared scene-based dataset splits, and documented dataset fingerprints using SHA-256. Tested on synthetic data with optional KITTI-style `.bin` ingestion support.

## Next improvements

Add a properly sourced open real LiDAR dataset, a verified annotation schema, DVC remote storage, Linux run evidence, and a CI workflow before describing those as implemented.

### Example output (synthetic demo)

![3D point cloud visualization from synthetic sample](docs/point_cloud_preview.png)

The sample quality-report snapshot is included at [`docs/sample_quality_report.json`](docs/sample_quality_report.json). Run the pipeline on your own system to reproduce it. On Windows you can also double-click `RUN_WINDOWS.bat` instead of typing the setup commands manually.
