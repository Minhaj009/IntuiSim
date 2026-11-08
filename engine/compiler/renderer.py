"""
Standalone Scene Renderer CLI for IntuiSim
Renders HTML visual blueprints to MP4 using headless Chromium and hardware NVENC.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT_DIR = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.compiler.nvenc_stream import NvencStreamCompiler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SceneRenderer")


def main():
    parser = argparse.ArgumentParser(description="Render IntuiSim HTML scene to NVENC MP4.")
    parser.add_argument("--scene", type=int, default=1, help="Scene number (1 to 5). Default: 1")
    parser.add_argument("--input", type=str, default="", help="Path to input HTML file")
    parser.add_argument("--output", type=str, default="", help="Path to output MP4 file")
    parser.add_argument("--duration", type=float, default=196.448, help="Scene duration in seconds")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second. Default: 30")
    parser.add_argument("--width", type=int, default=1920, help="Width in pixels. Default: 1920")
    parser.add_argument("--height", type=int, default=1080, help="Height in pixels. Default: 1080")
    parser.add_argument("--codec", type=str, default="hevc_nvenc", help="NVENC codec. Default: hevc_nvenc")
    parser.add_argument("--cq", type=int, default=18, help="NVENC CQ quality. Default: 18")

    args = parser.parse_args()

    compiler = NvencStreamCompiler()

    if args.input:
        input_path = Path(args.input)
    else:
        # Default based on scene number
        if args.scene == 1:
            input_path = ROOT_DIR / "projects" / "ep01_silicon_atom_sp3" / "scenes" / "scene_001.html"
            if not input_path.exists():
                input_path = ROOT_DIR / "vault" / "semiconductors" / "ep01_scene1_anomaly.html"
        else:
            input_path = ROOT_DIR / "projects" / "ep01_silicon_atom_sp3" / "scenes" / f"scene_{args.scene:03d}.html"

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = ROOT_DIR / "projects" / "ep01_silicon_atom_sp3" / "dist" / f"scene_{args.scene:03d}_visual.mp4"

    logger.info(f"Rendering Scene {args.scene}: {input_path} -> {output_path}")
    logger.info(f"Config: {args.width}x{args.height} @ {args.fps}fps, {args.duration:.3f}s, codec={args.codec}, cq={args.cq}")

    compiler.render_scene(
        html_file=input_path,
        output_mp4=output_path,
        duration=args.duration,
        fps=args.fps,
        width=args.width,
        height=args.height,
        codec=args.codec,
        quality_cq=args.cq
    )

    logger.info(f"[SUCCESS] Scene {args.scene} rendered: {output_path} ({output_path.stat().st_size / (1024*1024):.2f} MB)")


if __name__ == "__main__":
    main()
