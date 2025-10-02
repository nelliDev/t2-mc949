# 3D Reconstruction and Visualization Pipeline

A complete pipeline for 3D reconstruction from photographs using COLMAP, with point cloud processing and visualization tools.

## Overview

This project provides tools for:
- **3D Reconstruction**: Convert a series of photographs into 3D point clouds using COLMAP
- **Point Cloud Processing**: Crop and filter point clouds spatially 
- **Visualization**: Generate rotating video visualizations of 3D models

## Project Structure

```
├── run-cpu.sh              # COLMAP pipeline (CPU-only)
├── run-cuda.sh             # COLMAP pipeline (GPU-accelerated)
├── crop_ply_spatial.py     # Point cloud spatial cropping tool
├── viz_python.py           # 3D visualization and video generation
├── violao/                 # Example dataset (guitar reconstruction)
│   ├── images/             # Input photographs
│   ├── sparse/             # Sparse reconstruction output
│   └── dense/              # Dense reconstruction output
└── renders/                # Generated videos and visualizations
```

## Requirements

### System Dependencies
- **COLMAP**: Structure-from-Motion software
  - GPU version recommended for faster processing
  - CPU-only version supported
- **FFmpeg**: For video generation

### Python Dependencies
```bash
pip install numpy open3d matplotlib
```

## Usage

### 1. 3D Reconstruction

#### Using GPU-accelerated COLMAP (recommended):
```bash
chmod +x run-cuda.sh
./run-cuda.sh
```

#### Using CPU-only COLMAP:
```bash
chmod +x run-cpu.sh
./run-cpu.sh
```

**Input**: Place your photographs in `violao/images/` directory
**Output**: 
- Sparse reconstruction: `violao/sparse/`
- Dense point cloud: `violao/dense/fused.ply`

### 2. Point Cloud Processing

Crop point clouds to remove background and focus on the object of interest:

```bash
python3 crop_ply_spatial.py \
    --input violao/dense/fused.ply \
    --output violao/dense/cropped.ply \
    --x_min -1.0 --x_max 1.0 \
    --y_min -1.0 --y_max 1.0 \
    --z_min -0.5 --z_max 2.0
```

### 3. Video Visualization

Generate rotating videos of your 3D models:

```bash
python3 viz_python.py \
    --model violao/dense/cropped.ply \
    --seconds 10 \
    --fps 30 \
    --style neon \
    --out renders/out.mp4
```

**Available styles**: `neon`, `depth`, `ice`, `inferno`, `aurora`

## Pipeline Workflow

1. **Capture Photos**: Take multiple overlapping photos of your subject from different angles
2. **Place Images**: Copy photos to `violao/images/` directory
3. **Run Reconstruction**: Execute `./run-cuda.sh` or `./run-cpu.sh`
4. **Process Point Cloud**: Use `crop_ply_spatial.py` to clean up the reconstruction
5. **Generate Visualization**: Create videos with `viz_python.py`

## Configuration

### COLMAP Settings
Edit the shell scripts to adjust:
- Feature extraction parameters
- Matching settings
- Dense reconstruction quality
- GPU vs CPU usage

### Visualization Options
The visualization script supports multiple rendering styles and customizable parameters:
- Duration and frame rate
- Camera movement patterns
- Color schemes and lighting
- Point cloud downsampling for performance

## Example Dataset

The included `violao/` directory contains an example reconstruction of a guitar (violão in Portuguese), demonstrating the complete pipeline from input photos to final 3D model.

## Tips for Best Results

1. **Photography**:
   - Take 50-100+ overlapping photos
   - Maintain consistent lighting
   - Include the entire object from multiple angles
   - Avoid reflective or transparent surfaces

2. **Processing**:
   - Use GPU acceleration when available
   - Adjust cropping bounds based on your specific object
   - Experiment with different visualization styles

3. **Performance**:
   - Large point clouds may need downsampling for video generation
   - Consider using lower resolution for preview renders

## License

This project is provided as-is for educational and research purposes.
