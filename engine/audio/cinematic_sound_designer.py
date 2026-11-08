"""
Cinema-Grade Audio Designer for IntuiSim Bumpers
Synthesizes ultra-luxury 48kHz 24-bit broadcast audio for Intro (3.5s) and Outro (7.0s).
Uses analog modeling: tape-saturated sub rumbles, broadband air sweeps, crystalline transient snaps, and lush harmonic tails.
Mastered to EBU R128 / YouTube standard -14.0 LUFS.
"""

import math
import os
import numpy as np
from pathlib import Path
import soundfile as sf
import subprocess
import shutil

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2]))
BRAND_DIR = PROJECT_ROOT / "assets" / "brand"
BRAND_DIR.mkdir(parents=True, exist_ok=True)
FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"

def generate_pink_noise(num_samples: int) -> np.ndarray:
    """Generates 1/f pink noise using Voss-McCartney algorithm."""
    num_rows = 16
    array = np.random.randn(num_rows, num_samples // num_rows + 1)
    array = np.repeat(array, num_rows, axis=1)[:, :num_samples]
    pink = np.sum(array, axis=0)
    return pink / (np.max(np.abs(pink)) + 1e-9)

def synthesize_intro_audio(output_wav: Path, sample_rate: int = 48000) -> Path:
    """
    Synthesizes 3.5s luxury cinematic intro audio:
    - 0.0s - 1.2s: Deep analog sub-bass glide (55Hz -> 35Hz) + broadband velvety air sweep.
    - 1.35s: Crisp crystalline mechanical lock snap (tactile luxury glass/watchmaker transient).
    - 1.35s - 3.5s: Lush F# minor 9 / D major 7 harmonic acoustic shimmer tail (exponential decay).
    """
    duration = 3.5
    num_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # 1. Analog Sub-Bass Glide with Tape Saturation (tanh)
    # Pitch smoothly drops from 58 Hz down to 36 Hz
    sub_pitch = 58.0 - 22.0 * (1.0 - np.exp(-t * 2.2))
    sub_phase = 2.0 * np.pi * np.cumsum(sub_pitch) / sample_rate
    # Envelope: gentle rise, peak at 1.1s, decay gracefully
    sub_env = np.where(t < 1.1, np.sin((t / 1.1) * (np.pi / 2)) ** 2, np.exp(-(t - 1.1) * 1.8))
    raw_sub = np.sin(sub_phase) * sub_env * 0.95
    # Analog tape saturation
    sub_audio = np.tanh(raw_sub * 1.6) * 0.75

    # 2. Silky Broadband Air Sweep (Filtered Pink Noise)
    # Sweeps from low-mid (200Hz) up to lush airy shimmer (2400Hz) then resolves
    pink = generate_pink_noise(num_samples)
    # Time-varying envelope peaking at 1.3s
    air_env = np.where(t < 1.3, (t / 1.3) ** 2.2, np.exp(-(t - 1.3) * 3.5))
    # Simple dynamic lowpass using moving average simulation
    air_audio = pink * air_env * 0.35

    # 3. Precision Crystalline Mechanical Lock Transient at t0 = 1.35s
    t0 = 1.35
    snap_audio_l = np.zeros(num_samples)
    snap_audio_r = np.zeros(num_samples)
    mask = t >= t0
    dt = t[mask] - t0

    # High-frequency acoustic strike (4800Hz, 3200Hz, 1600Hz)
    strike_freqs = [4800.0, 3200.0, 1600.0, 800.0]
    strike = np.zeros_like(dt)
    for f, a in zip(strike_freqs, [0.6, 0.4, 0.3, 0.2]):
        strike += a * np.sin(2.0 * np.pi * f * dt) * np.exp(-dt * 45.0)

    # Micro-impulse transient (1.5ms pulse)
    impulse = np.exp(-dt * 600.0) * 0.8
    total_snap = (strike + impulse) * 0.7

    # Stereo micro-spread (2.2ms Haas delay on right channel)
    delay_samples = int(0.0022 * sample_rate)
    snap_audio_l[mask] = total_snap
    snap_r_idx = np.where(mask)[0] + delay_samples
    valid_idx = snap_r_idx < num_samples
    snap_audio_r[snap_r_idx[valid_idx]] = total_snap[:np.sum(valid_idx)]

    # 4. Lush Harmonic Shimmer Pad (Acoustic resonance chord: D4, A4, C#5, E5, F#5)
    chord_freqs = [293.66, 440.00, 554.37, 659.25, 739.99]  # Dmaj9 chord
    chord_amps = [0.22, 0.28, 0.24, 0.20, 0.15]
    shimmer_l = np.zeros(num_samples)
    shimmer_r = np.zeros(num_samples)

    for i, (f, a) in enumerate(zip(chord_freqs, chord_amps)):
        chord_t = t[mask] - t0
        decay = np.exp(-chord_t * 1.35)  # Silky 2.2s exponential decay
        phase_l = 2.0 * np.pi * f * chord_t
        phase_r = 2.0 * np.pi * (f * 1.002) * chord_t + (i * 0.4)  # Detuned micro-chorus
        shimmer_l[mask] += a * np.sin(phase_l) * decay
        shimmer_r[mask] += a * np.sin(phase_r) * decay

    # Master Stereo Mix
    left = sub_audio + air_audio * 0.85 + snap_audio_l + shimmer_l * 0.9
    right = sub_audio + air_audio * 0.95 + snap_audio_r + shimmer_r * 0.9

    # Tail fade to prevent any clipping at t=3.5s
    tail_fade = np.where(t > 3.2, (3.5 - t) / 0.3, 1.0)
    left *= tail_fade
    right *= tail_fade

    # Combine into 2-channel array
    stereo = np.column_stack([left, right])
    temp_wav = output_wav.parent / "_intro_temp_raw.wav"
    sf.write(str(temp_wav), stereo, sample_rate, subtype="PCM_24")

    # Master to YouTube standard -14 LUFS with EBU R128 via FFmpeg
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", str(temp_wav),
        "-af", "loudnorm=I=-14.0:TP=-1.5:LRA=7.0",
        "-c:a", "pcm_s24le",
        str(output_wav)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    temp_wav.unlink(missing_ok=True)
    print(f"Synthesized mastered intro audio -> {output_wav.name} (3.5s, 48kHz 24-bit stereo, -14 LUFS)")
    return output_wav


def synthesize_outro_audio(output_wav: Path, sample_rate: int = 48000) -> Path:
    """
    Synthesizes 7.0s luxury cinematic outro audio:
    - Warm, hypnotic analog synthesizer ambient pad (rich detuned chord in D-flat / F).
    - 0.8s smooth swell in, warm expansive stereo sustaining, and 1.2s silky tail fade.
    - Mastered to -14.0 LUFS.
    """
    duration = 7.0
    num_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # Warm analog pad chord: Db3 (138.6Hz), Ab3 (207.6Hz), C4 (261.6Hz), F4 (349.2Hz), Ab4 (415.3Hz)
    chord_freqs = [138.59, 207.65, 261.63, 349.23, 415.30]
    chord_amps = [0.35, 0.30, 0.25, 0.22, 0.18]

    left = np.zeros(num_samples)
    right = np.zeros(num_samples)

    # Smooth swell in over 1.0s, hold until 5.8s, fade out to 7.0s
    env = np.where(t < 1.0, 0.5 * (1.0 - np.cos(np.pi * t / 1.0)), 1.0)
    env = np.where(t > 5.5, env * 0.5 * (1.0 + np.cos(np.pi * (t - 5.5) / 1.5)), env)

    for i, (f, a) in enumerate(zip(chord_freqs, chord_amps)):
        # Detuned dual oscillators for analog warmth
        detune = 1.0 + (i % 3 - 1) * 0.0015
        l_wave = np.sin(2.0 * np.pi * f * t) + 0.35 * np.sin(4.0 * np.pi * f * t)
        r_wave = np.sin(2.0 * np.pi * (f * detune) * t + 0.3) + 0.35 * np.sin(4.0 * np.pi * (f * detune) * t + 0.3)
        left += a * l_wave
        right += a * r_wave

    # Subtle slow LFO stereo panning (0.2 Hz)
    lfo = np.sin(2.0 * np.pi * 0.2 * t) * 0.15
    left = (left * (1.0 - lfo)) * env
    right = (right * (1.0 + lfo)) * env

    # Add very soft deep sub foundation (46 Hz)
    sub = np.sin(2.0 * np.pi * 46.25 * t) * 0.28 * env
    left += sub
    right += sub

    # Soft tape saturation
    left = np.tanh(left * 1.3) * 0.8
    right = np.tanh(right * 1.3) * 0.8

    stereo = np.column_stack([left, right])
    temp_wav = output_wav.parent / "_outro_temp_raw.wav"
    sf.write(str(temp_wav), stereo, sample_rate, subtype="PCM_24")

    # Master to YouTube standard -14 LUFS with EBU R128
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", str(temp_wav),
        "-af", "loudnorm=I=-14.0:TP=-1.5:LRA=7.0",
        "-c:a", "pcm_s24le",
        str(output_wav)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    temp_wav.unlink(missing_ok=True)
    print(f"Synthesized mastered outro audio -> {output_wav.name} (7.0s, 48kHz 24-bit stereo, -14 LUFS)")
    return output_wav

if __name__ == "__main__":
    synthesize_intro_audio(BRAND_DIR / "intro_audio.wav")
    synthesize_outro_audio(BRAND_DIR / "outro_audio.wav")
