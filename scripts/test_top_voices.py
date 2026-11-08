import asyncio
import edge_tts
from pathlib import Path

text = (
    "To understand why pure silicon is the backbone of modern microchips, "
    "we have to peer straight into its atomic anatomy. "
    "Every single silicon atom holds fourteen protons in its nucleus, "
    "surrounded by four outermost valence electrons. "
    "Notice these four electrons marked in glowing amber: on their own, they are chemically hungry, "
    "seeking four more partners to achieve a stable octet. "
    "So, each silicon atom locks hands with its nearest neighbors, "
    "forming a rigid tetrahedral lattice."
)

out_dir = Path("F:/IntuiSim/projects/voice_audition_v2")
out_dir.mkdir(parents=True, exist_ok=True)

voices = [
    ("andrew_multilingual.mp3", "en-US-AndrewMultilingualNeural"),
    ("brian_multilingual.mp3", "en-US-BrianMultilingualNeural"),
    ("christopher_documentary.mp3", "en-US-ChristopherNeural"),
    ("ryan_british.mp3", "en-GB-RyanNeural"),
]

async def main():
    for fname, voice in voices:
        print(f"Synthesizing {voice}...")
        comm = edge_tts.Communicate(text, voice, rate="-4%", pitch="+0Hz")
        await comm.save(str(out_dir / fname))
        print(f"Saved {fname}")

if __name__ == "__main__":
    asyncio.run(main())
