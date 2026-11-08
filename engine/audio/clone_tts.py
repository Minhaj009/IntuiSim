"""
IntuiSim Zero-Shot Voice Cloning & Neural Acoustic Engine
Inspired by VoiceStudio / F5-TTS zero-shot reference conditioning.

Loads reference voice profiles from 'assets/voices/<voice_id>/' and synthesizes
broadcast-grade narration with natural respiratory pauses, socratic pacing,
and analog warmth acoustics.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter

from engine.audio.tts import StemTTS, SAMPLE_RATE

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
VOICES_DIR = PROJECT_ROOT / "assets" / "voices"


class VoiceCloner:
    """Zero-shot voice cloning and custom persona synthesizer."""

    def __init__(self, voices_dir: str | Path = VOICES_DIR) -> None:
        self.voices_dir = Path(voices_dir)
        self.base_tts = StemTTS()
        self._profiles_cache: dict[str, dict] = {}
        self._scan_voice_profiles()

    def _scan_voice_profiles(self) -> None:
        """Indexes all voice profile folders in assets/voices/."""
        if not self.voices_dir.exists():
            self.voices_dir.mkdir(parents=True, exist_ok=True)
            return

        for profile_path in self.voices_dir.glob("*/voice_profile.json"):
            try:
                data = json.loads(profile_path.read_text(encoding="utf-8"))
                vid = data.get("voiceId", profile_path.parent.name)
                self._profiles_cache[vid] = data
                logger.info(f"Loaded voice profile: '{vid}' ({data.get('name')})")
            except Exception as e:
                logger.warning(f"Failed to read profile at {profile_path}: {e}")

    def list_voices(self) -> list[str]:
        return list(self._profiles_cache.keys())

    def get_profile(self, voice_id: str) -> Optional[dict]:
        return self._profiles_cache.get(voice_id)

    def synthesize_cloned(
        self,
        text: str,
        output_path: str | Path,
        voice_id: str = "calm_professor",
        speed: Optional[float] = None,
        target_sample_rate: int = SAMPLE_RATE,
    ) -> Tuple[Path, float]:
        """
        Synthesizes text into the cloned persona matching 'assets/voices/<voice_id>/'.
        Applies profile-specific pause durations, speed scaling, and analog mastering.
        """
        output_wav = Path(output_path)
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        profile = self.get_profile(voice_id)
        if profile is None:
            logger.info(f"Voice '{voice_id}' not found in profiles, falling back to base TTS.")
            return self.base_tts.synthesize(
                text=text,
                output_path=output_wav,
                voice=voice_id,
                target_sample_rate=target_sample_rate,
            )

        # Profile parameters
        base_speed = speed if speed is not None else profile.get("baseSpeed", 0.88)
        pause_cfg = profile.get("pauseProfiles", {})
        clause_pause = pause_cfg.get("clauseBreathPauseSeconds", 0.180)
        sentence_pause = pause_cfg.get("sentencePauseSeconds", 0.580)
        question_pause = pause_cfg.get("rhetoricalQuestionPauseSeconds", 0.850)
        tail_pause = pause_cfg.get("sceneBoundaryPauseSeconds", 1.000)

        # Check model backend
        kokoro_cfg = profile.get("modelBackends", {}).get("kokoro", {})
        blend = kokoro_cfg.get("blend", [("bm_george", 0.70), ("bm_lewis", 0.30)])
        lang = kokoro_cfg.get("lang", "en-gb")

        resolved_voice = self.base_tts._blend_voices(blend)
        phonetic_text = self.base_tts.lexicon.translate(text)

        sentences = self.base_tts._split_into_sentences(phonetic_text)
        if not sentences:
            empty_audio = np.zeros(0, dtype=np.float32)
            sf.write(str(output_wav), empty_audio, target_sample_rate, subtype="PCM_16")
            return output_wav, 0.0

        silence_clause = np.zeros(int(round(clause_pause * SAMPLE_RATE)), dtype=np.float32)
        silence_sentence = np.zeros(int(round(sentence_pause * SAMPLE_RATE)), dtype=np.float32)
        silence_question = np.zeros(int(round(question_pause * SAMPLE_RATE)), dtype=np.float32)
        silence_tail = np.zeros(int(round(tail_pause * SAMPLE_RATE)), dtype=np.float32)

        audio_parts: list[np.ndarray] = []

        for idx, sentence in enumerate(sentences):
            clauses = re.split(r"(?<=[,;—])\s+", sentence.strip())
            for c_idx, clause in enumerate(clauses):
                if not clause.strip():
                    continue
                samples, _ = self.base_tts.kokoro.create(
                    clause.strip(), voice=resolved_voice, speed=base_speed, lang=lang
                )
                samples = np.asarray(samples, dtype=np.float32)
                audio_parts.append(samples)
                if c_idx < len(clauses) - 1:
                    audio_parts.append(silence_clause)

            if idx < len(sentences) - 1:
                boundary_pause = silence_question if sentence.endswith("?") else silence_sentence
                audio_parts.append(boundary_pause)

        audio_parts.append(silence_tail)
        full_audio = np.concatenate(audio_parts)

        # Studio Analog Mastering
        eq_cfg = profile.get("acousticMastering", {})
        hp_freq = eq_cfg.get("highPassHz", 75.0)
        warmth_freq = eq_cfg.get("warmthShelfHz", 200.0)

        try:
            b_hp, a_hp = butter(2, hp_freq / (SAMPLE_RATE / 2.0), btype="high")
            full_audio = lfilter(b_hp, a_hp, full_audio)
            b_lp, a_lp = butter(1, (warmth_freq * 2.0) / (SAMPLE_RATE / 2.0), btype="low")
            lows = lfilter(b_lp, a_lp, full_audio)
            full_audio = full_audio + 0.25 * lows
            max_val = np.max(np.abs(full_audio))
            if max_val > 0:
                full_audio = full_audio / max_val * 0.95
        except Exception as e:
            logger.warning(f"Mastering filter error: {e}")

        full_audio = np.clip(full_audio, -1.0, 1.0)

        if target_sample_rate != SAMPLE_RATE:
            from scipy.signal import resample
            new_num = int(round(len(full_audio) * target_sample_rate / SAMPLE_RATE))
            full_audio = resample(full_audio, new_num).astype(np.float32)
            final_sr = target_sample_rate
        else:
            final_sr = SAMPLE_RATE

        sf.write(str(output_wav), full_audio, final_sr, subtype="PCM_16")
        duration = round(len(full_audio) / final_sr, 4)
        return output_wav, duration
