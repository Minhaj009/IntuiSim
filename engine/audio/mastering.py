"""
Audio mastering engine with ducking, SFX mixing, and EBU R128 loudness normalization.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)


class AudioMaster:
    """Master scene audio: background music sidechain ducking, SFX mixing, and EBU R128 normalization."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg") -> None:
        self.ffmpeg_path = shutil.which(ffmpeg_bin) or ffmpeg_bin

    def build_master_command(
        self,
        voice_wav: str | Path,
        bgm_wav: str | Path | None = None,
        output_wav: str | Path = "mastered.wav",
        sfx_cues: Sequence[dict[str, Any]] | None = None,
        ducking_db: float = -16.0,
        target_lufs: float = -14.0,
    ) -> list[str]:
        cmd: list[str] = [self.ffmpeg_path, "-y"]
        cmd.extend(["-i", str(voice_wav)])

        has_bgm = bgm_wav is not None and Path(bgm_wav).exists()
        if has_bgm:
            cmd.extend(["-i", str(bgm_wav)])

        valid_sfx: list[dict[str, Any]] = []
        if sfx_cues:
            for cue in sfx_cues:
                cue_path = Path(cue["path"])
                if cue_path.exists():
                    valid_sfx.append(cue)
                    cmd.extend(["-i", str(cue_path)])

        filter_parts: list[str] = [
            "[0:a]highpass=f=80,equalizer=f=220:t=q:w=1.2:g=2.5,equalizer=f=3500:t=q:w=1.5:g=1.8,acompressor=threshold=0.2:ratio=2.5:attack=15:release=150[voice_warmed]"
        ]
        mix_inputs: list[str] = ["[voice_warmed]"]

        if has_bgm:
            filter_parts.append(
                "[1:a][voice_warmed]sidechaincompress=threshold=0.125:ratio=4:attack=20:release=300[ducked_bgm]"
            )
            mix_inputs.append("[ducked_bgm]")

        if valid_sfx:
            sfx_start_idx = 2 if has_bgm else 1
            for i, cue in enumerate(valid_sfx):
                input_idx = sfx_start_idx + i
                delay_ms = int(round(float(cue.get("timestamp", 0.0)) * 1000))
                tag = f"sfx_{i}"
                filter_parts.append(
                    f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[{tag}]"
                )
                mix_inputs.append(f"[{tag}]")

        if len(mix_inputs) > 1:
            total_inputs = len(mix_inputs)
            joined_inputs = "".join(mix_inputs)
            filter_parts.append(
                f"{joined_inputs}amix=inputs={total_inputs}:duration=first:dropout_transition=2[mixed]"
            )
            pre_norm = "[mixed]"
        else:
            pre_norm = "[0:a]"

        filter_parts.append(
            f"{pre_norm}loudnorm=I={target_lufs}:TP=-1.0:LRA=7[out]"
        )

        filter_str = ";".join(filter_parts)
        cmd.extend([
            "-filter_complex", filter_str,
            "-map", "[out]",
            "-ar", "48000",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(output_wav)
        ])
        return cmd

    def master_scene_audio(
        self,
        voice_wav: str | Path,
        bgm_wav: str | Path | None = None,
        output_wav: str | Path = "mastered.wav",
        sfx_cues: Sequence[dict[str, Any]] | None = None,
        ducking_db: float = -16.0,
        target_lufs: float = -14.0,
    ) -> Path:
        out_path = Path(output_wav)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self.build_master_command(
            voice_wav=voice_wav,
            bgm_wav=bgm_wav,
            output_wav=out_path,
            sfx_cues=sfx_cues,
            ducking_db=ducking_db,
            target_lufs=target_lufs,
        )

        if not shutil.which(self.ffmpeg_path) and not Path(self.ffmpeg_path).exists():
            logger.warning("FFmpeg executable unavailable. Fallback copy performed.")
            shutil.copyfile(str(voice_wav), str(out_path))
            return out_path

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg mastering error: {proc.stderr}")

        return out_path
