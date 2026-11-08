import asyncio
import os
from pathlib import Path
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
import edge_tts

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))

try:
    from engine.audio.lexicon import StemLexicon
except ImportError:
    from lexicon import StemLexicon

test_text = (
    "At the atomic scale, pure silicon forms a diamond cubic crystal lattice "
    "where each atom shares four valence bonds with its nearest neighbors. "
    "This covalent configuration forms a highly stable crystal structure at room temperature."
)

out_dir = PROJECT_ROOT / "projects" / "voice_audition"
out_dir.mkdir(parents=True, exist_ok=True)

lexicon = StemLexicon()
phonetic_text = lexicon.translate(test_text)

k = Kokoro(
    str(PROJECT_ROOT / "assets" / "models" / "kokoro" / "kokoro-v1.0.onnx"),
    str(PROJECT_ROOT / "assets" / "models" / "kokoro" / "voices-v1.0.bin"),
)

kokoro_candidates = [
    ("kokoro_af_bella.wav", "af_bella"),
    ("kokoro_am_adam.wav", "am_adam"),
    ("kokoro_am_michael.wav", "am_michael"),
    ("kokoro_bm_george.wav", "bm_george"),
]

print("Synthesizing Kokoro candidates...")
for fname, voice in kokoro_candidates:
    samples, sr = k.create(phonetic_text, voice=voice, speed=1.0, lang="en-us")
    sf.write(str(out_dir / fname), samples, sr)
    print(f"Generated {fname}")

edge_candidates = [
    ("edgetts_christopher.mp3", "en-US-ChristopherNeural"),
    ("edgetts_eric.mp3", "en-US-EricNeural"),
    ("edgetts_guy.mp3", "en-US-GuyNeural"),
    ("edgetts_jenny.mp3", "en-US-JennyNeural"),
    ("edgetts_ryan_british.mp3", "en-GB-RyanNeural"),
]

async def run_edge():
    print("Synthesizing Edge-TTS neural documentary candidates...")
    for fname, voice in edge_candidates:
        communicate = edge_tts.Communicate(test_text, voice=voice, rate="+0%", pitch="+0Hz")
        await communicate.save(str(out_dir / fname))
        print(f"Generated {fname}")

asyncio.run(run_edge())
print(f"\nAll voice audition files generated in {out_dir}/")
