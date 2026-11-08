from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.compiler.nvenc_stream import NvencStreamCompiler
from engine.linter.sanity_gate import SanityGate


def main() -> None:
    parser = argparse.ArgumentParser(description="Test render for Harmonic Oscillator demo scene.")
    parser.add_argument("--mode", choices=["lint", "snapshot", "stream"], default="lint", help="Render mode to test.")
    parser.add_argument("--duration", type=float, default=3.0, help="Duration for stream render in seconds.")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second.")
    parser.add_argument("--width", type=int, default=1920, help="Frame width.")
    parser.add_argument("--height", type=int, default=1080, help="Frame height.")
    args = parser.parse_args()

    scene_path = PROJECT_ROOT / "examples" / "demo_harmonic_oscillator" / "scene.html"
    if not scene_path.exists():
        raise FileNotFoundError(f"Demo scene not found at {scene_path}")

    output_dir = PROJECT_ROOT / "projects" / "test_render"
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "lint":
        gate = SanityGate()
        result = gate.check_scene(scene_path, width=args.width, height=args.height)
        print("SanityGate validation result:")
        print(f"  Valid: {result.get('valid')}")
        print(f"  Non-black content: {result.get('hasNonBlackContent')}")
        if result.get("errors"):
            print(f"  Errors: {result.get('errors')}")
        sys.exit(0 if result.get("valid") else 1)

    elif args.mode == "snapshot":
        stepper_js = PROJECT_ROOT / "engine" / "compiler" / "headless_stepper.js"
        out_png = output_dir / "demo_snapshot.png"
        cmd = [
            "node",
            str(stepper_js),
            "--mode", "snapshot",
            "--input", str(scene_path),
            "--output", str(out_png),
            "--width", str(args.width),
            "--height", str(args.height),
            "--time", "1.5",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        print(proc.stdout)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            sys.exit(proc.returncode)
        print(f"[SUCCESS] Snapshot captured: {out_png} ({out_png.stat().st_size} bytes)")

    elif args.mode == "stream":
        compiler = NvencStreamCompiler()
        out_mp4 = output_dir / "demo_harmonic_oscillator.mp4"
        compiler.render_scene(
            html_file=scene_path,
            output_mp4=out_mp4,
            duration=args.duration,
            fps=args.fps,
            width=args.width,
            height=args.height,
        )
        print(f"[SUCCESS] Render complete: {out_mp4} ({out_mp4.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
