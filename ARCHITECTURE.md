# IntuiSim Engine Architecture

## 1. Architectural Invariants & Boundary Discipline

IntuiSim enforces a strict decoupled architecture separating pure simulation geometry, audio synthesis, headless time stepping, and hardware encoding.

```
                    +------------------------------------+
                    |       Markdown Lesson Script       |
                    +-----------------+------------------+
                                      |
                                      v
                    +------------------------------------+
                    |   Master Orchestrator Pipeline     |
                    |      (engine/orchestrator.py)      |
                    +-----+-----------------------+------+
                          |                       |
                          v                       v
               +----------------------+  +---------------------+
               |   Audio Subsystem    |  |  Compiler Subsystem |
               | (TTS, Aligner, Mast) |  | (Renderer, Stepper) |
               +----------+-----------+  +----------+----------+
                          |                         |
                          | (WAV + Cue Timestamps)  | (Raw Frame Buffer)
                          \____________  ___________/
                                       v
                        +------------------------------+
                        |  NVENC / FFmpeg Multiplexer  |
                        |      (Output: Master MP4)    |
                        +------------------------------+
```

---

## 2. Directory & Module Ownership

| Directory | Responsibility | Invariants |
| :--- | :--- | :--- |
| `engine/orchestrator.py` | Top-level execution pipeline | Coordinates phases sequentially; deterministic exit codes. |
| `engine/audio/` | Speech synthesis & mastering | `tts.py` (Kokoro/Edge-TTS) -> `aligner.py` (Whisper word timestamps) -> `mastering.py` (EBU R128 -14 LUFS). |
| `engine/compiler/` | Simulation rendering & piping | `headless_stepper.js` advances frames via `page.evaluate()`; frames stream to NVENC via stdin pipe. |
| `engine/primitives/` | Three.js visual mathematics | Pure ES modules (`LatticeBuilder.js`, `WavepacketField.js`, etc.); zero hardcoded project paths. |
| `engine/linter/` | Pre-flight validation gate | Asserts canvas dimensions (3840x2160 or 1920x1080), animation hooks, and timing invariants. |
| `engine/packaging/` | Metadata & chapters | Generates timestamped chapter cues and YouTube metadata. |
| `assets/vendor/` | Third-party vendor libraries | Local bundles of Three.js, KaTeX, and GSAP for offline headless rendering. |
| `assets/templates/` | Headless blueprint harness | Standard HTML shell (`base_blueprint.html`) providing WebGL canvas and timeline hooks. |

---

## 3. The Deterministic Headless Stepper Contract

To avoid frame drops or micro-stutter during complex shader calculations, IntuiSim does not capture real-time screen recordings. Instead, `headless_stepper.js` controls time discretely:

1. **Initialization:** Headless Chromium is launched with flags `--disable-gpu-vsync`, `--enable-webgl`, and `--headless=new`.
2. **Hook Verification:** The scene must expose:
   - `window.__RENDER_FRAME(targetTimeSeconds)`: Advances internal simulation physics to the target time $t$.
   - `window.__SCENE_READY`: Set to `true` when WebGL shaders and materials are compiled.
3. **Discrete Advance:** The stepper calls `window.__RENDER_FRAME(frameIndex / fps)` for each frame $k \in [0, N-1]$ and extracts PNG / raw pixel buffers directly from the WebGL canvas.
4. **Encoding Stream:** The pixel buffer is piped to `ffmpeg -f rawvideo -pix_fmt rgba -s 3840x2160 -r 60 -i pipe:0 -c:v hevc_nvenc ...`.

---

## 4. Audio-Visual Timeline Synchronization

- **Voiceover Alignment:** `aligner.py` uses `faster-whisper` to output word-level timestamps $\tau_{word} = (t_{start}, t_{end})$.
- **Dynamic Cues Injection:** Timestamps are formatted into JSON cue maps (`window.__SCENE_CUES__`).
- **Camera & Shaders:** Scene scripts interpolate camera positions or highlight lattice regions when `targetTime >= cue.timestamp`.

---

## 5. Architectural Decision Records (ADRs)

- **ADR-001 (Offline Frame Stepping over Realtime Capture):** Realtime capture drops frames under heavy WebGL compute load. Stepping time deterministically guarantees 100% frame delivery at exact 60.000 fps.
- **ADR-002 (Local Kokoro ONNX over Cloud TTS APIs):** Local ONNX inference guarantees reproducible voice pitch, eliminates API costs, and runs fully offline.
- **ADR-003 (Dynamic Path Resolution):** All filesystem paths must resolve relative to `Path(__file__).resolve()` or `INTUISIM_ROOT`. Hardcoded drive letters or absolute directories are strictly banned.
