import math
import struct
import wave
from pathlib import Path

def write_wav(file_path: Path, samples: list[float], sample_rate: int = 44100):
    """Writes normalized floating point samples (-1.0 to 1.0) to a 16-bit PCM WAV."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(file_path), "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        packed = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            int_sample = int(clamped * 32767)
            packed.extend(struct.pack("<h", int_sample))
        wav_file.writeframes(packed)

def generate_micro_click(output_path: Path, sample_rate: int = 44100):
    """Subtle 12ms tactile micro-click for UI and HUD telemetry snaps (-24 dB)."""
    duration = 0.015
    num_samples = int(sample_rate * duration)
    samples = []
    # Base peak amplitude -24 dB approx 0.063
    peak_amp = 0.065
    freq = 2400.0  # Crisp high-frequency tick
    
    for i in range(num_samples):
        t = i / sample_rate
        decay = math.exp(-t * 400.0)
        # Sine burst with rapid exponential decay
        val = peak_amp * math.sin(2.0 * math.pi * freq * t) * decay
        samples.append(val)
        
    write_wav(output_path, samples, sample_rate)

def generate_smooth_whoosh(output_path: Path, sample_rate: int = 44100):
    """Smooth 400ms low-pass transition whoosh (-24 dB)."""
    duration = 0.45
    num_samples = int(sample_rate * duration)
    samples = []
    peak_amp = 0.060
    
    for i in range(num_samples):
        t = i / sample_rate
        # Bell curve envelope
        env = math.sin(math.pi * (t / duration)) ** 2
        # Frequency sweep from 180 Hz to 650 Hz back to 140 Hz
        freq = 180.0 + 470.0 * math.sin(math.pi * (t / duration))
        val = peak_amp * math.sin(2.0 * math.pi * freq * t) * env
        samples.append(val)
        
    write_wav(output_path, samples, sample_rate)

def generate_sub_swell(output_path: Path, sample_rate: int = 44100):
    """Gentle 1.2s deep 55 Hz sub-bass swell for scale shifts and zoom-ins."""
    duration = 1.2
    num_samples = int(sample_rate * duration)
    samples = []
    peak_amp = 0.070
    freq = 55.0  # Low A
    
    for i in range(num_samples):
        t = i / sample_rate
        env = math.sin(math.pi * (t / duration)) ** 2
        val = peak_amp * math.sin(2.0 * math.pi * freq * t) * env
        samples.append(val)
        
    write_wav(output_path, samples, sample_rate)

def generate_ambient_drone(output_path: Path, duration: float = 60.0, sample_rate: int = 44100):
    """Warm minimalist ambient science drone (C minor / 65.4 Hz fundamental with warm fifth)."""
    num_samples = int(sample_rate * duration)
    samples = []
    # Master peak volume -20 dB to -24 dB
    peak_amp = 0.045
    
    f1 = 65.41   # C2
    f2 = 98.00   # G2 (Fifth)
    f3 = 130.81  # C3 (Octave)
    
    for i in range(num_samples):
        t = i / sample_rate
        # Subtle slow breathing LFO (0.1 Hz)
        lfo = 0.85 + 0.15 * math.sin(2.0 * math.pi * 0.1 * t)
        
        # Harmonic blend
        s1 = 0.60 * math.sin(2.0 * math.pi * f1 * t)
        s2 = 0.30 * math.sin(2.0 * math.pi * f2 * t + 0.5)
        s3 = 0.15 * math.sin(2.0 * math.pi * f3 * t + 1.2)
        
        val = peak_amp * (s1 + s2 + s3) * lfo
        samples.append(val)
        
    write_wav(output_path, samples, sample_rate)

if __name__ == "__main__":
    import os
    base_dir = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[2])) / "assets" / "audio"
    sfx_dir = base_dir / "sfx"
    bgm_dir = base_dir / "bgm"
    
    generate_micro_click(sfx_dir / "click_snap.wav")
    generate_smooth_whoosh(sfx_dir / "whoosh_soft.wav")
    generate_sub_swell(sfx_dir / "sub_swell.wav")
    generate_ambient_drone(bgm_dir / "ambient_drone.wav", duration=45.0)
    print("Sound bank generated successfully.")
