#!/usr/bin/env python3
# -- coding: utf-8 --
"""
Gera um vídeo MP4 orbitando uma nuvem de pontos (.ply) em modo headless (sem CUDA/OpenGL).
- Lê o PLY via Open3D (apenas I/O)
- Renderiza com Matplotlib 3D (backend Agg)
- Grava com FFMpegWriter (libx264)

Exemplo:
  python3 viz_video_matplotlib.py \
    --model etapa_3/points_3d_70_71.ply \
    --seconds 10 --fps 30 \
    --style neon \
    --out renders/out.mp4
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")  # backend headless
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
import open3d as o3d

STYLES = {
    "neon":    dict(bg="black", colormap="turbo",   point_size=3.5, elev=18, az0=-80,  az1=280, axes=0),
    "depth":   dict(bg="white", colormap="viridis", point_size=2.5, elev=15, az0=-60,  az1=300, axes=0),
    "ice":     dict(bg="black", colormap="cividis", point_size=3.0, elev=12, az0=-90,  az1=270, axes=0),
    "inferno": dict(bg="black", colormap="inferno", point_size=3.0, elev=20, az0=-100, az1=260, axes=0),
    "aurora":  dict(bg="black", colormap="plasma",  point_size=3.2, elev=25, az0=-120, az1=240, axes=0),
}

def load_ply(path, max_points=50000):
    """Load and downsample point cloud for faster rendering"""
    pcd = o3d.io.read_point_cloud(path)
    pts = np.asarray(pcd.points)
    cols = np.asarray(pcd.colors) if len(pcd.colors) == len(pcd.points) else None
    
    print(f"Loaded {len(pts)} points from {path}")
    
    # Downsample if too many points
    if len(pts) > max_points:
        indices = np.random.choice(len(pts), max_points, replace=False)
        pts = pts[indices]
        if cols is not None:
            cols = cols[indices]
        print(f"Downsampled to {len(pts)} points for faster rendering")
    
    return pts, cols

def set_equal_axes(ax, pts):
    mins = pts.min(0); maxs = pts.max(0)
    c = (mins + maxs) / 2.0
    r = (maxs - mins).max() / 2.0
    ax.set_xlim(c[0]-r, c[0]+r)
    ax.set_ylim(c[1]-r, c[1]+r)
    ax.set_zlim(c[2]-r, c[2]+r)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="arquivo .ply (nuvem de pontos)")
    ap.add_argument("--seconds", type=int, default=12)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", default="renders/out.mp4")
    ap.add_argument("--max-points", type=int, default=50000, help="Maximum points to render (downsample if more)")

    # estilo pré-definido ou custom
    ap.add_argument("--style", default="neon", choices=list(STYLES.keys())+["custom"])
    ap.add_argument("--bg", default="black")
    ap.add_argument("--colormap", default="turbo")
    ap.add_argument("--point-size", type=float, default=3.0)
    ap.add_argument("--elev", type=float, default=15.0)
    ap.add_argument("--azim-start", type=float, default=-60.0)
    ap.add_argument("--azim-end", type=float, default=300.0)
    ap.add_argument("--axes", type=int, default=0)
    args = ap.parse_args()

    # aplica estilo
    if args.style != "custom":
        s = STYLES[args.style]
        args.bg          = s["bg"]
        args.colormap    = s["colormap"]
        args.point_size  = s["point_size"]
        args.elev        = s["elev"]
        args.azim_start  = s["az0"]
        args.azim_end    = s["az1"]
        args.axes        = s["axes"]

    # carrega nuvem
    pts, cols = load_ply(args.model, args.max_points)
    if pts.size == 0:
        raise RuntimeError("Point cloud vazio (ou arquivo não encontrado).")

    # figura (smaller for faster rendering)
    if args.bg == "black":
        plt.style.use("dark_background")
    fig = plt.figure(figsize=(8, 8), dpi=80)
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor(args.bg)
    ax.set_facecolor(args.bg)
    if not args.axes:
        ax.set_axis_off()

    set_equal_axes(ax, pts)

    # cor: usa cor do PLY, senão colormap por profundidade (Z)
    if cols is None or len(cols) != len(pts):
        z = pts[:, 2]
        sc = ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2],
                        c=z, cmap=args.colormap, s=args.point_size)
    else:
        sc = ax.scatter(pts[:, 0], pts[:, 1], pts[:, 2],
                        c=cols, s=args.point_size)

    # writer (use mpeg4 codec which should be available)
    n_frames = max(1, args.seconds * args.fps)
    writer = FFMpegWriter(
        fps=args.fps,
        codec="mpeg4",
        bitrate=8000
    )

    with writer.saving(fig, args.out, dpi=80):
        print(f"Generating {n_frames} frames...")
        for i in range(n_frames):
            if i % 10 == 0:
                print(f"  Frame {i+1}/{n_frames}")
            az = args.azim_start + (args.azim_end - args.azim_start) * (i / (n_frames - 1))
            ax.view_init(elev=float(args.elev), azim=float(az))
            writer.grab_frame()

    print(f"[OK] Vídeo salvo em: {args.out}")

if __name__ == "__main__":
    main()