#!/bin/bash

# COLMAP Structure-from-Motion Pipeline
# Universal version supporting both custom builds and system installations

set -e  # Exit on any error

# Configuration - Set this to your COLMAP build path or leave empty for system COLMAP
COLMAP_BUILD_PATH="/home/nelli/vscode-prjs/COLMAP/colmap/build/src/colmap/exe"  # Custom build path with GPU support
# COLMAP_BUILD_PATH=""  # Uncomment this line to use system COLMAP

# Set up input paths
IMAGE_PATH="./violao/images"
DATABASE_PATH="./violao/database.db"
OUTPUT_PATH="./violao/sparse"
DENSE_PATH="./violao/dense"

# Determine COLMAP executable
if [ -z "$COLMAP_BUILD_PATH" ]; then
    COLMAP_EXE="colmap"  # Use system COLMAP
else
    COLMAP_EXE="$COLMAP_BUILD_PATH/colmap"  # Use custom build
fi

echo "📍 Using COLMAP: $COLMAP_EXE"

# Feature extraction
echo "🔍 Extracting features..."
"$COLMAP_EXE" feature_extractor \
   --database_path "$DATABASE_PATH" \
   --image_path "$IMAGE_PATH"

# Feature matching
echo "🔗 Matching features..."
"$COLMAP_EXE" exhaustive_matcher \
   --database_path "$DATABASE_PATH"

# Bundle adjustment and mapping
echo "📐 Running bundle adjustment..."
"$COLMAP_EXE" mapper \
   --database_path "$DATABASE_PATH" \
   --image_path "$IMAGE_PATH" \
   --output_path "$OUTPUT_PATH"

# Create dense reconstruction directory
mkdir -p "$DENSE_PATH"

# Check if COLMAP was compiled with CUDA support
if "$COLMAP_EXE" help 2>&1 | grep -q "with CUDA"; then
    echo "✅ CUDA support detected in COLMAP - proceeding with dense reconstruction..."
    
    # Image undistortion
    echo "  📐 Undistorting images..."
    "$COLMAP_EXE" image_undistorter \
        --image_path "$IMAGE_PATH" \
        --input_path "$OUTPUT_PATH/0" \
        --output_path "$DENSE_PATH" \
        --output_type COLMAP

    # Patch match stereo
    echo "  🔍 Computing stereo depth maps..."
    "$COLMAP_EXE" patch_match_stereo \
        --workspace_path "$DENSE_PATH" \
        --workspace_format COLMAP

    # Stereo fusion
    echo "  ⚡ Fusing depth maps into point cloud..."
    "$COLMAP_EXE" stereo_fusion \
        --workspace_path "$DENSE_PATH" \
        --workspace_format COLMAP \
        --input_type geometric \
        --output_path "$DENSE_PATH/fused.ply"

    # Automated point cloud cropping
    echo "✂️ Cropping point cloud to remove irrelevant points..."
    if [ -f "$DENSE_PATH/fused.ply" ]; then
        python3 crop_ply_spatial.py "$DENSE_PATH/fused.ply" "$DENSE_PATH/cropped.ply" \
            --x-min 0.3 --x-max 5.2 \
            --y-min -0.6 --y-max 1.4 \
            --z-min 0.2 --z-max 3.2
        echo "✅ Cropped point cloud saved to $DENSE_PATH/cropped.ply"
    else
        echo "⚠️ Warning: fused.ply not found, skipping cropping"
    fi
    
    DENSE_SUCCESS=true
else
    echo "⚠️ COLMAP was compiled without CUDA support - skipping dense reconstruction"
    echo "🔄 Generating point cloud from sparse reconstruction instead..."
    
    # Generate PLY from sparse reconstruction as fallback
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
            
            DENSE_SUCCESS=true
        else
            echo "⚠️ Warning: Failed to generate sparse point cloud"
            DENSE_SUCCESS=false
        fi
    else
        echo "⚠️ Warning: Sparse reconstruction not found at $OUTPUT_PATH/0"
        DENSE_SUCCESS=false
    fi
fi

echo "✅ Done! Results:"
echo "  📂 Sparse reconstruction: $OUTPUT_PATH"
if [ "$DENSE_SUCCESS" = true ]; then
    echo "  📂 Dense reconstruction: $DENSE_PATH"
    if [ -f "$DENSE_PATH/fused.ply" ]; then
        # Check if this is dense or sparse reconstruction
        if "$COLMAP_EXE" help 2>&1 | grep -q "with CUDA"; then
            echo "  🎯 Dense point cloud: $DENSE_PATH/fused.ply"
        else
            echo "  🎯 Sparse point cloud: $DENSE_PATH/fused.ply"
        fi
    fi
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
