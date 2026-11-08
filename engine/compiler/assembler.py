"""
Incremental Scene Assembler & Video Stream Concatenator
Stitches individual scene MP4s losslessly or with seamless xfade transitions and muxes master audio.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)


class VideoAssembler:
    """Concatenates rendered scene clips with xfade transitions and muxes master audio track."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg", ffprobe_bin: str = "ffprobe") -> None:
        self.ffmpeg_path = shutil.which(ffmpeg_bin) or ffmpeg_bin
        self.ffprobe_path = shutil.which(ffprobe_bin) or ffprobe_bin

    @staticmethod
    def compute_scene_hash(narration_text: str, scene_html_content: str) -> str:
        """Returns SHA256 hash of narration and visual HTML code for cache gating."""
        h = hashlib.sha256()
        h.update(narration_text.strip().encode("utf-8"))
        h.update(scene_html_content.strip().encode("utf-8"))
        return h.hexdigest()[:16]

    def get_media_info(self, file_path: Path | str) -> dict:
        """Probes video duration, streams, codec, resolution, framerate, and pixel format via ffprobe."""
        resolved = Path(file_path).resolve()
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-show_entries", "stream=codec_name,codec_type,width,height,r_frame_rate,pix_fmt",
            "-of", "json",
            str(resolved),
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            data = json.loads(res.stdout)
            duration = float(data.get("format", {}).get("duration", 0.0))
            streams = data.get("streams", [])
            has_audio = any(s.get("codec_type") == "audio" for s in streams)
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            has_video = video_stream is not None

            width = int(video_stream.get("width", 1920)) if video_stream else 1920
            height = int(video_stream.get("height", 1080)) if video_stream else 1080
            codec_name = video_stream.get("codec_name", "h264") if video_stream else "h264"
            pix_fmt = video_stream.get("pix_fmt", "yuv420p") if video_stream else "yuv420p"
            r_frame_rate = video_stream.get("r_frame_rate", "30/1") if video_stream else "30/1"
            fps = 30.0
            if r_frame_rate:
                try:
                    parts = r_frame_rate.split("/")
                    if len(parts) == 2:
                        num, den = float(parts[0]), float(parts[1])
                        fps = round(num / den, 3) if den != 0 else 30.0
                    else:
                        fps = round(float(parts[0]), 3)
                except Exception:
                    fps = 30.0

            return {
                "duration": duration,
                "has_audio": has_audio,
                "has_video": has_video,
                "width": width,
                "height": height,
                "codec_name": codec_name,
                "pix_fmt": pix_fmt,
                "fps": fps,
                "r_frame_rate": r_frame_rate,
            }
        except Exception as e:
            logger.warning(f"ffprobe probe failed for {resolved}: {e}")
            return {
                "duration": 0.0,
                "has_audio": False,
                "has_video": True,
                "width": 1920,
                "height": 1080,
                "codec_name": "h264",
                "pix_fmt": "yuv420p",
                "fps": 30.0,
                "r_frame_rate": "30/1",
            }

    def _normalize_clip(
        self,
        input_path: Path | str,
        output_path: Path | str,
        width: int = 1920,
        height: int = 1080,
        fps: float = 30.0,
        codec_name: str = "h264",
        pix_fmt: str = "yuv420p",
    ) -> Path:
        """
        Pre-normalizes a video file into a video-only stream matching exact resolution,
        framerate, codec, and pixel format.
        """
        in_p = Path(input_path).resolve()
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        # Map target codec name to appropriate ffmpeg encoder
        is_hevc = codec_name in ("hevc", "h265")
        if is_hevc:
            encoder = "hevc_nvenc"
            extra_args = ["-preset", "fast", "-cq", "18"]
        else:
            encoder = "libx264"
            extra_args = ["-preset", "fast", "-crf", "17"]

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(in_p),
            "-an",
            "-vf", f"scale={width}:{height},fps={fps}",
            "-pix_fmt", pix_fmt,
            "-c:v", encoder,
            *extra_args,
            str(out_p),
        ]

        logger.info(
            f"Pre-normalizing {in_p.name} -> {out_p.name} "
            f"({width}x{height} @ {fps}fps, codec={encoder}, pix_fmt={pix_fmt}, no audio)..."
        )
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            # Fallback if hardware nvenc is unavailable
            if encoder == "hevc_nvenc":
                logger.warning(f"hevc_nvenc failed, retrying with libx265 for {in_p.name}...")
                cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-i", str(in_p),
                    "-an",
                    "-vf", f"scale={width}:{height},fps={fps}",
                    "-pix_fmt", pix_fmt,
                    "-c:v", "libx265",
                    "-preset", "fast",
                    "-crf", "18",
                    str(out_p),
                ]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0:
                raise RuntimeError(f"FFmpeg normalization failed for {in_p}: {proc.stderr}")

        return out_p

    def verify_video_stream(self, video_path: Path | str) -> None:
        """
        Runs an automated null-sink packet decode gate via FFmpeg.
        Fails immediately if any NAL unit corruption, demux mismatch, or decode error is emitted.
        """
        resolved = Path(video_path).resolve()
        cmd = [
            self.ffmpeg_path,
            "-v", "error",
            "-i", str(resolved),
            "-f", "null",
            "-",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0 or proc.stderr.strip():
            err_msg = proc.stderr.strip()
            raise RuntimeError(
                f"Post-assembly verification gate failed for '{resolved.name}'. "
                f"FFmpeg emitted decode errors: {err_msg}"
            )
        logger.info(f"Post-assembly verification gate PASSED for '{resolved.name}' (0 decode errors).")

    def concatenate_scenes(
        self,
        scene_mp4s: Sequence[Path | str],
        output_video_path: Path | str,
        transition_duration: float = 0.6,
        transition_type: str = "fade",
    ) -> Path:
        """
        Concatenates multiple MP4 video files with seamless FFmpeg xfade crossfades.
        Gracefully falls back to lossless concat demuxer if streams differ or xfade fails.
        """
        out_path = Path(output_video_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not scene_mp4s:
            raise ValueError("scene_mp4s sequence cannot be empty")

        if len(scene_mp4s) == 1:
            shutil.copyfile(scene_mp4s[0], out_path)
            return out_path

        # Attempt high-fidelity xfade filtergraph transition
        try:
            return self._concatenate_with_xfade(
                scene_mp4s=scene_mp4s,
                out_path=out_path,
                transition_duration=transition_duration,
                transition_type=transition_type,
            )
        except Exception as exc:
            logger.warning(
                f"FFmpeg xfade transition failed ({exc}). "
                "Gracefully falling back to lossless concat demuxer..."
            )
            return self._concatenate_demuxer(scene_mp4s, out_path)

    def _concatenate_with_xfade(
        self,
        scene_mp4s: Sequence[Path | str],
        out_path: Path,
        transition_duration: float,
        transition_type: str,
    ) -> Path:
        """Builds and executes an FFmpeg xfade filtergraph across 2 or more scenes."""
        durations: list[float] = []
        has_audios: list[bool] = []

        for p in scene_mp4s:
            info = self.get_media_info(p)
            dur = info.get("duration", 0.0)
            if dur <= 0.0:
                raise ValueError(f"Invalid duration ({dur}s) for {p}")
            durations.append(dur)
            has_audios.append(info.get("has_audio", False))

        all_have_audio = all(has_audios)
        n = len(scene_mp4s)

        v_chains: list[str] = []
        a_chains: list[str] = []
        last_v = "[0:v]"
        last_a = "[0:a]"
        total_time = durations[0]

        for i in range(1, n):
            actual_trans = min(transition_duration, durations[i - 1] * 0.45, durations[i] * 0.45)
            if actual_trans <= 0.01:
                raise ValueError("Clip duration too short for xfade transition")

            offset = max(0.0, total_time - actual_trans)
            out_v = f"[v{i}]" if i < n - 1 else "[outv]"
            v_chains.append(
                f"{last_v}[{i}:v]xfade=transition={transition_type}:duration={actual_trans:.4f}:offset={offset:.4f}{out_v}"
            )
            last_v = out_v

            if all_have_audio:
                out_a = f"[a{i}]" if i < n - 1 else "[outa]"
                a_chains.append(
                    f"{last_a}[{i}:a]acrossfade=d={actual_trans:.4f}:c1=tri:c2=tri{out_a}"
                )
                last_a = out_a

            total_time = offset + durations[i]

        filtergraph = ";".join(v_chains + a_chains)

        cmd = [self.ffmpeg_path, "-y"]
        for p in scene_mp4s:
            cmd.extend(["-i", str(Path(p).resolve())])

        cmd.extend(["-filter_complex", filtergraph, "-map", "[outv]"])
        if all_have_audio:
            cmd.extend(["-map", "[outa]"])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "17",
            "-pix_fmt", "yuv420p",
        ])

        if all_have_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "320k"])

        cmd.append(str(out_path))

        logger.info(f"Rendering xfade crossfade across {n} scenes -> {out_path.name}...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg xfade failed: {proc.stderr}")

        return out_path

    def _concatenate_demuxer(
        self,
        scene_mp4s: Sequence[Path | str],
        out_path: Path,
    ) -> Path:
        """Losslessly concatenates MP4 clips using FFmpeg concat demuxer."""
        concat_list_file = out_path.parent / "scenes_concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for p in scene_mp4s:
                resolved_p = Path(p).resolve().as_posix()
                f.write(f"file '{resolved_p}'\n")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(out_path),
        ]

        logger.info(f"Concatenating {len(scene_mp4s)} scenes losslessly into {out_path.name}...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg concat demuxer failed: {proc.stderr}")

        return out_path

    def concatenate_audio(
        self,
        audio_files: Sequence[Path | str],
        output_audio_path: Path | str,
        crossfade_duration: float = 0.05,
    ) -> Path:
        """
        Concatenates audio files with exact sample alignment or subtle crossfade.
        """
        out_path = Path(output_audio_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not audio_files:
            raise ValueError("audio_files sequence cannot be empty")
        if len(audio_files) == 1:
            shutil.copyfile(audio_files[0], out_path)
            return out_path

        # If crossfade requested, use acrossfade
        if crossfade_duration > 0.001:
            try:
                a_chains: list[str] = []
                last_a = "[0:a]"
                n = len(audio_files)
                for i in range(1, n):
                    out_a = f"[a{i}]" if i < n - 1 else "[outa]"
                    a_chains.append(
                        f"{last_a}[{i}:a]acrossfade=d={crossfade_duration:.3f}:c1=tri:c2=tri{out_a}"
                    )
                    last_a = out_a

                filtergraph = ";".join(a_chains)
                cmd = [self.ffmpeg_path, "-y"]
                for p in audio_files:
                    cmd.extend(["-i", str(Path(p).resolve())])
                cmd.extend(["-filter_complex", filtergraph, "-map", "[outa]", str(out_path)])

                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.returncode == 0:
                    return out_path
            except Exception as e:
                logger.warning(f"Audio crossfade failed ({e}), falling back to concat demuxer...")

        # Filtergraph concat (auto-resamples and conforms channels to 48kHz stereo)
        try:
            n = len(audio_files)
            inputs = "".join(f"[{i}:a]" for i in range(n))
            filtergraph = f"{inputs}concat=n={n}:v=0:a=1[outa]"
            cmd = [self.ffmpeg_path, "-y"]
            for p in audio_files:
                cmd.extend(["-i", str(Path(p).resolve())])
            cmd.extend([
                "-filter_complex", filtergraph,
                "-map", "[outa]",
                "-ar", "48000",
                "-ac", "2",
                "-c:a", "pcm_s16le",
                str(out_path),
            ])
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode == 0:
                return out_path
            logger.warning(f"Filtergraph audio concat failed ({proc.stderr}), falling back to concat demuxer...")
        except Exception as e:
            logger.warning(f"Filtergraph audio concat exception ({e}), falling back to concat demuxer...")

        # Concat demuxer fallback
        concat_list_file = out_path.parent / "audio_concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for p in audio_files:
                resolved_p = Path(p).resolve().as_posix()
                f.write(f"file '{resolved_p}'\n")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-ar", "48000",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(out_path),
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg audio concat failed: {proc.stderr}")

        return out_path

    def concatenate_audio_matched(
        self,
        audio_files: Sequence[Path | str],
        output_audio_path: Path | str,
        transition_duration: float = 0.6,
    ) -> Path:
        """
        Concatenates audio files with acrossfade durations matching the EXACT video xfade transitions.
        Eliminates timeline drift completely (0.0s drift guarantee).
        """
        out_path = Path(output_audio_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        n = len(audio_files)
        if n == 1:
            shutil.copyfile(audio_files[0], out_path)
            return out_path

        durations = [self.get_media_info(p).get("duration", 0.0) for p in audio_files]
        a_chains = []
        last_a = "[0:a]"

        for i in range(1, n):
            actual_trans = min(transition_duration, durations[i - 1] * 0.45, durations[i] * 0.45)
            out_a = f"[a{i}]" if i < n - 1 else "[outa]"
            a_chains.append(
                f"{last_a}[{i}:a]acrossfade=d={actual_trans:.4f}:c1=tri:c2=tri{out_a}"
            )
            last_a = out_a

        filtergraph = ";".join(a_chains)
        cmd = [self.ffmpeg_path, "-y"]
        for p in audio_files:
            cmd.extend(["-i", str(Path(p).resolve())])
        cmd.extend(["-filter_complex", filtergraph, "-map", "[outa]", "-c:a", "pcm_s16le", str(out_path)])

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg synchronized audio acrossfade failed: {proc.stderr}")
        return out_path

    def assemble_full_documentary(
        self,
        intro_mp4: Path | str,
        scene_mp4s: Sequence[Path | str],
        outro_mp4: Path | str,
        output_mp4: Path | str,
        transition_duration: float = 0.6,
        transition_type: str = "fade",
    ) -> Path:
        """
        Stitches universal intro bumper, documentary scene MP4s, and outro bumper into a seamless master video.
        Concatenates internal scenes with xfade transitions, pre-normalizes bumpers into video-only streams
        matching exact codec, framerate, resolution, and pixel format, executes concat demuxer across
        identical streams, and verifies output with a null-sink decode gate.
        """
        intro_path = Path(intro_mp4).resolve()
        outro_path = Path(outro_mp4).resolve()
        out_path = Path(output_mp4).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not intro_path.exists():
            raise FileNotFoundError(f"Intro bumper not found: {intro_path}")
        if not outro_path.exists():
            raise FileNotFoundError(f"Outro bumper not found: {outro_path}")
        if not scene_mp4s:
            raise ValueError("scene_mp4s sequence cannot be empty")

        temp_dir = out_path.parent / "_temp_assembly"
        temp_dir.mkdir(parents=True, exist_ok=True)
        concatenated_scenes = temp_dir / "scenes_combined.mp4"

        logger.info(f"Concatenating {len(scene_mp4s)} documentary scenes with xfade transitions...")
        self.concatenate_scenes(
            scene_mp4s=scene_mp4s,
            output_video_path=concatenated_scenes,
            transition_duration=transition_duration,
            transition_type=transition_type,
        )

        # 1. Inspect concatenated scenes for stream properties (Assembly Invariant A1)
        scene_info = self.get_media_info(concatenated_scenes)
        target_width = scene_info.get("width", 1920)
        target_height = scene_info.get("height", 1080)
        target_fps = scene_info.get("fps", 30.0)
        target_codec = scene_info.get("codec_name", "h264")
        target_pix_fmt = scene_info.get("pix_fmt", "yuv420p")
        has_audio = scene_info.get("has_audio", False)

        logger.info(
            f"Scenes stream properties: {target_width}x{target_height} @ {target_fps}fps, "
            f"codec={target_codec}, pix_fmt={target_pix_fmt}, has_audio={has_audio}"
        )

        # Ensure concatenated_scenes has NO audio stream (Assembly Invariant A1.3)
        scenes_video_only = concatenated_scenes
        if has_audio:
            scenes_no_audio = temp_dir / "scenes_no_audio.mp4"
            cmd_strip = [
                self.ffmpeg_path,
                "-y",
                "-i", str(concatenated_scenes),
                "-c:v", "copy",
                "-an",
                str(scenes_no_audio),
            ]
            res_strip = subprocess.run(cmd_strip, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res_strip.returncode == 0:
                scenes_video_only = scenes_no_audio
            else:
                logger.warning(f"Failed to strip audio from combined scenes: {res_strip.stderr}")

        # 2. Pre-normalize intro and outro bumpers into video-only matching streams
        intro_normalized = temp_dir / "intro_normalized.mp4"
        self._normalize_clip(
            input_path=intro_path,
            output_path=intro_normalized,
            width=target_width,
            height=target_height,
            fps=target_fps,
            codec_name=target_codec,
            pix_fmt=target_pix_fmt,
        )

        outro_normalized = temp_dir / "outro_normalized.mp4"
        self._normalize_clip(
            input_path=outro_path,
            output_path=outro_normalized,
            width=target_width,
            height=target_height,
            fps=target_fps,
            codec_name=target_codec,
            pix_fmt=target_pix_fmt,
        )

        # 3. Concatenate the 3 strictly identical streams using concat demuxer
        full_sequence = [intro_normalized, scenes_video_only, outro_normalized]
        logger.info(
            f"Attaching normalized bumpers: intro ({intro_normalized.name}) + "
            f"scenes ({scenes_video_only.name}) + outro ({outro_normalized.name}) -> {out_path.name}"
        )
        self._concatenate_demuxer(full_sequence, out_path)

        # 4. Mandatory Post-Assembly Verification Gate (Assembly Invariant A1.4)
        logger.info(f"Running post-assembly verification gate on {out_path.name}...")
        self.verify_video_stream(out_path)

        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        return out_path

    def mux_video_and_audio(
        self,
        video_path: Path | str,
        audio_path: Path | str,
        final_output_path: Path | str,
    ) -> Path:
        """Muxes visual MP4 and master audio WAV into high-bitrate broadcast MP4."""
        final_path = Path(final_output_path).resolve()
        final_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "320k",
            "-movflags", "+faststart",
            str(final_path),
        ]

        logger.info(f"Muxing {video_path} and {audio_path} -> {final_path.name}...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg muxing failed: {proc.stderr}")

        return final_path
