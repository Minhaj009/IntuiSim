"""
Unit and Integration Test Suite for the Natural Spoken Math Voiceover Engine.
Verifies LaTeX/STEM translation into conversational spoken English and
Kokoro ONNX audio synthesis validation.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import soundfile as sf
from engine.audio.math_speech import format_spoken_math
from engine.audio.tts import StemTTS


def test_format_spoken_math():
    print("--- 1. Testing Mathematical Formula Formatting ---")

    # 1. Kronig-Penney dispersion relation
    kp_raw = r"P \frac{\sin(\alpha a)}{\alpha a} + \cos(\alpha a) = \cos(ka)"
    kp_spoken = format_spoken_math(kp_raw)
    print(f"Original: {kp_raw}")
    print(f"Spoken:   {kp_spoken}")
    assert "sine of alpha a" in kp_spoken
    assert "— equals" in kp_spoken
    assert "cosine of k a" in kp_spoken

    # 2. Schrödinger Equation
    schro_raw = r"\hat{H} \psi = E \psi"
    schro_spoken = format_spoken_math(schro_raw)
    print(f"Original: {schro_raw}")
    print(f"Spoken:   {schro_spoken}")
    assert "the Hamiltonian, H-hat," in schro_spoken
    assert "— equals" in schro_spoken

    # 3. Fractions and Roots
    root_raw = r"\alpha = \frac{\sqrt{2m_0 E}}{\hbar}"
    root_spoken = format_spoken_math(root_raw)
    print(f"Original: {root_raw}")
    print(f"Spoken:   {root_spoken}")
    assert "the square root of two m-zero E" in root_spoken
    assert "h-bar" in root_spoken

    # 4. Brillouin Zone Boundary & Standing Waves
    bz_raw = r"k = \pm \frac{\pi}{a}"
    bz_spoken = format_spoken_math(bz_raw)
    print(f"Original: {bz_raw}")
    print(f"Spoken:   {bz_spoken}")
    assert "plus or minus" in bz_spoken
    assert "pi" in bz_spoken

    # 5. Complex Wavevector & Evanescent Decay
    decay_raw = r"k = \frac{\pi}{a} \pm i \kappa"
    decay_spoken = format_spoken_math(decay_raw)
    print(f"Original: {decay_raw}")
    print(f"Spoken:   {decay_spoken}")
    assert "kappa" in decay_spoken

    print("PASS: Mathematical formula formatting tests passed!\n")


def test_stem_tts_synthesis():
    print("--- 2. Testing Kokoro ONNX Synthesis with Spoken Math ---")
    tts = StemTTS(default_voice="documentary_cinematic")

    sample_text = (
        "In Lecture Zero Five, we solve the Kronig-Penney dispersion relation: "
        r"P \frac{\sin(\alpha a)}{\alpha a} + \cos(\alpha a) = \cos(ka). "
        "At the Brillouin zone boundaries, Bragg reflection opens a forbidden energy bandgap."
    )

    out_wav = PROJECT_ROOT / "dist" / "test_math_speech.wav"
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    result_wav, duration = tts.synthesize(
        text=sample_text,
        output_path=out_wav,
        voice="documentary_cinematic",
    )

    print(f"Synthesized Output: {result_wav}")
    print(f"Audio Duration:     {duration:.2f} seconds")

    assert result_wav.exists(), "Output WAV was not created"
    assert duration > 5.0, f"Expected audio duration > 5.0s, got {duration:.2f}s"

    info = sf.info(str(result_wav))
    assert info.samplerate == 24000, f"Expected 24000Hz, got {info.samplerate}"
    assert info.channels == 1, f"Expected mono audio, got {info.channels}"

    print("PASS: StemTTS synthesis on spoken math succeeded!\n")


if __name__ == "__main__":
    test_format_spoken_math()
    test_stem_tts_synthesis()
    print("ALL NATURAL SPOKEN MATH TESTS PASSED 100%!")
