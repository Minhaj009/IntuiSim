"""
Verification test script for IntuiSim natural voice synthesis and alignment pipeline.
Tests:
1. Kokoro blended 'documentary_cinematic' (0.65 am_adam + 0.35 bm_george)
2. Kokoro 'af_bella'
3. Edge-TTS 'edge:en-US-ChristopherNeural'
4. AudioAligner forced alignment and SRT subtitle generation
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.audio.tts import StemTTS
from engine.audio.aligner import AudioAligner
from engine.audio.subtitles import export_srt


def test_pipeline():
    output_dir = PROJECT_ROOT / "test_outputs" / "voices"
    output_dir.mkdir(parents=True, exist_ok=True)

    test_sentence = (
        "In a 3nm GAAFET, electron transport in AlGaAs reaches 1.5 THz; "
        "this high-velocity ballistic regime fundamentally suppresses short-channel effects. "
        "Consequently, quantum confinement governs subthreshold leakage across the gate dielectric."
    )

    print("=" * 65)
    print("IntuiSim Natural Voice Engine Verification")
    print("=" * 65)
    print(f"Sample Sentence:\n{test_sentence}\n")

    tts = StemTTS()
    aligner = AudioAligner(device="cpu", fallback_model="base")

    tests = [
        ("Kokoro documentary_cinematic", "documentary_cinematic", output_dir / "test_documentary_cinematic.wav"),
        ("Kokoro af_bella", "af_bella", output_dir / "test_af_bella.wav"),
        ("Edge-TTS ChristopherNeural", "edge:en-US-ChristopherNeural", output_dir / "test_edge_christopher.wav"),
    ]

    results = {}

    for label, voice_key, wav_path in tests:
        print(f"--- Synthesizing: {label} ({voice_key}) ---")
        out_path, duration = tts.synthesize(test_sentence, wav_path, voice=voice_key)
        size_bytes = out_path.stat().st_size
        print(f"  -> File: {out_path.name}")
        print(f"  -> Duration: {duration:.2f}s | Size: {size_bytes:,} bytes")
        assert out_path.exists(), f"Audio file missing: {out_path}"
        assert size_bytes > 0, f"Audio file empty: {out_path}"
        assert duration > 0, f"Duration is zero: {out_path}"
        results[voice_key] = {
            "path": str(out_path),
            "duration": duration,
            "size_bytes": size_bytes,
        }

    # Test forced alignment on documentary_cinematic
    print("\n--- Testing Forced Alignment on documentary_cinematic ---")
    cinematic_wav = Path(results["documentary_cinematic"]["path"])
    alignment_json = output_dir / "test_documentary_cinematic_alignment.json"
    aligner.align(cinematic_wav, alignment_json, fps=30)
    assert alignment_json.exists() and alignment_json.stat().st_size > 0, "Alignment JSON missing or empty"
    print(f"  -> Alignment JSON: {alignment_json.name} ({alignment_json.stat().st_size:,} bytes)")

    # Test SRT subtitle export
    srt_path = output_dir / "test_documentary_cinematic_captions.srt"
    export_srt(alignment_json, srt_path)
    assert srt_path.exists() and srt_path.stat().st_size > 0, "SRT captions missing or empty"
    print(f"  -> SRT Captions: {srt_path.name} ({srt_path.stat().st_size:,} bytes)")
    print("\nSRT Subtitle Preview:")
    print(srt_path.read_text(encoding="utf-8")[:320] + "...\n")

    print("=" * 65)
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY")
    print("=" * 65)
    return results


if __name__ == "__main__":
    test_pipeline()
