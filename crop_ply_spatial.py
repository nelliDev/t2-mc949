#!/usr/bin/env python3
"""
Crop PLY point cloud by removing points outside specified X, Y, Z coordinate ranges.
This removes background/irrelevant points by defining spatial boundaries for the region of interest.
"""

import numpy as np
import struct
import os
import argparse

def read_ply_header(filepath):
    """Read PLY header to understand format and vertex count."""
    with open(filepath, 'rb') as f:
        header_lines = []
        line = f.readline().decode('ascii').strip()
        header_lines.append(line)
        
        while line != 'end_header':
            line = f.readline().decode('ascii').strip()
            header_lines.append(line)
            
        return header_lines, f.tell()

def parse_ply_header(header_lines):
    """Parse PLY header to extract vertex count and properties."""
    vertex_count = 0
    properties = []
    format_type = None
    
    for line in header_lines:
        if line.startswith('format'):
            format_type = line.split()[1]
        elif line.startswith('element vertex'):
            vertex_count = int(line.split()[2])
        elif line.startswith('property'):
            parts = line.split()
            prop_type = parts[1]
            prop_name = parts[2]
            properties.append((prop_type, prop_name))
    
    return vertex_count, properties, format_type

def create_struct_format(properties):
    """Create struct format string from properties."""
    format_str = '<'  # little endian
    for prop_type, prop_name in properties:
        if prop_type == 'float':
            format_str += 'f'
        elif prop_type == 'uchar':
            format_str += 'B'
        elif prop_type == 'int':
            format_str += 'i'
        elif prop_type == 'double':
            format_str += 'd'
    return format_str

def analyze_point_cloud_bounds(filepath, sample_size=10000):
    """Analyze point cloud to understand spatial bounds."""
    print(f"Analyzing spatial bounds of {filepath}...")
    
    header_lines, data_offset = read_ply_header(filepath)
    vertex_count, properties, format_type = parse_ply_header(header_lines)
    format_str = create_struct_format(properties)
    vertex_size = struct.calcsize(format_str)
    
    # Read sample of vertices
    actual_sample_size = min(sample_size, vertex_count)
    vertices = []
    
    with open(filepath, 'rb') as f:
        f.seek(data_offset)
        
        # Read evenly spaced samples
        step = max(1, vertex_count // actual_sample_size)
        
        for i in range(0, vertex_count, step):
            if len(vertices) >= actual_sample_size:
                break
                
            f.seek(data_offset + i * vertex_size)
            vertex_data = f.read(vertex_size)
            if len(vertex_data) != vertex_size:
                break
            vertex = struct.unpack(format_str, vertex_data)
            vertices.append(vertex)
    
    vertices = np.array(vertices)
    
    if len(vertices) == 0:
        print("Error: No vertices read")
        return None
    
    # Extract XYZ coordinates (first 3 columns)
    xyz = vertices[:, :3]
    
    # Calculate bounds
    min_bounds = np.min(xyz, axis=0)
    max_bounds = np.max(xyz, axis=0)
    center = (min_bounds + max_bounds) / 2
    ranges = max_bounds - min_bounds
    
    print(f"\nSpatial Analysis (from {len(vertices)} sample points):")
    print(f"X range: [{min_bounds[0]:.3f}, {max_bounds[0]:.3f}] (range: {ranges[0]:.3f})")
    print(f"Y range: [{min_bounds[1]:.3f}, {max_bounds[1]:.3f}] (range: {ranges[1]:.3f})")
    print(f"Z range: [{min_bounds[2]:.3f}, {max_bounds[2]:.3f}] (range: {ranges[2]:.3f})")
    print(f"Center: ({center[0]:.3f}, {center[1]:.3f}, {center[2]:.3f})")
    
    return {
        'min_bounds': min_bounds,
        'max_bounds': max_bounds,
        'center': center,
        'ranges': ranges,
        'vertex_count': vertex_count,
        'properties': properties
    }

def crop_by_bounds(input_path, output_path, x_range=None, y_range=None, z_range=None, 
                   center_crop_ratio=None, interactive=False):
    """Crop PLY file by removing points outside specified coordinate ranges."""
    
    # First analyze the point cloud
    bounds_info = analyze_point_cloud_bounds(input_path)
    if bounds_info is None:
        return False
    
    # Determine cropping bounds
    if center_crop_ratio is not None:
        # Crop around center with specified ratio
        center = bounds_info['center']
        ranges = bounds_info['ranges']
        new_ranges = ranges * center_crop_ratio
        
        x_range = [center[0] - new_ranges[0]/2, center[0] + new_ranges[0]/2]
        y_range = [center[1] - new_ranges[1]/2, center[1] + new_ranges[1]/2]
        z_range = [center[2] - new_ranges[2]/2, center[2] + new_ranges[2]/2]
        
        print(f"\nUsing center crop with {center_crop_ratio:.1%} of original size:")
    elif interactive:
        # Interactive mode - suggest bounds and ask user
        print("\nSuggested cropping ranges (adjust as needed):")
        min_b, max_b = bounds_info['min_bounds'], bounds_info['max_bounds']
        center = bounds_info['center']
        
        # Suggest 80% crop around center
        margin = 0.1
        x_range = [min_b[0] + (max_b[0] - min_b[0]) * margin, max_b[0] - (max_b[0] - min_b[0]) * margin]
        y_range = [min_b[1] + (max_b[1] - min_b[1]) * margin, max_b[1] - (max_b[1] - min_b[1]) * margin]
        z_range = [min_b[2] + (max_b[2] - min_b[2]) * margin, max_b[2] - (max_b[2] - min_b[2]) * margin]
        
        print(f"Suggested X range: [{x_range[0]:.3f}, {x_range[1]:.3f}]")
        print(f"Suggested Y range: [{y_range[0]:.3f}, {y_range[1]:.3f}]")
        print(f"Suggested Z range: [{z_range[0]:.3f}, {z_range[1]:.3f}]")
        
        # For now, use suggested ranges (in real interactive mode, would prompt user)
        print("Using suggested ranges...")
    else:
        # Use provided ranges or default to no cropping
        min_b, max_b = bounds_info['min_bounds'], bounds_info['max_bounds']
        x_range = x_range or [min_b[0], max_b[0]]
        y_range = y_range or [min_b[1], max_b[1]]
        z_range = z_range or [min_b[2], max_b[2]]
    
    print(f"\nCropping to bounds:")
    print(f"X: [{x_range[0]:.3f}, {x_range[1]:.3f}]")
    print(f"Y: [{y_range[0]:.3f}, {y_range[1]:.3f}]")
    print(f"Z: [{z_range[0]:.3f}, {z_range[1]:.3f}]")
    
    # Read and process full point cloud
    header_lines, data_offset = read_ply_header(input_path)
    vertex_count, properties, format_type = parse_ply_header(header_lines)
    format_str = create_struct_format(properties)
    vertex_size = struct.calcsize(format_str)
    
    cropped_vertices = []
    chunk_size = 50000  # Process in chunks to handle memory
    
    print(f"\nProcessing {vertex_count} vertices in chunks...")
    
    with open(input_path, 'rb') as f:
        f.seek(data_offset)
        
        for chunk_start in range(0, vertex_count, chunk_size):
            chunk_end = min(chunk_start + chunk_size, vertex_count)
            chunk_count = chunk_end - chunk_start
            
            chunk_vertices = []
            for i in range(chunk_count):
                vertex_data = f.read(vertex_size)
                if len(vertex_data) != vertex_size:
                    break
                vertex = struct.unpack(format_str, vertex_data)
                chunk_vertices.append(vertex)
            
            if not chunk_vertices:
                break
            
            chunk_array = np.array(chunk_vertices)
            
            # Apply spatial filtering (XYZ are first 3 columns)
            xyz = chunk_array[:, :3]
            
            mask = ((xyz[:, 0] >= x_range[0]) & (xyz[:, 0] <= x_range[1]) &
                   (xyz[:, 1] >= y_range[0]) & (xyz[:, 1] <= y_range[1]) &
                   (xyz[:, 2] >= z_range[0]) & (xyz[:, 2] <= z_range[1]))
            
            filtered_chunk = chunk_array[mask]
            
            if len(filtered_chunk) > 0:
                cropped_vertices.extend(filtered_chunk.tolist())
            
            progress = min(chunk_end, vertex_count)
            print(f"Processed {progress}/{vertex_count} vertices ({progress/vertex_count*100:.1f}%) - "
                  f"kept {len(cropped_vertices)} so far")
    
    if not cropped_vertices:
        print("Error: No vertices remain after cropping!")
        return False
    
    cropped_vertices = np.array(cropped_vertices)
    
    print(f"\nCropping results:")
    print(f"Original vertices: {vertex_count}")
    print(f"Cropped vertices: {len(cropped_vertices)}")
    print(f"Reduction: {(1 - len(cropped_vertices)/vertex_count)*100:.1f}%")
    print(f"Kept: {len(cropped_vertices)/vertex_count*100:.1f}%")
    
    # Write output PLY file
    write_ply_file(output_path, cropped_vertices, properties, 
                   comments=[f"Spatially cropped from {input_path}",
                            f"X range: [{x_range[0]:.3f}, {x_range[1]:.3f}]",
                            f"Y range: [{y_range[0]:.3f}, {y_range[1]:.3f}]", 
                            f"Z range: [{z_range[0]:.3f}, {z_range[1]:.3f}]",
                            f"Original: {vertex_count}, Cropped: {len(cropped_vertices)}"])
    
    print(f"\nOutput saved to: {output_path}")
    return True

def write_ply_file(output_path, vertices, properties, comments=None):
    """Write vertices to a PLY file."""
    vertex_count = len(vertices)
    
    with open(output_path, 'wb') as f:
        # Write header
        f.write(b'ply\n')
        f.write(b'format binary_little_endian 1.0\n')
        
        if comments:
            for comment in comments:
                f.write(f'comment {comment}\n'.encode('ascii'))
        
        f.write(f'element vertex {vertex_count}\n'.encode('ascii'))
        
        for prop_type, prop_name in properties:
            f.write(f'property {prop_type} {prop_name}\n'.encode('ascii'))
        
        f.write(b'end_header\n')
        
        # Write vertex data
        format_str = create_struct_format(properties)
        
        for vertex in vertices:
            # Convert vertex data to proper types
            converted_vertex = []
            for i, (prop_type, prop_name) in enumerate(properties):
                if prop_type == 'float':
                    converted_vertex.append(float(vertex[i]))
                elif prop_type == 'uchar':
                    converted_vertex.append(int(vertex[i]) % 256)  # Ensure 0-255 range
                elif prop_type == 'int':
                    converted_vertex.append(int(vertex[i]))
                elif prop_type == 'double':
                    converted_vertex.append(float(vertex[i]))
                else:
                    converted_vertex.append(vertex[i])
            
            vertex_data = struct.pack(format_str, *converted_vertex)
            f.write(vertex_data)

def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='Crop PLY point cloud by spatial bounds')
    parser.add_argument('input', help='Input PLY file path')
    parser.add_argument('output', help='Output PLY file path')
    parser.add_argument('--analyze-only', action='store_true', 
                       help='Only analyze bounds without cropping')
    parser.add_argument('--x-min', type=float, help='Minimum X coordinate')
    parser.add_argument('--x-max', type=float, help='Maximum X coordinate') 
    parser.add_argument('--y-min', type=float, help='Minimum Y coordinate')
    parser.add_argument('--y-max', type=float, help='Maximum Y coordinate')
    parser.add_argument('--z-min', type=float, help='Minimum Z coordinate')
    parser.add_argument('--z-max', type=float, help='Maximum Z coordinate')
    parser.add_argument('--center-crop', type=float, metavar='RATIO',
                       help='Crop around center with specified ratio (e.g., 0.8 for 80%)')
    parser.add_argument('--interactive', action='store_true',
                       help='Suggest cropping bounds interactively')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist")
        return 1
    
    if args.analyze_only:
        analyze_point_cloud_bounds(args.input)
        return 0
    
    # Prepare ranges
    x_range = None
    y_range = None  
    z_range = None
    
    if args.x_min is not None or args.x_max is not None:
        if args.x_min is None or args.x_max is None:
            print("Error: Both --x-min and --x-max must be specified")
            return 1
        x_range = [args.x_min, args.x_max]
    
    if args.y_min is not None or args.y_max is not None:
        if args.y_min is None or args.y_max is None:
            print("Error: Both --y-min and --y-max must be specified")
            return 1
        y_range = [args.y_min, args.y_max]
        
    if args.z_min is not None or args.z_max is not None:
        if args.z_min is None or args.z_max is None:
            print("Error: Both --z-min and --z-max must be specified")
            return 1
        z_range = [args.z_min, args.z_max]
    
    success = crop_by_bounds(args.input, args.output, 
                           x_range=x_range, y_range=y_range, z_range=z_range,
                           center_crop_ratio=args.center_crop,
                           interactive=args.interactive)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
