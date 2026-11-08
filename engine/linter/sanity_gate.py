"""
Pre-Render Sanity Gate & Autonomous Linter
Validates scene HTML files and verifies YouTube thumbnails against Rule T6 standards.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STEPPER_JS = Path(__file__).resolve().parents[1] / "compiler" / "headless_stepper.js"


class SanityGate:
    """Automated validator and linter that ensures scenes render properly before full compilation."""

    def __init__(self, node_bin: str = "node") -> None:
        self.node_path = shutil.which(node_bin) or node_bin

    def check_scene(
        self,
        html_file: str | Path,
        width: int = 1920,
        height: int = 1080,
    ) -> dict[str, Any]:
        """Runs headless Chromium to check for JS exceptions, missing renderFrame hook, and black screens."""
        path = Path(html_file).resolve()
        if not path.exists():
            return {
                "valid": False,
                "errors": [f"File not found: {path}"],
                "hasNonBlackContent": False,
            }

        content = path.read_text(encoding="utf-8")
        if "window.renderFrame" not in content:
            return {
                "valid": False,
                "errors": ["Missing mandatory 'window.renderFrame' hook in HTML"],
                "hasNonBlackContent": False,
            }

        cmd = [
            self.node_path,
            str(STEPPER_JS),
            "--mode", "lint",
            "--input", str(path),
            "--width", str(width),
            "--height", str(height),
        ]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=25,
            )
            stdout = proc.stdout.strip()
            if proc.returncode == 0:
                data = json.loads(stdout)
                return data
            else:
                try:
                    data = json.loads(stdout)
                    return data
                except Exception:
                    return {
                        "valid": False,
                        "errors": [proc.stderr or stdout],
                        "hasNonBlackContent": False,
                    }
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "hasNonBlackContent": False,
            }

    def check_episode_blueprints(
        self,
        scene_blueprints: list[Path | str],
    ) -> dict[str, Any]:
        """
        Enforces Rule P1: Dedicated Multi-Scene Architecture & Rule M3: Watertight Solid Geometries.
        Verifies that an episode does NOT naively reuse the identical blueprint source across scenes,
        and ensures clipping planes are sealed with planar caps.
        """
        resolved = [Path(p).resolve() for p in scene_blueprints]
        unique_paths = set(resolved)
        errors: list[str] = []

        if len(resolved) > 1 and len(unique_paths) < len(resolved):
            duplicates = {p.name: resolved.count(p) for p in unique_paths if resolved.count(p) > 1}
            errors.append(
                f"Rule P1 Violation: Monolithic blueprint reuse detected. "
                f"Scenes cannot reuse the same blueprint file {duplicates}. "
                f"Each scene must have a dedicated, cinema-grade WebGL blueprint."
            )

        for p in unique_paths:
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="ignore")
                if "localClippingEnabled = true" in text and "SphereGeometry" in text:
                    has_caps = any(term in text for term in ["cap", "RingGeometry", "ShapeGeometry", "CylinderGeometry", "LatheGeometry", "solid", "wedge"])
                    if not has_caps:
                        errors.append(
                            f"Rule M3 Violation in {p.name}: Potential hollow eggshell clipping. "
                            f"SphereGeometry with localClippingEnabled must include flat planar cut caps to prevent open hollow shells."
                        )

        return {
            "valid": len(errors) == 0,
            "scene_count": len(resolved),
            "unique_blueprint_count": len(unique_paths),
            "errors": errors,
        }

    def check_thumbnail(
        self,
        image_path: str | Path,
        width: int = 3840,
        height: int = 2160,
    ) -> dict[str, Any]:
        """
        Evaluates a rendered YouTube thumbnail against Rule T6 Directives:
        1. Downsamples image to 320x180 px (simulating YouTube mobile feed card).
        2. Asserts text bounding-box luminance contrast ratio >= 7.0:1 in top-left quadrant (x: 10..120, y: 10..60).
        3. Asserts bottom-right dead zone (x > 262, y > 151 in downsampled space, corresponding to x > 3150, y > 1820 in 4K)
           has mean luminance < 0.15 and no high-contrast feature edges.
        4. Asserts central hero region (x: 80..240, y: 40..140) has >= 25% of pixels with luminance > 0.40.
        """
        from PIL import Image
        import numpy as np

        path = Path(image_path).resolve()
        if not path.exists():
            return {
                "valid": False,
                "contrast_ratio": 0.0,
                "deadzone_clean": False,
                "hero_luminance_ratio": 0.0,
                "errors": [f"Thumbnail image not found: {path}"],
            }

        img = Image.open(path).convert("RGB")
        small_img = img.resize((320, 180), Image.Resampling.BILINEAR)
        arr = np.array(small_img, dtype=np.float32) / 255.0

        lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]

        errors: list[str] = []

        # 1. Top-left safe-zone typography contrast ratio (x: 10 to 120, y: 10 to 60)
        tl_crop = lum[10:60, 10:120]
        l_text = float(np.percentile(tl_crop, 98))
        l_bg = float(np.percentile(tl_crop, 2))
        contrast_ratio = (l_text + 0.05) / (l_bg + 0.05)

        if contrast_ratio < 7.0:
            errors.append(
                f"Top-left text contrast ratio {contrast_ratio:.2f}:1 is below WCAG AAA 7.0:1 requirement"
            )

        # 2. Bottom-right timestamp dead zone (x > 262, y > 151)
        br_crop = lum[151:180, 262:320]
        mean_br = float(np.mean(br_crop))
        max_br = float(np.max(br_crop))
        std_br = float(np.std(br_crop))

        deadzone_clean = (mean_br < 0.15) and (max_br < 0.40) and (std_br < 0.08)
        if not deadzone_clean:
            errors.append(
                f"Bottom-right deadzone violation: mean_lum={mean_br:.3f} (must be < 0.15), max_lum={max_br:.3f}"
            )

        # 3. Central hero region luminance ratio (x: 80 to 240, y: 40 to 140)
        hero_crop = lum[40:140, 80:240]
        hero_luminance_ratio = float(np.mean(hero_crop > 0.40))
        if hero_luminance_ratio < 0.25:
            errors.append(
                f"Central hero region luminance ratio {hero_luminance_ratio:.1%} is below mandatory 25.0%"
            )

        valid = len(errors) == 0
        return {
            "valid": valid,
            "contrast_ratio": round(contrast_ratio, 2),
            "deadzone_clean": deadzone_clean,
            "hero_luminance_ratio": round(hero_luminance_ratio, 3),
            "errors": errors,
        }


    def check_short_dimensions(
        self,
        video_or_image_path: str | Path,
    ) -> dict[str, Any]:
        """Evaluates rendered Short video or image against 9:16 (1080x1920) and duration constraints."""
        return check_short_dimensions(video_or_image_path)



def check_short_dimensions(
    video_or_image_path: str | Path,
    ffprobe_bin: str = "ffprobe",
) -> dict[str, Any]:
    """
    Validates that a rendered YouTube Short or preview image satisfies:
    1. Dimensions are exactly 1080x1920 (9:16 aspect ratio).
    2. Video duration is strictly between 30.0s and 50.0s (Directive S1).
    """
    path = Path(video_or_image_path).resolve()
    if not path.exists():
        return {
            "valid": False,
            "errors": [f"File not found: {path}"],
            "width": 0,
            "height": 0,
            "duration": 0.0,
            "aspect_ratio": "unknown",
        }

    errors: list[str] = []
    width = 0
    height = 0
    duration = 0.0
    is_video = False

    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            from PIL import Image
            with Image.open(path) as img:
                width, height = img.size
        except Exception as e:
            errors.append(f"Image read error: {e}")
    else:
        is_video = True
        ffprobe_path = shutil.which(ffprobe_bin) or ffprobe_bin
        cmd = [
            ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-show_entries", "stream=width,height,codec_type",
            "-of", "json",
            str(path),
        ]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            data = json.loads(proc.stdout)
            duration = float(data.get("format", {}).get("duration", 0.0))
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    width = int(stream.get("width", 0))
                    height = int(stream.get("height", 0))
                    break
        except Exception as e:
            errors.append(f"ffprobe probe failed: {e}")

    # Assert aspect ratio is exactly 9:16 (1080x1920)
    if width != 1080 or height != 1920:
        errors.append(
            f"Invalid dimensions: {width}x{height}. Expected exactly 1080x1920 (9:16 aspect ratio)."
        )

    # Assert duration between 30.0s and 50.0s
    if is_video:
        if duration < 30.0 or duration > 50.0:
            errors.append(
                f"Invalid duration: {duration:.2f}s. Expected between 30.0s and 50.0s."
            )

    valid = len(errors) == 0
    return {
        "valid": valid,
        "width": width,
        "height": height,
        "aspect_ratio": "9:16" if (width == 1080 and height == 1920) else f"{width}:{height}",
        "duration": round(duration, 3),
        "is_video": is_video,
        "errors": errors,
    }

if __name__ == "__main__":
    gate = SanityGate()
    print("SanityGate loaded successfully.")
