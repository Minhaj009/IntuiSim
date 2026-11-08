"""
Word and segment alignment engine utilizing Faster-Whisper with automatic CUDA DLL registration and CPU fallback.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import soundfile as sf
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_WHISPER_DIR = PROJECT_ROOT / "assets" / "models" / "whisper"


def _register_cuda_dll_dirs() -> None:
    """On Windows, registers nvidia pip package directories containing cublas and cudnn DLLs."""
    if sys.platform != "win32":
        return

    site_packages = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if not site_packages.exists():
        return

    for sub in ["cublas", "cudnn", "cuda_runtime"]:
        bin_dir = site_packages / sub / "bin"
        if bin_dir.exists():
            try:
                os.add_dll_directory(str(bin_dir))
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
                logger.info(f"Registered CUDA DLL directory: {bin_dir}")
            except Exception as e:
                logger.debug(f"Could not add DLL directory {bin_dir}: {e}")


class AudioAligner:
    """Extracts frame-accurate word and sentence timestamps from speech audio."""

    def __init__(
        self,
        model_size_or_path: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "int8_float16",
        download_root: str | Path = DEFAULT_WHISPER_DIR,
        fallback_model: str = "base",
    ) -> None:
        _register_cuda_dll_dirs()
        self.download_root = Path(download_root)
        self.download_root.mkdir(parents=True, exist_ok=True)
        self.model_size_or_path = model_size_or_path
        self.device = device
        self.compute_type = compute_type
        self.fallback_model = fallback_model

        self.model = self._load_model_with_fallback(
            model_size_or_path=model_size_or_path,
            device=device,
            compute_type=compute_type,
            download_root=self.download_root,
            fallback_model=fallback_model,
        )

    def _load_model_with_fallback(
        self,
        model_size_or_path: str,
        device: str,
        compute_type: str,
        download_root: Path,
        fallback_model: str,
    ) -> WhisperModel:
        if device == "cuda":
            try:
                logger.info(f"Loading Whisper model '{model_size_or_path}' on cuda ({compute_type})...")
                return WhisperModel(
                    model_size_or_path,
                    device="cuda",
                    compute_type=compute_type,
                    download_root=str(download_root),
                )
            except Exception as cuda_err:
                logger.warning(
                    f"CUDA model init failed: {cuda_err}. Falling back to CPU..."
                )

        logger.info(f"Loading Whisper model '{fallback_model}' on CPU (int8)...")
        return WhisperModel(
            fallback_model,
            device="cpu",
            compute_type="int8",
            download_root=str(download_root),
        )

    def align(
        self,
        audio_path: str | Path,
        output_json_path: str | Path,
        fps: int = 60,
        language: str = "en",
    ) -> Path:
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        out_json = Path(output_json_path)
        out_json.parent.mkdir(parents=True, exist_ok=True)

        with sf.SoundFile(str(audio_file)) as f:
            true_duration = float(len(f)) / float(f.samplerate)

        try:
            segments_gen, info = self.model.transcribe(
                str(audio_file),
                word_timestamps=True,
                language=language,
            )
            # Evaluate the generator to catch any runtime CUDA execution errors
            segments_list = list(segments_gen)
        except RuntimeError as runtime_err:
            if "cublas" in str(runtime_err).lower() or "cuda" in str(runtime_err).lower():
                logger.warning(f"CUDA execution error: {runtime_err}. Switching model to CPU fallback...")
                self.model = WhisperModel(
                    self.fallback_model,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(self.download_root),
                )
                segments_gen, info = self.model.transcribe(
                    str(audio_file),
                    word_timestamps=True,
                    language=language,
                )
                segments_list = list(segments_gen)
            else:
                raise runtime_err

        all_words: list[dict[str, Any]] = []
        structured_segments: list[dict[str, Any]] = []

        for seg in segments_list:
            seg_words: list[dict[str, Any]] = []
            if seg.words:
                for w in seg.words:
                    word_clean = w.word.strip()
                    if not word_clean:
                        continue
                    w_start = round(float(w.start), 3)
                    w_end = round(float(w.end), 3)
                    word_entry = {
                        "word": word_clean,
                        "start": w_start,
                        "end": w_end,
                        "frame_start": int(round(w_start * fps)),
                        "frame_end": int(round(w_end * fps)),
                    }
                    all_words.append(word_entry)
                    seg_words.append(word_entry)

            seg_start = round(float(seg.start), 3)
            seg_end = round(float(seg.end), 3)
            structured_segments.append(
                {
                    "id": int(seg.id),
                    "text": seg.text.strip(),
                    "start": seg_start,
                    "end": seg_end,
                    "frame_start": int(round(seg_start * fps)),
                    "frame_end": int(round(seg_end * fps)),
                    "words": seg_words,
                }
            )

        duration = round(true_duration or float(info.duration), 3)
        total_frames = int(round(duration * fps))

        alignment_data: dict[str, Any] = {
            "audio_duration_seconds": duration,
            "total_frames": total_frames,
            "fps": fps,
            "words": all_words,
            "segments": structured_segments,
        }

        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(alignment_data, f, indent=2, ensure_ascii=False)

        return out_json
