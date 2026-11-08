import asyncio
import edge_tts
from edge_tts.drm import DRM

async def main():
    print("Initial DRM clock skew:", DRM.clock_skew_seconds)
    try:
        voices = await edge_tts.list_voices()
        print("After list_voices DRM clock skew:", DRM.clock_skew_seconds)
    except Exception as e:
        print("list_voices failed:", e)

    comm = edge_tts.Communicate("Hello world, this is a test of natural voice.", "en-US-ChristopherNeural")
    await comm.save("F:/IntuiSim/test_skew.mp3")
    print("Synthesized test_skew.mp3 successfully!")

if __name__ == "__main__":
    asyncio.run(main())
