"""
IntuiSim YouTube SEO & Description Engine
Implements the 8-Block Description Architecture, Chapter Generator, Unicode Math Transducer,
and Companion Metadata Specifications defined in vault/DESCRIPTION_DIRECTIVES.md.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)

STEPPER_JS = Path(__file__).resolve().parents[1] / "compiler" / "headless_stepper.js"


def latex_to_unicode(text: str) -> str:
    """Converts common LaTeX mathematical symbols and constructs into clean Unicode math notation."""
    replacements = [
        (r"\\text\{([^}]+)\}", r"\1"),
        (r"\\mathrm\{([^}]+)\}", r"\1"),
        (r"\\mathbf\{([^}]+)\}", r"\1"),
        (r"\\approx", "≈"),
        (r"\\sim", "~"),
        (r"\\le", "≤"),
        (r"\\ge", "≥"),
        (r"\\cdot", "·"),
        (r"\\times", "×"),
        (r"\\pm", "±"),
        (r"\\mp", "∓"),
        (r"\\to", "→"),
        (r"\\rightarrow", "→"),
        (r"\\infty", "∞"),
        (r"\\nabla", "∇"),
        (r"\\hbar", "ℏ"),
        (r"\\partial", "∂"),
        (r"\\mu_([a-zA-Z0-9]+)", r"μ_\1"),
        (r"\\mu", "μ"),
        (r"\\theta", "θ"),
        (r"\\phi", "φ"),
        (r"\\psi", "ψ"),
        (r"\\alpha", "α"),
        (r"\\beta", "β"),
        (r"\\gamma", "γ"),
        (r"\\epsilon", "ε"),
        (r"\\eps_([a-zA-Z0-9]+)", r"ε_\1"),
        (r"\\eps", "ε"),
        (r"\\lambda", "λ"),
        (r"\\tau", "τ"),
        (r"\\sigma", "σ"),
        (r"\\rho", "ρ"),
        (r"\\omega", "ω"),
        (r"\\pi", "π"),
        (r"\\Delta", "Δ"),
        (r"\\Sigma", "Σ"),
        (r"\\Omega", "Ω"),
        (r"\\Phi", "Φ"),
        (r"\\Psi", "Ψ"),
        (r"\\sqrt\{([^}]+)\}", r"√(\1)"),
        (r"\\sqrt", "√"),
        (r"\\AA", "Å"),
        (r"\\Angstrom", "Å"),
        (r"\\circ", "°"),
        (r"\\deg", "°"),
        (r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1 / \2)"),
    ]

    res = text
    for pat, sub in replacements:
        res = re.sub(pat, sub, res)

    # Clean remaining dollar signs, slashes and braces
    res = res.replace("$", "").replace("\\", "").replace("{", "").replace("}", "")
    return res.strip()


class YouTubePackager:
    """Prepares publication-ready YouTube metadata, thumbnail beauty-shots, chapters, and SEO packages."""

    def __init__(self, node_bin: str = "node") -> None:
        self.node_path = shutil.which(node_bin) or node_bin

    def render_thumbnail(
        self,
        scene_html: Path | str,
        output_image: Path | str,
        timestamp: float = 0.0,
        width: int = 3840,
        height: int = 2160,
    ) -> Path:
        """Captures a 4K beauty-shot keyframe from the scene for YouTube thumbnail design."""
        html_path = Path(scene_html).resolve()
        out_img = Path(output_image).resolve()
        out_img.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.node_path,
            str(STEPPER_JS),
            "--mode", "snapshot",
            "--input", str(html_path),
            "--output", str(out_img),
            "--time", str(timestamp),
            "--width", str(width),
            "--height", str(height),
        ]

        logger.info(f"Rendering 4K thumbnail snapshot from {html_path.name} at {timestamp}s...")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Thumbnail render failed: {proc.stderr or proc.stdout}")

        return out_img

    def generate_metadata(
        self,
        topic: str,
        scenes: Sequence[dict[str, Any]],
        output_md: Path | str,
        intro_offset: float = 3.5,
        script_path: Path | str | None = None,
        ep_num: int = 1,
        total_eps: int = 22,
        playlist_title: str = "Semiconductor & Transistor Physics",
        playlist_url: str = "https://www.youtube.com/playlist?list=PL_INTUISIM_SEMICONDUCTORS",
    ) -> Path:
        """
        Generates the complete 8-Block YouTube Description, Titles A/B/C, Backend Tags,
        and Pinned Comment Prompt adhering strictly to vault/DESCRIPTION_DIRECTIVES.md.
        """
        out_file = Path(output_md).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Detect episode number from topic or script filename if present
        ep_match = re.search(r"(?:Lecture|Ep|Episode)\s*0?(\d+)", topic, re.IGNORECASE)
        if ep_match:
            ep_num = int(ep_match.group(1))
        elif script_path:
            script_match = re.search(r"ep0?(\d+)", Path(script_path).name, re.IGNORECASE)
            if script_match:
                ep_num = int(script_match.group(1))

        prev_ep = f"Lecture {ep_num - 1:02d}" if ep_num > 1 else None
        next_ep = f"Lecture {ep_num + 1:02d}" if ep_num < total_eps else None

        # ---------------------------------------------------------------------
        # 1. Title Variants A, B, C (Strictly <= 65 Characters)
        # ---------------------------------------------------------------------
        clean_topic = re.sub(r"^(?:Lecture|Episode)\s*\d+:\s*", "", topic).strip()
        title_a = f"{clean_topic}: First-Principles 3D Masterclass"
        if len(title_a) > 65:
            title_a = clean_topic[:65]

        title_b = f"Physics of {clean_topic} Visualized in 3D"
        if len(title_b) > 65:
            title_b = f"{clean_topic} Visualized in 3D"[:65]

        title_c = f"Why {clean_topic} Governs Modern Transistors"
        if len(title_c) > 65:
            title_c = f"The Secret of {clean_topic}"[:65]

        # ---------------------------------------------------------------------
        # 2. Block 1: The Above-the-Fold Search & Curiosity Hook (<= 160 Chars)
        # ---------------------------------------------------------------------
        hook_text = (
            f"How does {clean_topic} govern semiconductor physics from first principles? "
            f"Dissecting the quantum mechanics and atomic topology in 4K 60fps 3D."
        )
        if len(hook_text) > 160:
            hook_text = hook_text[:157] + "..."

        # ---------------------------------------------------------------------
        # 3. Block 2: Playlist Session-Loop Block
        # ---------------------------------------------------------------------
        playlist_lines = [
            f"🎓 FULL {total_eps}-LECTURE COURSE — {playlist_title}: {playlist_url}",
        ]
        if prev_ep:
            playlist_lines.append(f"⏮ Previous Lecture ({prev_ep}): [Link to {prev_ep}]")
        if next_ep:
            playlist_lines.append(f"⏭ Next Lecture ({next_ep}): [Link to {next_ep}]")
        block_2_text = "\n".join(playlist_lines)

        # ---------------------------------------------------------------------
        # 4. Block 3: Deep Technical Synopsis & Mastery Bullets
        # ---------------------------------------------------------------------
        scene_titles = [s.get("title", f"Scene {i+1}") for i, s in enumerate(scenes)]
        bullet_items = [f"• {title}" for title in scene_titles if title]
        if not bullet_items:
            bullet_items = [
                f"• First-principles geometric 3D spatial construction of {clean_topic}.",
                f"• Term-by-term live derivation of the governing physical equations.",
                f"• Laboratory parameter perturbation across temperature and electric fields.",
                f"• Multi-scale synthesis bridging atomic structure to modern nanoelectronics."
            ]

        block_3_text = (
            f"In this university masterclass, we explore the deep physics of {clean_topic}. "
            f"Rather than relying on qualitative analogies, we construct the physical system "
            f"from the ground up in full 3D WebGL simulation before deriving its governing equations "
            f"term by term.\n\n"
            f"We trace how atomic-scale quantum constraints translate directly into macroscopic "
            f"electrical characteristics, examining temperature limits, boundary conditions, "
            f"and real fabrication parameters encountered in state-of-the-art semiconductor engineering.\n\n"
            f"🔬 WHAT YOU WILL MASTER IN THIS LECTURE:\n" + "\n".join(bullet_items[:5])
        )

        # ---------------------------------------------------------------------
        # 5. Block 4: Key Equations & Physical Constants (Unicode Math)
        # ---------------------------------------------------------------------
        equations_sample = [
            "• Lattice Constant (Silicon at 300 K): a = 5.431 Å (0.5431 nm)",
            "• Atomic Number Density: N_Si = 8 / a³ ≈ 5.0 × 10²² atoms/cm³",
            "• Tetrahedral Bond Angle: θ = arccos(-1/3) ≈ 109.47°",
            "• Atomic Packing Factor: APF = (8 · (4/3)πr³) / a³ = π√3 / 16 ≈ 34.0%",
            "• Drift-Diffusion Current: J_n = q·n·μ_n·E + q·D_n·∇n",
            "• Einstein Relation: D_n / μ_n = (k_B·T) / q"
        ]
        block_4_text = "📐 GOVERNING EQUATIONS & CONSTANTS DERIVED:\n" + "\n".join(equations_sample)

        # ---------------------------------------------------------------------
        # 6. Block 5: Sample-Accurate Interactive Chapters (00:00 + 3.5s offset)
        # ---------------------------------------------------------------------
        chapters: list[str] = []
        cumulative_seconds = 0.0

        # YouTube hard requirement: Chapter 1 MUST be 00:00
        first_title = scenes[0].get("title", f"Introduction to {clean_topic}") if scenes else f"Introduction to {clean_topic}"
        chapters.append(f"00:00 — {first_title}")

        # The subsequent chapters accumulate time starting after the intro bumper (+3.5s)
        cumulative_seconds = intro_offset
        for i, s in enumerate(scenes):
            duration = float(s.get("duration", 0.0))
            if i > 0:
                mins = int(cumulative_seconds // 60)
                secs = int(cumulative_seconds % 60)
                time_str = f"{mins:02d}:{secs:02d}"
                ch_title = s.get("title", f"Part {i + 1}")
                chapters.append(f"{time_str} — {ch_title}")
            cumulative_seconds += duration

        total_mins = int(cumulative_seconds // 60)
        total_secs = int(cumulative_seconds % 60)
        block_5_text = (
            "⏱️ CHAPTERS & TIMESTAMPS:\n"
            + "\n".join(chapters)
            + f"\n\nTotal Video Runtime: {total_mins:02d}:{total_secs:02d}"
        )

        # ---------------------------------------------------------------------
        # 7. Block 6: University Syllabus & Textbook Alignment
        # ---------------------------------------------------------------------
        block_6_text = (
            "📚 UNIVERSITY SYLLABUS & TEXTBOOK ALIGNMENT:\n"
            "• Courses: Solid-State Physics, Semiconductor Device Physics (MIT 6.012 / EE130 / ECE 3050)\n"
            "• Textbooks: Streetman & Banerjee (Solid State Electronic Devices, Ch. 1–3), "
            "Sze & Ng (Physics of Semiconductor Devices, Ch. 1), "
            "Pierret (Semiconductor Device Fundamentals, Ch. 1–3)"
        )

        # ---------------------------------------------------------------------
        # 8. Block 7: Interactive 3D Simulation Lab & About IntuiSim
        # ---------------------------------------------------------------------
        block_7_text = (
            "⚡ ABOUT INTUISIM:\n"
            "At IntuiSim, we replace rote formula memorization with visceral 3D physical intuition—combining "
            "first-principles mathematical derivations with cinema-grade 4K 60fps WebGL simulations across "
            "Science, Technology, Engineering, and Mathematics.\n\n"
            "Every simulation is built with our Dual-Mode Architecture (video render + interactive student sandbox), "
            "allowing viewers to manipulate physical parameters, orbit camera angles, and test boundary limits live in 3D."
        )

        # ---------------------------------------------------------------------
        # 9. Block 8: CC-BY 4.0 Audio Attribution & 3 Bottom Hashtags
        # ---------------------------------------------------------------------
        block_8_text = (
            "🎵 AUDIO & CREDITS:\n"
            'Intro/Outro Music: "Elementary" by Scott Buckley (https://www.scottbuckley.com.au) — '
            "Licensed under Creative Commons Attribution 4.0 International (CC-BY 4.0: https://creativecommons.org/licenses/by/4.0/)\n"
            "Simulation & Rendering Engine: IntuiSim Autonomous WebGL/Three.js r169 + NVENC 60fps Pipeline\n\n"
            "#SemiconductorPhysics #SolidStatePhysics #ElectricalEngineering"
        )

        # ---------------------------------------------------------------------
        # Assemble Full 8-Block Description
        # ---------------------------------------------------------------------
        full_description = (
            f"{hook_text}\n\n"
            f"{block_2_text}\n\n"
            f"{block_3_text}\n\n"
            f"{block_4_text}\n\n"
            f"{block_5_text}\n\n"
            f"{block_6_text}\n\n"
            f"{block_7_text}\n\n"
            f"{block_8_text}"
        )

        # ---------------------------------------------------------------------
        # Backend Tags (Strictly 400–480 Characters)
        # ---------------------------------------------------------------------
        tags_list = [
            clean_topic.lower(),
            f"{clean_topic.lower()} physics",
            "semiconductor physics",
            "solid state physics",
            "silicon crystal structure",
            "diamond cubic lattice",
            "sp3 hybridization",
            "how transistors work",
            "3d physics simulation",
            "electrical engineering lecture",
            "mit 6.012",
            "atomic packing factor",
            "intuisim",
            "first principles science",
            "stem documentary 4k",
            "branch education style",
            "3blue1brown physics"
        ]
        tags_str = ", ".join(tags_list)
        if len(tags_str) > 480:
            tags_str = tags_str[:480].rsplit(", ", 1)[0]
        elif len(tags_str) < 400:
            extra_tags = ["quantum mechanics", "device physics", "band theory", "materials science"]
            for et in extra_tags:
                if len(tags_str) + len(et) + 2 <= 480:
                    tags_str += f", {et}"

        # ---------------------------------------------------------------------
        # Pinned Comment Prompt
        # ---------------------------------------------------------------------
        pinned_comment = (
            f"Quick intuition check before Lecture {ep_num + 1:02d}: If every valence electron in pure silicon is "
            f"locked into a covalent bond at 0 K, what physical mechanism enables carrier generation as temperature "
            f"rises to 300 K—and why does silicon's resistivity drop with heat while a copper wire's resistivity rises? "
            f"Drop your physical prediction below! 👇\n\n"
            f"Full {total_eps}-Lecture Course Playlist: {playlist_url}"
        )

        # ---------------------------------------------------------------------
        # Complete Markdown Document
        # ---------------------------------------------------------------------
        metadata_doc = f"""# YouTube Upload Package: {topic}

---

## 1. Suggested Video Titles (Strictly <= 65 Characters)
* **Title A (Primary Launch Hook):** `{title_a}` ({len(title_a)} chars)
* **Title B (Direct Search / Course Query):** `{title_b}` ({len(title_b)} chars)
* **Title C (Paradox / Curiosity Hook):** `{title_c}` ({len(title_c)} chars)

---

## 2. Complete 8-Block Video Description (Ready to Paste)

```text
{full_description}
```

---

## 3. Backend Video Tags ({len(tags_str)} Characters | 400–480 Limit)

```text
{tags_str}
```

---

## 4. Creator Pinned Comment Prompt

```text
{pinned_comment}
```

---

## 5. Visual Complementarity Triad Check
* **4K Thumbnail Badge Hook:** `109.5° BOND` (or Variant B: `WHY IT LEAKS`)
* **Primary Launch Title:** `{title_a}`
* **Above-the-Fold Line 1:** `{hook_text.splitlines()[0]}`
*(All three components reinforce the same topic while using distinct, non-repetitive vocabulary)*
"""

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(metadata_doc)

        logger.info(f"Generated complete 8-Block YouTube metadata at {out_file.name}")
        return out_file
