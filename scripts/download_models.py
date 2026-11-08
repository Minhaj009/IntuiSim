from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[1]))
MODELS_DIR = PROJECT_ROOT / "assets" / "models" / "kokoro"
WHISPER_DIR = PROJECT_ROOT / "assets" / "models" / "whisper"

KOKORO_BASE_URL = "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main"
FILES_TO_DOWNLOAD = [
    {
        "filename": "kokoro-v1.0.onnx",
        "url": f"{KOKORO_BASE_URL}/kokoro-v1.0.onnx",
        "dest": MODELS_DIR / "kokoro-v1.0.onnx",
    },
    {
        "filename": "voices-v1.0.bin",
        "url": f"{KOKORO_BASE_URL}/voices-v1.0.bin",
        "dest": MODELS_DIR / "voices-v1.0.bin",
    },
]


def format_size(bytes_val: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def download_with_progress(url: str, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".download")

    req = urllib.request.Request(url, headers={"User-Agent": "IntuiSim-Model-Downloader"})

    with urllib.request.urlopen(req) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        block_size = 1024 * 64
        start_time = time.time()

        with open(temp_path, "wb") as f:
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if total_size > 0:
                    percent = downloaded / total_size * 100.0
                    bar_len = 30
                    filled = int(bar_len * downloaded / total_size)
                    bar = "=" * filled + ">" + " " * max(0, bar_len - filled - 1)
                    if filled >= bar_len:
                        bar = "=" * bar_len
                    elapsed = max(0.001, time.time() - start_time)
                    speed = downloaded / elapsed
                    sys.stdout.write(
                        f"\r[{bar}] {percent:5.1f}% ({format_size(downloaded)} / {format_size(total_size)}) @ {format_size(speed)}/s"
                    )
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\rDownloaded {format_size(downloaded)}")
                    sys.stdout.flush()

    sys.stdout.write("\n")
    temp_path.replace(dest_path)


def main() -> None:
    print("=" * 60)
    print("IntuiSim Neural Model Downloader")
    print("=" * 60)
    print(f"Target Kokoro directory: {MODELS_DIR}")
    print(f"Target Whisper directory: {WHISPER_DIR}\n")

    for item in FILES_TO_DOWNLOAD:
        dest = item["dest"]
        if dest.exists() and dest.stat().st_size > 0:
            print(f"[OK] {item['filename']} already exists ({format_size(dest.stat().st_size)}).")
        else:
            print(f"Downloading {item['filename']} from {item['url']} ...")
            download_with_progress(item["url"], dest)
            print(f"[COMPLETED] {item['filename']} saved to {dest}")

    print("\n" + "=" * 60)
    print("Faster-Whisper Model Information")
    print("=" * 60)
    print(
        "Faster-Whisper models (e.g. 'large-v3', 'base') do not require manual pre-download.\n"
        f"When AudioAligner is first instantiated, faster-whisper will automatically fetch\n"
        f"and cache model weights directly to:\n  {WHISPER_DIR}\n"
    )
    print("[SUCCESS] All essential offline neural models are verified.")


if __name__ == "__main__":
    main()
