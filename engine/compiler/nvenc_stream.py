"""
Direct Memory-Piped NVENC Stream Compiler
Connects headless Chromium frame buffer output directly into FFmpeg NVIDIA NVENC encoder.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

STEPPER_JS = Path(__file__).resolve().parent / "headless_stepper.js"


class NvencStreamCompiler:
    """Renders HTML scenes via headless Chromium and encodes via NVIDIA NVENC hardware."""

    def __init__(self, node_bin: str = "node", ffmpeg_bin: str = "ffmpeg", ffprobe_bin: str = "ffprobe") -> None:
        self.node_path = shutil.which(node_bin) or node_bin
        self.ffmpeg_path = shutil.which(ffmpeg_bin) or ffmpeg_bin
        self.ffprobe_path = shutil.which(ffprobe_bin) or ffprobe_bin

    def render_scene(
        self,
        html_file: str | Path,
        output_mp4: str | Path,
        duration: float,
        fps: int = 60,
        width: int = 3840,
        height: int = 2160,
        codec: str = "hevc_nvenc",
        quality_cq: int = 18,
    ) -> Path:
        """
        Renders HTML scene to MP4 using hardware NVENC.
        Pipes PNG frame stream from Chromium stdout directly to FFmpeg stdin.
        """
        query_suffix = ""
        if isinstance(html_file, str) and ("?" in html_file or "#" in html_file):
            sep = "?" if "?" in html_file else "#"
            base_part, query_part = html_file.split(sep, 1)
            html_path = Path(base_part).resolve()
            query_suffix = f"{sep}{query_part}"
        else:
            html_path = Path(html_file).resolve()

        out_mp4 = Path(output_mp4).resolve()
        out_mp4.parent.mkdir(parents=True, exist_ok=True)

        if not html_path.exists():
            raise FileNotFoundError(f"Scene HTML not found: {html_path}")

        logger.info(
            f"Rendering {html_path.name} -> {out_mp4.name} ({width}x{height} @ {fps}fps, {duration:.2f}s, {codec})"
        )
        start_time = time.time()

        # 1. Build Node frame stepper command
        node_cmd = [
            self.node_path,
            str(STEPPER_JS),
            "--mode", "stream",
            "--input", f"{html_path}{query_suffix}", 
            "--duration", str(duration),
            "--fps", str(fps),
            "--width", str(width),
            "--height", str(height),
        ]

        # 2. Build FFmpeg NVENC encode command
        ffmpeg_cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "image2pipe",
            "-vcodec", "png",
            "-r", str(fps),
            "-i", "-",  # Read from stdin
            "-c:v", codec,
            "-preset", "p5",
            "-cq", str(quality_cq),
            "-pix_fmt", "yuv420p",
            str(out_mp4),
        ]

        # Launch Node producer with stderr redirected to log file to avoid pipe buffer deadlocks
        err_log_path = out_mp4.with_suffix(".render.log")
        with open(err_log_path, "w", encoding="utf-8") as err_log_file:
            producer = subprocess.Popen(node_cmd, stdout=subprocess.PIPE, stderr=err_log_file)
            consumer = subprocess.Popen(ffmpeg_cmd, stdin=producer.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Allow producer to write directly to consumer
            if producer.stdout:
                producer.stdout.close()

            consumer_stdout, consumer_stderr = consumer.communicate()
            producer.wait()

        # Check producer exit code
        if producer.returncode != 0:
            err_content = err_log_path.read_text(encoding="utf-8", errors="ignore") if err_log_path.exists() else ""
            raise RuntimeError(
                f"Headless Chromium frame stepper failed with exit code {producer.returncode}: {err_content}"
            )

        if consumer.returncode != 0:
            err_msg = consumer_stderr.decode("utf-8", errors="ignore")
            # If hevc_nvenc failed, try h264_nvenc fallback
            if codec == "hevc_nvenc":
                logger.warning(f"hevc_nvenc failed ({err_msg}). Retrying with h264_nvenc...")
                return self.render_scene(
                    html_file, output_mp4, duration, fps, width, height, codec="h264_nvenc", quality_cq=quality_cq
                )
            raise RuntimeError(f"FFmpeg NVENC encoding error: {err_msg}")

        # Post-render duration verification gate
        try:
            probe_cmd = [
                self.ffprobe_path,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(out_mp4),
            ]
            actual_dur = float(subprocess.check_output(probe_cmd, text=True).strip())
            if actual_dur < duration * 0.90:
                raise RuntimeError(
                    f"Rendered video {out_mp4.name} is truncated! Expected {duration:.2f}s, got {actual_dur:.2f}s."
                )
        except Exception as e:
            if "truncated" in str(e):
                raise
            logger.warning(f"Could not probe output duration: {e}")

        # Clean up render log on success
        if err_log_path.exists():
            try:
                err_log_path.unlink()
            except OSError:
                pass

        elapsed = time.time() - start_time
        total_frames = int(round(duration * fps))
        fps_speed = total_frames / max(0.001, elapsed)

        logger.info(
            f"Render complete: {out_mp4.name} in {elapsed:.2f}s ({fps_speed:.1f} fps rendering speed)"
        )
        return out_mp4


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    compiler = NvencStreamCompiler()
    project_root = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
    test_html = project_root / "examples" / "demo_harmonic_oscillator" / "scene.html"
    test_out = project_root / "projects" / "test_render" / "demo_test_1080p.mp4"
    compiler.render_scene(test_html, test_out, duration=3.0, fps=30, width=1920, height=1080)
    print("Render test completed:", test_out.exists(), test_out.stat().st_size)
