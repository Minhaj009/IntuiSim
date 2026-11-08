import asyncio
import edge_tts

async def main():
    voices = await edge_tts.list_voices()
    targets = [
        "en-US-ChristopherNeural",
        "en-US-AndrewMultilingualNeural",
        "en-US-BrianMultilingualNeural",
        "en-US-EricNeural",
        "en-US-GuyNeural",
        "en-GB-RyanNeural",
        "en-GB-ThomasNeural",
        "en-US-AvaMultilingualNeural",
        "en-US-EmmaMultilingualNeural",
    ]
    available = [v for v in voices if v["ShortName"] in targets]
    print(f"Found {len(available)} top documentary voices:")
    for v in available:
        print(f"- {v['ShortName']} ({v['Gender']}, {v['Locale']})")

if __name__ == "__main__":
    asyncio.run(main())
