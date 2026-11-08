# IntuiSim Engine Specification

## 1. What is IntuiSim?
IntuiSim is an open-source, cinema-grade STEM documentary production engine. It bridges the gap between abstract mathematical physics and visual cinematic intuition by autonomously converting markdown lesson scripts into 60fps high-definition masterclass videos.

## 2. Who is it for?
- **Physics & Engineering Educators:** Create publication-quality 3D interactive simulations and visual explainers without manual video editing.
- **STEM Researchers:** Render crystal lattices, vector fields, and quantum wavepackets with exact mathematical precision.
- **Technical Creators:** Produce broadcast-ready educational video content powered by neural voiceovers, automated word-level subtitle alignment, and GPU-accelerated rendering.

## 3. Core Capabilities
- **Script-to-Screen Orchestration:** Pass a markdown script with timestamp directives, KaTeX formulas, and 3D scene parameters; IntuiSim coordinates voice synthesis, subtitle alignment, WebGL simulation, and video encoding automatically.
- **Synchronized 3D Simulations:** Three.js scenes run inside a deterministic headless browser stepper that advances frame-by-frame (`window.__RENDER_FRAME(t)`), guaranteeing zero frame drops or temporal jitter regardless of scene complexity.
- **Neural Voice & Timeline Alignment:** Leverages local neural text-to-speech (Kokoro-ONNX / Edge-TTS) paired with faster-whisper speech recognition to generate sample-accurate timecode cues for camera moves and visual transitions.
- **Broadcast Audio Mastering:** Integrated audio mastering engine enforces EBU R128 loudness standards (`-14 LUFS`), multi-band compression, and audio-ducking for background scores and sound effects.
- **Hardware-Accelerated Encoding:** Direct piping of raw frame buffers to NVENC HEVC / H.264 encoders via Direct3D11 / FFmpeg for lightning-fast 4K60 and 1080p60 exports.

## 4. User Workflow
1. **Define a Scene:** Create an HTML/JavaScript scene using the reusable Three.js technical primitives (e.g., `LatticeBuilder`, `WavepacketField`, `SplineTransducerHUD`).
2. **Write a Script:** Provide narration text with embedded timing directives and visual cue tags.
3. **Execute the Engine:** Run `python -m engine.orchestrator --script <path> --scene <path> --output <path>`.
4. **Collect the Master:** IntuiSim outputs the mastered video (`.mp4`), synchronized captions (`.srt`), and audio stems.
