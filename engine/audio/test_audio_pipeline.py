"""
End-to-end verification script for IntuiSim Phase 2 Audio Pipeline.
"""

import json
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.audio.tts import StemTTS
from engine.audio.aligner import AudioAligner
from engine.audio.subtitles import export_srt
from engine.audio.mastering import AudioMaster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TestAudioPipeline")


def run_pipeline_test():
    test_dir = PROJECT_ROOT / "engine" / "audio" / "test_output"
    test_dir.mkdir(parents=True, exist_ok=True)

    test_script = (
        "At the atomic scale, pure silicon forms a diamond cubic crystal lattice "
        "where each atom shares valence bonds. The MOSFET gate oxide thickness is measured in nanometers."
    )

    logger.info("Step 1: STEM TTS Synthesis")
    tts = StemTTS()
    wav_path = test_dir / "test_narration.wav"
    audio_path, duration = tts.synthesize(test_script, wav_path)

    assert audio_path.exists(), f"WAV file missing: {audio_path}"
    assert duration > 0.0, f"Invalid duration: {duration}"
    logger.info(f"Synthesized duration: {duration:.2f}s")

    logger.info("Step 2: Forced Alignment with Whisper")
    aligner = AudioAligner(device="cpu", fallback_model="base")
    alignment_json_path = test_dir / "test_alignment.json"
    aligner.align(audio_path, alignment_json_path, fps=60)

    assert alignment_json_path.exists(), f"Alignment JSON missing: {alignment_json_path}"
    with open(alignment_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    words = data.get("words", [])
    segments = data.get("segments", [])
    assert len(words) > 0, "No words found in alignment."
    assert len(segments) > 0, "No segments found in alignment."
    logger.info(f"Aligned words: {len(words)}, segments: {len(segments)}")

    logger.info("Step 3: Subtitle Generation (SRT)")
    captions_srt_path = test_dir / "test_captions.srt"
    export_srt(alignment_json_path, captions_srt_path)

    assert captions_srt_path.exists(), f"SRT missing: {captions_srt_path}"
    with open(captions_srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    assert len(srt_content.strip()) > 0, "SRT content is empty."

    logger.info("Step 4: Audio Mastering and Loudness Normalization")
    master = AudioMaster()
    mastered_wav_path = test_dir / "test_mastered.wav"
    master.master_scene_audio(
        voice_wav=audio_path,
        bgm_wav=None,
        output_wav=mastered_wav_path,
        target_lufs=-14.0,
    )
    assert mastered_wav_path.exists(), f"Mastered WAV missing: {mastered_wav_path}"

    results = {
        "status": "PASS",
        "audio_path": str(audio_path),
        "duration": duration,
        "word_count": len(words),
        "segment_count": len(segments),
        "alignment_json": str(alignment_json_path),
        "captions_srt": str(captions_srt_path),
        "mastered_wav": str(mastered_wav_path),
    }
    print("\nTEST RECEIPTS:")
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run_pipeline_test()
