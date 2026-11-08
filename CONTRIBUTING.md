# Contributing to IntuiSim

Thank you for your interest in contributing to **IntuiSim**! We welcome contributions from researchers, educators, Three.js developers, and audio engineers.

---

## Code of Conduct & Ground Rules

1. **Zero Proprietary Leaks:** Do not commit proprietary lesson scripts, personal voice profiles, or commercial brand packages to this repository. All simulations in PRs must use generic scientific models.
2. **Deterministic Primitives:** Any new 3D primitives submitted to `engine/primitives/` must be pure ES modules that operate cleanly inside Three.js and support deterministic time stepping via `update(timeSeconds)`.
3. **No Hardcoded Absolute Paths:** All paths must resolve dynamically via relative paths or `Path(__file__).resolve()`.
4. **Offline Capability:** Simulations and renderers must not depend on external CDNs at runtime. Vendor dependencies belong in `assets/vendor/`.

---

## Development Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Minhaj009/IntuiSim.git
   cd IntuiSim
   ```

2. **Python Environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Node.js Environment:**
   ```bash
   npm install
   ```

4. **Download Model Weights:**
   ```bash
   python scripts/download_models.py
   ```

5. **Run the Quickstart Demo:**
   ```bash
   python examples/demo_harmonic_oscillator/render_demo.py
   ```

---

## Submitting Pull Requests

- Keep PRs focused on a single feature, bug fix, or primitive.
- Use Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`).
- Verify pre-commit checks with `python -m py_compile engine/**/*.py` before opening your PR.
