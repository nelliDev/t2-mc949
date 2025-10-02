#!/bin/bash

# COLMAP Structure-from-Motion Pipeline - CPU Only Version
# Optimized for system COLMAP installation without GPU dependencies

set -e  # Exit on any error

# Use system COLMAP (CPU-only)
COLMAP_EXE="colmap"

# Set up input paths
IMAGE_PATH="./violao/images"
DATABASE_PATH="./violao/database.db"
OUTPUT_PATH="./violao/sparse"
DENSE_PATH="./violao/dense"

echo "📍 Using COLMAP: $COLMAP_EXE (CPU-only mode)"

# Feature extraction (CPU-only)
echo "🔍 Extracting features (CPU)..."
"$COLMAP_EXE" feature_extractor \
   --database_path "$DATABASE_PATH" \
   --image_path "$IMAGE_PATH" \
   --SiftExtraction.use_gpu 0

# Feature matching (CPU-only)
echo "🔗 Matching features (CPU)..."
"$COLMAP_EXE" exhaustive_matcher \
   --database_path "$DATABASE_PATH" \
   --SiftMatching.use_gpu 0

# Bundle adjustment and mapping
echo "📐 Running bundle adjustment..."
"$COLMAP_EXE" mapper \
   --database_path "$DATABASE_PATH" \
   --image_path "$IMAGE_PATH" \
   --output_path "$OUTPUT_PATH"

# Create dense reconstruction directory
mkdir -p "$DENSE_PATH"

# CPU-only reconstruction - skip dense reconstruction and use sparse conversion
echo "💻 CPU-only mode - generating point cloud from sparse reconstruction..."

# Generate PLY from sparse reconstruction
if [ -d "$OUTPUT_PATH/0" ]; then
    echo "🔧 Converting sparse reconstruction to point cloud..."
    "$COLMAP_EXE" model_converter \
        --input_path "$OUTPUT_PATH/0" \
        --output_path "$DENSE_PATH/sparse.ply" \
        --output_type PLY
    
    # Use sparse PLY as the "fused" PLY for cropping
    if [ -f "$DENSE_PATH/sparse.ply" ]; then
        cp "$DENSE_PATH/sparse.ply" "$DENSE_PATH/fused.ply"
        
        # Automated point cloud cropping
        echo "✂️ Cropping point cloud to remove irrelevant points..."
        python3 crop_ply_spatial.py "$DENSE_PATH/fused.ply" "$DENSE_PATH/cropped.ply" \
            --x-min 0.3 --x-max 5.2 \
            --y-min -0.6 --y-max 1.4 \
            --z-min 0.2 --z-max 3.2
        echo "✅ Cropped point cloud saved to $DENSE_PATH/cropped.ply"
        
        RECONSTRUCTION_SUCCESS=true
    else
        echo "⚠️ Warning: Failed to generate sparse point cloud"
        RECONSTRUCTION_SUCCESS=false
    fi
else
    echo "⚠️ Warning: Sparse reconstruction not found at $OUTPUT_PATH/0"
    RECONSTRUCTION_SUCCESS=false
fi

echo "✅ Done! Results:"
echo "  📂 Sparse reconstruction: $OUTPUT_PATH"
if [ "$RECONSTRUCTION_SUCCESS" = true ]; then
    echo "  📂 Point cloud reconstruction: $DENSE_PATH"
    echo "  🎯 Sparse point cloud: $DENSE_PATH/fused.ply"
    echo "  ✂️ Cropped point cloud: $DENSE_PATH/cropped.ply"
    
    # Generate visualization video
    echo "🎬 Generating visualization video..."
    if [ -f "$DENSE_PATH/cropped.ply" ]; then
        python3 viz_python.py --model "$DENSE_PATH/cropped.ply" --fps 5 --seconds 30
        echo "✅ Visualization video generated!"
    else
        echo "⚠️ Warning: cropped.ply not found, skipping visualization"
    fi
else
    echo "  ⚠️ Point cloud generation failed"
    echo "  💡 Check that sparse reconstruction completed successfully"
fi

echo ""
echo "🖥️  CPU-only reconstruction complete!"
echo "📝 Note: This version uses sparse reconstruction for compatibility"
echo "🚀 For dense reconstruction with GPU acceleration, use ./run.sh with custom COLMAP build"
