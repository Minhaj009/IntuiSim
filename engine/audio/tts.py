"""
STEM-aware Text-to-Speech engine utilizing Kokoro ONNX with voice blending
and Microsoft Edge-TTS neural broadcast narration.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

try:
    from engine.audio.lexicon import StemLexicon
except ImportError:
    from lexicon import StemLexicon

try:
    from engine.audio.math_speech import format_spoken_math
except ImportError:
    try:
        from math_speech import format_spoken_math
    except ImportError:
        def format_spoken_math(text: str) -> str:
            return text

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_MODEL_PATH = PROJECT_ROOT / "assets" / "models" / "kokoro" / "kokoro-v1.0.onnx"
DEFAULT_VOICES_PATH = PROJECT_ROOT / "assets" / "models" / "kokoro" / "voices-v1.0.bin"
SAMPLE_RATE = 24000

VOICE_PRESETS = {
    "calm_professor": {"blend": [("bm_george", 0.70), ("bm_lewis", 0.30)]},
    "documentary_cinematic": {"blend": [("am_adam", 0.65), ("bm_george", 0.35)]},
    "documentary_male": "am_adam",
    "documentary_female": "af_bella",
    "scholar_british": "bm_george",
}


class StemTTS:
    """STEM-aware Text-to-Speech synthesizer supporting Kokoro ONNX voice blending and Edge-TTS."""

    def __init__(
        self,
        model_path: str | Path = DEFAULT_MODEL_PATH,
        voices_path: str | Path = DEFAULT_VOICES_PATH,
        lexicon_dict_path: str | Path | None = None,
        default_voice: str = "calm_professor",
        sample_rate: int = SAMPLE_RATE,
    ) -> None:
        self.model_path = Path(model_path)
        self.voices_path = Path(voices_path)
        self.default_voice = default_voice
        self.sample_rate = sample_rate

        if not self.model_path.exists():
            raise FileNotFoundError(f"Kokoro model not found at {self.model_path}")
        if not self.voices_path.exists():
            raise FileNotFoundError(f"Kokoro voices not found at {self.voices_path}")

        logger.info(f"Initializing Kokoro TTS from {self.model_path}")
        self.kokoro = Kokoro(str(self.model_path), str(self.voices_path))
        self.lexicon = StemLexicon(
            dict_path=Path(lexicon_dict_path) if lexicon_dict_path else None
        )

        self._cached_voices: dict[str, np.ndarray | str] = {}
        self._precache_presets()

    def _blend_voices(self, voice_weights: list[tuple[str, float]]) -> np.ndarray:
        """Linear combination blend of Kokoro voice style vectors."""
        blend = None
        for name, weight in voice_weights:
            style = self.kokoro.get_voice_style(name)
            if blend is None:
                blend = weight * style
            else:
                blend = blend + weight * style
        return blend.astype(np.float32)

    def _precache_presets(self) -> None:
        """Pre-cache blended and named voice presets."""
        try:
            self._cached_voices["calm_professor"] = self._blend_voices(
                [("bm_george", 0.70), ("bm_lewis", 0.30)]
            )
            self._cached_voices["documentary_cinematic"] = self._blend_voices(
                [("am_adam", 0.65), ("bm_george", 0.35)]
            )
            self._cached_voices["documentary_male"] = "am_adam"
            self._cached_voices["documentary_female"] = "af_bella"
            self._cached_voices["scholar_british"] = "bm_george"
            logger.info("Pre-cached Kokoro voice presets successfully.")
        except Exception as e:
            logger.warning(f"Failed to pre-cache voice presets: {e}")

    def resolve_voice(self, voice_name: str | np.ndarray) -> str | np.ndarray:
        """Resolve a preset name, raw voice name, or pre-computed ndarray style vector."""
        if isinstance(voice_name, np.ndarray):
            return voice_name
        if voice_name in self._cached_voices:
            return self._cached_voices[voice_name]
        if voice_name in VOICE_PRESETS:
            preset = VOICE_PRESETS[voice_name]
            if isinstance(preset, str):
                return preset
            elif isinstance(preset, dict) and "blend" in preset:
                return self._blend_voices(preset["blend"])
        return voice_name

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences ONLY at [.!?], retaining internal commas and semicolons."""
        raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in raw_sentences if s.strip()]

    def _synthesize_edge_tts(
        self,
        text: str,
        output_wav: Path,
        voice_name: str,
        target_sample_rate: int = SAMPLE_RATE,
    ) -> Tuple[Path, float]:
        """Synthesize narration using Edge-TTS with async stream save and conversion to WAV."""
        import edge_tts

        phonetic_text = self.lexicon.translate(text)
        logger.info(f"Edge-TTS phonetically translated: {phonetic_text}")

        if not phonetic_text.strip():
            empty_audio = np.zeros(0, dtype=np.float32)
            sf.write(str(output_wav), empty_audio, target_sample_rate, subtype="PCM_16")
            return output_wav, 0.0

        temp_mp3 = output_wav.with_suffix(".temp.mp3")

        async def _run_communicate():
            comm = edge_tts.Communicate(phonetic_text, voice_name, rate="+0%", pitch="+0Hz")
            await comm.save(str(temp_mp3))

        try:
            asyncio.run(_run_communicate())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_run_communicate())
            loop.close()

        silence_tail = np.zeros(int(round(1.000 * target_sample_rate)), dtype=np.float32)

        try:
            data, sr = sf.read(str(temp_mp3))
            if data.ndim > 1:
                data = data.mean(axis=1)
            if sr != target_sample_rate:
                from scipy.signal import resample
                new_num = int(round(len(data) * target_sample_rate / sr))
                data = resample(data, new_num).astype(np.float32)
            else:
                data = data.astype(np.float32)
            full_audio = np.concatenate([data, silence_tail])
            full_audio = np.clip(full_audio, -1.0, 1.0)
            sf.write(str(output_wav), full_audio, target_sample_rate, subtype="PCM_16")
        except Exception as e:
            logger.warning(f"Direct soundfile read failed ({e}), falling back to ffmpeg...")
            temp_wav = output_wav.with_suffix(".conv.wav")
            subprocess.run([
                "ffmpeg", "-y", "-i", str(temp_mp3),
                "-ar", str(target_sample_rate), "-ac", "1",
                str(temp_wav)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            data, _ = sf.read(str(temp_wav))
            temp_wav.unlink(missing_ok=True)
            if data.ndim > 1:
                data = data.mean(axis=1)
            full_audio = np.concatenate([data.astype(np.float32), silence_tail])
            full_audio = np.clip(full_audio, -1.0, 1.0)
            sf.write(str(output_wav), full_audio, target_sample_rate, subtype="PCM_16")
        finally:
            if temp_mp3.exists():
                temp_mp3.unlink(missing_ok=True)

        info = sf.info(str(output_wav))
        duration_seconds = round(float(info.duration), 4)
        return output_wav, duration_seconds

    def _synthesize_openai(
        self,
        text: str,
        output_wav: Path,
        voice_name: str = "onyx",
        target_sample_rate: int = SAMPLE_RATE,
    ) -> Tuple[Path, float]:
        """Synthesize using OpenAI Audio TTS API (tts-1-hd)."""
        import os, urllib.request, json
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI TTS.")
        
        phonetic_text = self.lexicon.translate(text)
        req = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps({"model": "tts-1-hd", "input": phonetic_text, "voice": voice_name}).encode("utf-8")
        )
        temp_mp3 = output_wav.with_suffix(".temp.mp3")
        with urllib.request.urlopen(req) as resp:
            temp_mp3.write_bytes(resp.read())

        subprocess.run([
            "ffmpeg", "-y", "-i", str(temp_mp3),
            "-ar", str(target_sample_rate), "-ac", "1", str(output_wav)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        temp_mp3.unlink(missing_ok=True)
        info = sf.info(str(output_wav))
        return output_wav, round(float(info.duration), 4)

    def _synthesize_elevenlabs(
        self,
        text: str,
        output_wav: Path,
        voice_id: str = "pNInz6obpgDQGcFmaJgB",  # Default 'Adam' or 'George'
        target_sample_rate: int = SAMPLE_RATE,
    ) -> Tuple[Path, float]:
        """Synthesize using ElevenLabs Multilingual v2 API."""
        import os, urllib.request, json
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required for ElevenLabs TTS.")
        
        phonetic_text = self.lexicon.translate(text)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        req = urllib.request.Request(
            url,
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            data=json.dumps({
                "text": phonetic_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.55, "similarity_boost": 0.8}
            }).encode("utf-8")
        )
        temp_mp3 = output_wav.with_suffix(".temp.mp3")
        with urllib.request.urlopen(req) as resp:
            temp_mp3.write_bytes(resp.read())

        subprocess.run([
            "ffmpeg", "-y", "-i", str(temp_mp3),
            "-ar", str(target_sample_rate), "-ac", "1", str(output_wav)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        temp_mp3.unlink(missing_ok=True)
        info = sf.info(str(output_wav))
        return output_wav, round(float(info.duration), 4)

    def synthesize(
        self,
        text: str,
        output_path: str | Path,
        voice: str | None = None,
        speed: float = 0.92,
        lang: str = "en-us",
        target_sample_rate: int = SAMPLE_RATE,
        pause_duration: float = 0.400,
        tail_silence: float = 1.000,
    ) -> Tuple[Path, float]:
        """
        Synthesize STEM narration into a 16-bit PCM WAV file.

        - If voice starts with 'elevenlabs:' or 'eleven:', uses ElevenLabs API.
        - If voice starts with 'openai:', uses OpenAI TTS API.
        - If voice starts with 'edge:' or 'edgetts:', uses Edge-TTS.
        - Otherwise, uses Kokoro ONNX with resolved voice vectors and whole-sentence synthesis.
        """
        output_wav = Path(output_path)
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        active_voice = voice if voice is not None else self.default_voice

        # Pre-process math notation with natural spoken prosody
        text = format_spoken_math(text)

        # ElevenLabs branch
        if isinstance(active_voice, str) and (active_voice.startswith("elevenlabs:") or active_voice.startswith("eleven:")):
            vid = active_voice.split(":", 1)[1]
            return self._synthesize_elevenlabs(text, output_wav, voice_id=vid, target_sample_rate=target_sample_rate)

        # OpenAI branch
        if isinstance(active_voice, str) and active_voice.startswith("openai:"):
            vname = active_voice.split(":", 1)[1]
            return self._synthesize_openai(text, output_wav, voice_name=vname, target_sample_rate=target_sample_rate)

        # Edge-TTS branch
        if isinstance(active_voice, str) and (
            active_voice.startswith("edge:") or active_voice.startswith("edgetts:")
        ):
            if active_voice.startswith("edge:"):
                voice_name = active_voice[len("edge:"):]
            else:
                voice_name = active_voice[len("edgetts:"):]
            return self._synthesize_edge_tts(
                text=text,
                output_wav=output_wav,
                voice_name=voice_name,
                target_sample_rate=target_sample_rate,
            )

        # Kokoro ONNX branch
        phonetic_text = self.lexicon.translate(text)
        logger.info(f"Phonetically translated: {phonetic_text}")

        resolved_voice = self.resolve_voice(active_voice)

        sentences = self._split_into_sentences(phonetic_text)
        if not sentences:
            empty_audio = np.zeros(0, dtype=np.float32)
            sf.write(str(output_wav), empty_audio, target_sample_rate, subtype="PCM_16")
            return output_wav, 0.0

        silence_sentence = np.zeros(int(round(pause_duration * self.sample_rate)), dtype=np.float32)
        silence_question = np.zeros(int(round(0.750 * self.sample_rate)), dtype=np.float32)
        silence_tail = np.zeros(int(round(tail_silence * self.sample_rate)), dtype=np.float32)

        audio_parts: list[np.ndarray] = []

        for idx, sentence in enumerate(sentences):
            sent_str = sentence.strip()
            if not sent_str:
                continue

            # For sentences under 80 words, pass the full sentence to kokoro.create()
            # If a single sentence exceeds 80 words, only split on major punctuation like semicolons
            words = sent_str.split()
            if len(words) <= 80:
                chunks = [sent_str]
            else:
                chunks = [c.strip() for c in re.split(r"(?<=[;])\s+", sent_str) if c.strip()]
                if not chunks:
                    chunks = [sent_str]

            for c_idx, chunk in enumerate(chunks):
                samples, _ = self.kokoro.create(
                    chunk, voice=resolved_voice, speed=speed, lang=lang
                )
                samples = np.asarray(samples, dtype=np.float32)
                audio_parts.append(samples)
                if c_idx < len(chunks) - 1:
                    silence_semi = np.zeros(int(round(0.250 * self.sample_rate)), dtype=np.float32)
                    audio_parts.append(silence_semi)

            if idx < len(sentences) - 1:
                boundary_pause = silence_question if sent_str.endswith("?") else silence_sentence
                audio_parts.append(boundary_pause)

        audio_parts.append(silence_tail)

        full_audio = np.concatenate(audio_parts)

        # Broadcast analog warmth filtering (Directive 5 & 25)
        try:
            from scipy.signal import butter, lfilter
            b_hp, a_hp = butter(2, 75.0 / (self.sample_rate / 2.0), btype="high")
            full_audio = lfilter(b_hp, a_hp, full_audio)
            b_lp, a_lp = butter(1, 400.0 / (self.sample_rate / 2.0), btype="low")
            lows = lfilter(b_lp, a_lp, full_audio)
            full_audio = full_audio + 0.22 * lows
            max_val = np.max(np.abs(full_audio))
            if max_val > 0:
                full_audio = full_audio / max_val * 0.95
        except Exception as filter_err:
            logger.warning(f"Analog warmth filtering bypassed: {filter_err}")

        full_audio = np.clip(full_audio, -1.0, 1.0)

        if target_sample_rate != self.sample_rate:
            from scipy.signal import resample
            new_num = int(round(len(full_audio) * target_sample_rate / self.sample_rate))
            full_audio = resample(full_audio, new_num).astype(np.float32)
            final_sample_rate = target_sample_rate
        else:
            final_sample_rate = self.sample_rate

        sf.write(str(output_wav), full_audio, final_sample_rate, subtype="PCM_16")
        duration_seconds = round(len(full_audio) / final_sample_rate, 4)

        return output_wav, duration_seconds
