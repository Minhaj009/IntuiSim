import asyncio
import edge_tts.constants
edge_tts.constants.CHROMIUM_FULL_VERSION = "156.0.4314.15"
edge_tts.constants.CHROMIUM_MAJOR_VERSION = "156"
edge_tts.constants.SEC_MS_GEC_VERSION = "1-156.0.4314.15"
edge_tts.constants.BASE_HEADERS["User-Agent"] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36 Edg/156.0.0.0"
)
edge_tts.constants.WSS_HEADERS.update(edge_tts.constants.BASE_HEADERS)

import edge_tts

async def main():
    print("Testing with Edge version 156.0.4314.15...")
    comm = edge_tts.Communicate("Hello world, this is a test.", "en-US-ChristopherNeural")
    await comm.save("F:/IntuiSim/test_edge156.mp3")
    print("SUCCESS! File generated!")

if __name__ == "__main__":
    asyncio.run(main())
