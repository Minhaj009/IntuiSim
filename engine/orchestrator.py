"""
IntuiSim Master Pipeline Orchestrator
Takes Topic, Script, and Narration text -> autonomously synthesizes speech, aligns timing,
verifies WebGL blueprints, encodes with hardware NVENC, masters audio, and packages for YouTube.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import soundfile as sf

PROJECT_ROOT = Path(os.environ.get("INTUISIM_ROOT", Path(__file__).resolve().parents[1]))
INTRO_BUMPER = PROJECT_ROOT / "assets" / "brand" / "intro_bumper.mp4"
OUTRO_BUMPER = PROJECT_ROOT / "assets" / "brand" / "outro_bumper.mp4"
INTRO_AUDIO = PROJECT_ROOT / "assets" / "brand" / "intro_audio.wav"
OUTRO_AUDIO = PROJECT_ROOT / "assets" / "brand" / "outro_audio.wav"
INTRO_DURATION = 3.5
OUTRO_DURATION = 7.0

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.audio.tts import StemTTS
from engine.audio.aligner import AudioAligner
from engine.audio.subtitles import export_srt, combine_srts, export_shorts_srt, validate_srt_file
from engine.audio.mastering import AudioMaster
from engine.linter.sanity_gate import SanityGate
from engine.compiler.nvenc_stream import NvencStreamCompiler
from engine.compiler.assembler import VideoAssembler
from engine.packaging.youtube import YouTubePackager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("IntuiSimOrchestrator")


class IntuiSimPipeline:
    """End-to-end automated compilation engine for STEM educational documentaries."""

    def __init__(self) -> None:
        self.tts = StemTTS()
        self.aligner = AudioAligner(device="cpu", fallback_model="base")
        self.sanity_gate = SanityGate()
        self.compiler = NvencStreamCompiler()
        self.assembler = VideoAssembler()
        self.packager = YouTubePackager()
        self.audio_master = AudioMaster()

    def parse_markdown_script(self, script_path: Path | str) -> list[dict]:
        """Parses a Markdown script into discrete scenes with titles and narration text."""
        raw_text = Path(script_path).read_text(encoding="utf-8")
        raw_sections = [s.strip() for s in re.split(r"(?m)^##\s+", raw_text) if s.strip()]
        scenes = []

        valid_idx = 1
        for sec in raw_sections:
            lines = sec.split("\n")
            title = lines[0].strip()
            # Clean body lines from visual tags, markdown metadata, and HTML comments
            body_lines = [
                l.strip() for l in lines[1:]
                if l.strip()
                and not l.startswith("[Visual:")
                and not l.startswith("<!--")
                and not l.startswith(">")
                and not l.startswith("---")
            ]
            narration = " ".join(body_lines).strip()
            if not narration:
                continue

            # Detect archetype intent from explicit tags, episode presets, or keyword analysis
            sec_lower = sec.lower()
            title_lower = title.lower()

            # 1. Explicit Blueprint Tag Invariant: <!-- BLUEPRINT: xxx.html --> or [Blueprint: xxx]
            bp_match = re.search(r"<!--\s*BLUEPRINT:\s*([^\s>]+)\s*-->", sec, re.IGNORECASE) or re.search(r"\[Blueprint:\s*([^\]]+)\]", sec, re.IGNORECASE)

            is_ep01 = any(k in raw_text.lower() for k in ["lecture 01", "lecture 1", "episode 01", "episode 1", "silicon atom, valence shell"])
            is_ep02 = any(k in raw_text.lower() for k in ["lecture 02", "lecture 2", "episode 02", "episode 2", "bravais lattices, diamond cubic symmetry", "diamond cubic symmetry"])

            if bp_match:
                archetype = bp_match.group(1).replace(".html", "").strip()
            elif is_ep01:
                # Dedicated Cinema-Grade Blueprints for Episode 01 (Pedagogical Invariant P1)
                ep01_map = {
                    1: "ep01_scene1_anomaly",
                    2: "ep01_scene2_atom_nodes",
                    3: "ep01_scene3_sp3_math",
                    4: "ep01_scene4_perturbation",
                    5: "silicon_lattice",
                }
                archetype = ep01_map.get(valid_idx, "ep01_scene1_anomaly")
            elif is_ep02:
                # Dedicated Cinema-Grade Blueprints for Episode 02 (Rule P1 Invariant)
                ep02_map = {
                    1: "ep02_scene1_paradox",
                    2: "ep02_scene2_fcc_basis",
                    3: "ep02_scene3_octant_disassembly",
                    4: "ep02_scene4_apf_derivation",
                    5: "ep02_scene5_nuances_crescendo",
                }
                archetype = ep02_map.get(valid_idx, "ep02_scene1_paradox")
            else:
                archetype = "ep01_scene1_anomaly"
                if any(k in sec_lower for k in ["anomaly", "picoammeter", "dead insulator"]):
                    archetype = "ep01_scene1_anomaly"
                elif any(k in sec_lower for k in ["radial nodes", "isolated core", "effective core charge"]):
                    archetype = "ep01_scene2_atom_nodes"
                elif any(k in sec_lower for k in ["tetrahedral bond angle", "lcao", "antibonding"]):
                    archetype = "ep01_scene3_sp3_math"
                elif any(k in sec_lower for k in ["bloch wavepacket", "group iv", "phonon"]):
                    archetype = "ep01_scene4_perturbation"
                elif any(k in sec_lower for k in ["sp3", "hybridization", "valence", "orbital"]):
                    archetype = "ep01_sp3_hybridization"
                elif any(k in sec_lower for k in ["equation", "math", "formula", "transport", "drift", "diffusion"]):
                    archetype = "kinetic_equation"
                elif any(k in sec_lower for k in ["unit cell", "bravais", "fcc", "octant", "lattice"]):
                    archetype = "silicon_lattice"

            scenes.append({
                "scene_id": f"scene_{valid_idx:03d}",
                "index": valid_idx,
                "title": title,
                "narration": narration,
                "archetype": archetype,
            })
            valid_idx += 1

        return scenes

    def extract_scene_cues(self, align_json_path: Path, archetype: str) -> dict[str, float]:
        """
        Extracts dynamic spoken cue timestamps from Faster-Whisper alignment.json.
        Searches for key spoken phrase milestones to synchronize WebGL blueprints with speech.
        """
        if not align_json_path.exists():
            return {}

        with open(align_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        words = data.get("words", [])
        if not words:
            return {}

        norm_words = [
            re.sub(r"[^a-zA-Z0-9]", "", w.get("word", "").lower())
            for w in words
        ]

        def find_timestamp(phrases: list[str], default_t: float) -> float:
            for phrase in phrases:
                target = [re.sub(r"[^a-zA-Z0-9]", "", t.lower()) for t in phrase.split() if t]
                if not target:
                    continue
                k = len(target)
                for i in range(len(norm_words) - k + 1):
                    if norm_words[i : i + k] == target:
                        return float(words[i].get("start", default_t))
            for phrase in phrases:
                target = [re.sub(r"[^a-zA-Z0-9]", "", t.lower()) for t in phrase.split() if t]
                for tok in target:
                    if len(tok) < 3:
                        continue
                    for i, nw in enumerate(norm_words):
                        if nw == tok or (len(nw) >= 4 and tok in nw):
                            return float(words[i].get("start", default_t))
            return default_t

        dur = float(data.get("audio_duration_seconds", 60.0))

        if archetype == "silicon_lattice":
            cues = {
                "t_isolated_atom": find_timestamp(["thirty orders", "isolated silicon atom", "center sits"], dur * 0.08),
                "t_valence": find_timestamp(["four covalent lobes", "valence octet", "valence"], dur * 0.18),
                "t_bonds": find_timestamp(["one hundred nine", "109", "locks hands", "covalent bonds"], dur * 0.28),
                "t_unit_cell": find_timestamp(["diamond cubic lattice", "diamond cubic", "unit cell"], dur * 0.45),
                "t_corners": find_timestamp(["thirty four percent", "corner atoms", "corner octants"], dur * 0.60),
                "t_faces": find_timestamp(["microprocessor", "face centered", "face"], dur * 0.72),
                "t_interior": find_timestamp(["cubic box", "interior basis", "interior"], dur * 0.82),
                "t_bulk": find_timestamp(["lecture zero two", "stoichiometry", "together"], dur * 0.90),
            }
            # Enforce strict temporal monotonicity
            order = ["t_isolated_atom", "t_valence", "t_bonds", "t_unit_cell", "t_corners", "t_faces", "t_interior", "t_bulk"]
            for i in range(1, len(order)):
                prev_k, cur_k = order[i-1], order[i]
                if cues[cur_k] <= cues[prev_k]:
                    cues[cur_k] = round(cues[prev_k] + 4.0, 2)
            return cues
        elif archetype == "kinetic_equation":
            return {
                "t_overview": 0.0,
                "t_drift_group": find_timestamp(["in the drift term", "drift term", "drift"], dur * 0.18),
                "t_q": find_timestamp(["begins with q", "elementary charge", "charge"], dur * 0.20),
                "t_n": find_timestamp(["next is n", "carrier density", "conduction band"], dur * 0.32),
                "t_mu": find_timestamp(["mobility mu", "electron mobility", "mobility"], dur * 0.43),
                "t_E": find_timestamp(["electric field e", "applied electric field", "electric field"], dur * 0.60),
                "t_diff_group": find_timestamp(["in the diffusion term", "diffusion term", "diffusion"], dur * 0.67),
                "t_D": find_timestamp(["d sub n", "diffusion coefficient"], dur * 0.70),
                "t_dn_dx": find_timestamp(["dn by dx", "d n by d x", "concentration gradient", "spatial concentration gradient"], dur * 0.80),
            }
        elif archetype == "ep01_scene1_anomaly":
            cues = {
                "t_cover_title": 0.0,
                "t_curriculum_roadmap": find_timestamp(["today we explore five", "explore five foundational", "five foundational stages", "curriculum roadmap"], 17.3),
                "t_stage_1": find_timestamp(["stage one the cryogenic", "stage one cryogenic", "stage one", "cryogenic conduction anomaly"], 21.06),
                "t_stage_2": find_timestamp(["stage two the neon core", "stage two neon", "stage two", "neon core and radial nodes"], 25.22),
                "t_stage_3": find_timestamp(["stage three mathematical derivation", "stage three derivation", "stage three", "sp3 hybridization"], 29.02),
                "t_stage_4": find_timestamp(["stage four thermal band gap", "stage four thermal", "stage four", "thermal band gap perturbations"], 34.44),
                "t_stage_5": find_timestamp(["stage five the open diamond", "stage five diamond", "stage five", "diamond cubic crystal"], 38.20),
                "t_anomaly": find_timestamp(["place a flawless ingot", "pure monocrystalline silicon", "atomically pristine solid", "monocrystalline silicon", "laboratory bench"], 42.38),
                "t_ammeter": find_timestamp(["connect a megavolt", "megavolt potential", "ammeter does not", "not register a single", "picoammeter", "exceeds ten to the fourteenth", "dead insulator"], 77.72),
                "t_laser_cutaway": 95.0,
                "t_copper_contrast": find_timestamp(["block of copper", "copper conducts", "effortless fluidity", "metallic sea", "open metallic sea", "copper possesses"], 142.20),
                "t_quantum_deadlock": find_timestamp(["frozen into an immovable", "quantum deadlock", "immovable quantum", "atomic perfection", "extinguish electrical"], 164.28),
            }
            order = [
                "t_cover_title",
                "t_curriculum_roadmap",
                "t_stage_1",
                "t_stage_2",
                "t_stage_3",
                "t_stage_4",
                "t_stage_5",
                "t_anomaly",
                "t_ammeter",
                "t_laser_cutaway",
                "t_copper_contrast",
                "t_quantum_deadlock",
            ]
            for i in range(1, len(order)):
                prev_k, cur_k = order[i-1], order[i]
                if cues[cur_k] <= cues[prev_k]:
                    cues[cur_k] = round(cues[prev_k] + 1.0, 2)
            return cues
        elif archetype == "ep01_scene2_atom_nodes":
            return {
                "t_isolated_core": find_timestamp(["isolate a single silicon", "atomic number z", "fourteen elementary charges", "neon core", "shield the nucleus", "effective core charge", "plus four q"], 0.0),
                "t_m_shell": find_timestamp(["outermost principal quantum", "m shell", "principal quantum number", "ground state configuration", "three s two", "three p x", "completely vacant"], dur * 0.22),
                "t_radial_nodes": find_timestamp(["distinct radial topology", "radial nodes", "two radial nodes", "vanishes completely", "three p orbitals", "angular nodes", "internal radial node"], dur * 0.45),
                "t_promotion_payoff": find_timestamp(["apparent energetic barrier", "five point seven electron", "promote one three s", "thermodynamic penalty", "cohesive covalent bonding", "bonding payoff", "nine point two", "thermodynamic minimum"], dur * 0.72),
            }
        elif archetype == "ep01_scene3_sp3_math":
            return {
                "t_basis_vectors": find_timestamp(["unitary linear transformation", "coordinate cube", "alternating vertices", "vector v one", "coordinates one one one"], 0.0),
                "t_sp3_morph": find_timestamp(["normalized linear superposition", "ket sp three", "spherically symmetric and isotropic", "one half into ket s", "directional p components"], dur * 0.18),
                "t_orthonormality": find_timestamp(["prove their orthonormality", "inner product", "self product", "distinct hybrids", "rigorously orthogonal"], dur * 0.38),
                "t_tetrahedral_angle": find_timestamp(["fundamental tetrahedral", "bond angle theta", "one plus three cosine", "negative one third", "one hundred nine point four", "109.47"], dur * 0.55),
                "t_lcao_bonding": find_timestamp(["two adjacent silicon atoms", "overlap head on", "constructive quantum interference", "symmetric bonding orbital", "psi sigma", "filled valence band"], dur * 0.72),
                "t_antibonding_plane": find_timestamp(["destructive interference", "antisymmetric antibonding", "psi sigma star", "nodal plane bisects", "conduction band"], dur * 0.86),
            }
        elif archetype == "ep01_scene4_perturbation":
            return {
                "t_bandgap_origin": find_timestamp(["physical origin of the semiconductor", "energy bandgap", "overlap integral s", "adjacent valence lobes"], 0.0),
                "t_group_iv_trend": find_timestamp(["traverse group iv", "periodic table", "carbon in the diamond", "five point four seven", "germanium", "gray tin", "alpha tin"], dur * 0.18),
                "t_thermal_boltzmann": find_timestamp(["thermal perturbation", "maxwell boltzmann", "fermi dirac", "absolute zero", "temperature t is zero", "exponential vanishes"], dur * 0.45),
                "t_phonon_agitation": find_timestamp(["three hundred kelvin", "thermal lattice vibrations", "quantized phonons", "ambient thermal energy", "twenty five point nine", "one point zero times ten"], dur * 0.65),
                "t_bloch_wavepackets": find_timestamp(["demolish the pervasive", "broken bond", "socket", "quantum translational symmetry", "delocalized bloch wavepackets", "collective quasiparticles"], dur * 0.82),
            }
        elif archetype == "ep01_sp3_hybridization":
            return {
                "t_isolated_atom": find_timestamp(["isolated silicon atom", "fourteen protons", "nucleus shielding", "isolated"], dur * 0.08),
                "t_radial_nodes": find_timestamp(["radial nodes", "quantum shell", "3s", "radial"], dur * 0.18),
                "t_sp3_hybridization": find_timestamp(["hybridize into", "sp3", "four equivalent lobes", "hybridization"], dur * 0.32),
                "t_tetrahedral_angle": find_timestamp(["109.5", "tetrahedral angle", "cube vertices", "109.47"], dur * 0.45),
                "t_lcao_bonding": find_timestamp(["linear combination", "lcao", "sigma bonding", "overlapping"], dur * 0.60),
                "t_promotion_payoff": find_timestamp(["promotion energy", "bonding payoff", "net energy"], dur * 0.72),
                "t_group_iv_trend": find_timestamp(["group iv", "periodic table", "carbon diamond", "bandgap"], dur * 0.83),
                "t_bloch_synthesis": find_timestamp(["bloch wavepacket", "delocalized", "diamond cubic lattice", "open lattice"], dur * 0.92),
            }
        elif archetype == "ep02_silicon_lattice":
            cues = {
                "t_corner": find_timestamp(["stand on one silicon atom", "four covalent bonds", "point upward into alternating", "alternating corners", "corner atom"], dur * 0.22),
                "t_neighbor": find_timestamp(["hop onto its nearest neighbor", "nearest neighbor", "bonds invert", "pointing downward", "opposite octants"], dur * 0.48),
                "t_inversion": find_timestamp(["rotated by one hundred eighty", "one hundred eighty degrees", "translational invariance fails", "bravais assumption", "geometric paradox"], dur * 0.70),
            }
            order = ["t_corner", "t_neighbor", "t_inversion"]
            for i in range(1, len(order)):
                prev_k, cur_k = order[i-1], order[i]
                if cues[cur_k] <= cues[prev_k]:
                    cues[cur_k] = round(cues[prev_k] + 1.0, 2)
            return cues
        return {}

    def extract_shorts_script(self, markdown_text: str) -> dict:
        """
        Extracts high-impact 35-45s Short narration from masterclass markdown script (Directive S1).
        Checks for explicit <!-- SHORT_EXTRACT_START --> tags or falls back to Scene 01 + Scene 02.
        Appends bridge sentence directing viewers to full masterclass below.
        """
        bridge_sentence = (
            "So how does adding just one phosphorus atom in a million shatter this lock "
            "and turn silicon into a transistor? Tap the full 4K masterclass linked right below."
        )

        # 1. Explicit Markdown Extraction Markers (Preferred)
        match = re.search(
            r"<!--\s*SHORT_EXTRACT_START\s*-->(.*?)<!--\s*SHORT_EXTRACT_END\s*-->",
            markdown_text,
            re.DOTALL,
        )
        if match:
            block = match.group(1).strip()
            scene_refs = re.findall(r"<!--\s*(?:SCENE_\d+|SCENE):\s*([^\s>]+)\s*-->", block)
            cta_match = re.search(r"<!--\s*SHORT_CTA:\s*(.*?)\s*-->", block, re.DOTALL)
            bridge = cta_match.group(1).strip() if cta_match else bridge_sentence

            clean = re.sub(r"<!--.*?-->", "", block, flags=re.DOTALL)
            clean = re.sub(r"\[Visual:.*?\]", "", clean, flags=re.DOTALL)
            lines = [l.strip() for l in clean.split("\n") if l.strip()]
            narration = " ".join(lines)
            if bridge not in narration:
                narration = f"{narration} {bridge}".strip()

            if scene_refs:
                ref_stem = Path(scene_refs[0].split("?")[0]).stem
                arc = ref_stem if (PROJECT_ROOT / "vault" / "semiconductors" / f"{ref_stem}.html").exists() else "silicon_lattice"
            elif any(k in markdown_text.lower() for k in ["sp3", "hybridization", "valence shell"]):
                arc = "ep01_sp3_hybridization"
            else:
                arc = "silicon_lattice"
            return {
                "narration": narration,
                "scenes": scene_refs or [f"vault/semiconductors/{arc}.html"],
                "archetype": arc,
                "word_count": len(narration.split()),
                "bridge": bridge,
                "source": "explicit_tags",
            }

        # 2. Autonomous Fallback Scorer (Scene 01 + Scene 02)
        raw_sections = [s.strip() for s in re.split(r"(?m)^##\s+", markdown_text) if s.strip()]
        scenes = []
        for sec in raw_sections:
            lines = sec.split("\n")
            title = lines[0].strip().lower()
            if "scene" in title or "episode" in title:
                body_lines = [
                    l.strip()
                    for l in lines[1:]
                    if l.strip() and not l.startswith("[Visual:") and not l.startswith("---") and not l.startswith(">")
                ]
                if body_lines:
                    scenes.append({"title": lines[0].strip(), "body": " ".join(body_lines)})

        s1_text = scenes[0]["body"] if len(scenes) > 0 else ""
        s2_text = scenes[1]["body"] if len(scenes) > 1 else ""

        s1_sents = re.split(r"(?<=[.!?])\s+", s1_text)
        s2_sents = re.split(r"(?<=[.!?])\s+", s2_text)

        chosen: list[str] = []
        cur_words = 0

        # Take Scene 01 anomaly hook sentences (~40-45 words)
        for s in s1_sents:
            sw = len(s.split())
            if cur_words + sw <= 48:
                chosen.append(s)
                cur_words += sw
            else:
                break
        if not chosen and s1_sents:
            chosen.append(s1_sents[0])
            cur_words += len(s1_sents[0].split())

        # Take Scene 02 geometric construction sentences (~40-45 words)
        for s in s2_sents:
            sw = len(s.split())
            if cur_words + sw <= 88:
                chosen.append(s)
                cur_words += sw
            else:
                break

        base_narration = " ".join(chosen).strip()
        full_narration = f"{base_narration} {bridge_sentence}".strip()

        return {
            "narration": full_narration,
            "scenes": ["vault/semiconductors/silicon_lattice.html"],
            "archetype": "silicon_lattice",
            "word_count": len(full_narration.split()),
            "bridge": bridge_sentence,
            "source": "fallback",
        }

    def compile_shorts(
        self,
        topic: str,
        script_file: str | Path,
        project_id: str | None = None,
        voice: str = "documentary_cinematic",
    ) -> dict:
        """
        Compiles an autonomous 9:16 vertical companion YouTube Short (1080x1920 @ 60fps)
        from Scene 01 and Scene 02 with zero bumpers and compressed acoustic prosody.
        """
        start_time = time.time()
        script_path = Path(script_file).resolve()
        if not script_path.exists():
            raise FileNotFoundError(f"Script file not found: {script_path}")

        pid = project_id or f"{re.sub(r'[^a-zA-Z0-9_]', '_', topic.lower())}_{int(time.time())}"
        shorts_dir = PROJECT_ROOT / "projects" / pid / "shorts"
        audio_dir = shorts_dir / "audio"
        dist_dir = shorts_dir / "dist"

        for d in [audio_dir, dist_dir]:
            d.mkdir(parents=True, exist_ok=True)

        logger.info(f"=== Starting Autonomous YouTube Shorts Compilation for: '{topic}' ===")
        logger.info(f"Shorts Workspace: {shorts_dir} (1080x1920 @ 60fps, 9:16)")

        clean_topic = re.sub(r'[^a-zA-Z0-9\s:,-]', '', topic).strip()
        width, height, fps = 1080, 1920, 60

        # 1. Script Extraction
        raw_script = script_path.read_text(encoding="utf-8")
        extracted = self.extract_shorts_script(raw_script)
        narration = extracted["narration"]
        logger.info(
            f"Extracted Shorts Script ({extracted['word_count']} words, source: {extracted['source']}):\n{narration}"
        )

        # 2. Voiceover Synthesis with Compressed Pauses (Directive S5: 120ms gaps)
        voice_wav = audio_dir / "short_voice.wav"
        _, duration = self.tts.synthesize(
            narration,
            voice_wav,
            voice=voice,
            speed=1.0,
            pause_duration=0.120,
            tail_silence=0.250,
        )
        logger.info(f"Shorts Voiceover synthesized: {duration:.2f}s")

        # 3. Whisper Alignment (Strictly 0.0s offset, Directive S2)
        align_json = audio_dir / "short_alignment.json"
        self.aligner.align(voice_wav, align_json, fps=fps)

        # 4. Kinetic 2-4 Word Subtitle Card Generation (Directive S8)
        short_captions_srt = shorts_dir / "short_captions.srt"
        export_shorts_srt(align_json, short_captions_srt, max_words=3)

        # 5. Visual Blueprint Selection & Cue Binding
        archetype = extracted.get("archetype", "silicon_lattice")
        blueprint_src = PROJECT_ROOT / "vault" / "semiconductors" / f"{archetype}.html"
        if not blueprint_src.exists():
            blueprint_src = PROJECT_ROOT / "vault" / "semiconductors" / "silicon_lattice.html"

        scene_html = shorts_dir / "short_scene.html"
        shutil.copyfile(blueprint_src, scene_html)

        cues = self.extract_scene_cues(align_json, archetype)
        raw_html = scene_html.read_text(encoding="utf-8")
        cue_tag = (
            f"\n  <script>\n"
            f"    window.__SCENE_CUES__ = {json.dumps(cues)};\n"
            f"    window.__SCENE_DURATION__ = {duration:.3f};\n"
            f"    window.__SCENE_INDEX__ = 1;\n"
            f"    window.__SCENE_ID__ = 'short_scene';\n"
            f"    window.__SCENE_TITLE__ = {json.dumps(clean_topic)};\n"
            f"  </script>\n"
        )
        if "</body>" in raw_html:
            injected_html = raw_html.replace("</body>", f"{cue_tag}</body>")
        else:
            injected_html = raw_html + cue_tag
        scene_html.write_text(injected_html, encoding="utf-8")

        # 6. Pre-Render Sanity Gate (1080x1920)
        lint_res = self.sanity_gate.check_scene(scene_html, width=width, height=height)
        if not lint_res.get("valid", False):
            logger.warning(f"Sanity Gate warnings on Short scene: {lint_res.get('errors')}")

        # 7. Headless 9:16 D3D11 Stepper & Direct NVENC Hardware Encoding
        scene_visual_mp4 = dist_dir / "short_visual.mp4"
        self.compiler.render_scene(
            f"{scene_html}?aspect=9x16",
            scene_visual_mp4,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
        )

        # 8. Audio Mastering (Sidechain Ducking -18dB under -14 LUFS, Directive S5)
        bgm_path = PROJECT_ROOT / "assets" / "audio" / "bgm" / "ambient_drone.wav"
        mastered_audio = audio_dir / "short_mastered.wav"
        self.audio_master.master_scene_audio(
            voice_wav=voice_wav,
            bgm_wav=bgm_path,
            output_wav=mastered_audio,
            ducking_db=-18.0,
            target_lufs=-14.0,
        )

        # 9. Assembly & Muxing (Directive S2: ZERO intro/outro bumpers)
        master_short_mp4 = shorts_dir / "master_short.mp4"
        self.assembler.mux_video_and_audio(scene_visual_mp4, mastered_audio, master_short_mp4)

        # 10. Generate Metadata Package (short_metadata.md)
        short_metadata_md = shorts_dir / "short_metadata.md"
        clean_topic = topic.split(":")[-1].strip() if ":" in topic else topic.strip()
        short_title = f"{clean_topic} #Shorts"
        if len(short_title) > 60:
            short_title = f"{short_title[:52]}... #Shorts"

        metadata_text = f"""# YouTube Short Metadata

**Title:** {short_title}

**Hook:**
Why does an atomically perfect silicon crystal refuse to conduct electricity?
Watch the sp3 diamond-cubic lattice lock electrons into complete paralysis.

**Description:**
Why does an atomically perfect silicon crystal refuse to conduct electricity?
Watch the sp3 diamond-cubic lattice lock electrons into complete paralysis.

▼ FULL 4K MASTERCLASS LINKED BELOW:
Tap the related video linked right below this Short for the complete 15-minute quantum mechanical derivation.

#Shorts #Physics #Semiconductors
"""
        short_metadata_md.write_text(metadata_text, encoding="utf-8")

        # 11. Final Dimension & Duration Sanity Check
        sanity_check = self.sanity_gate.check_short_dimensions(master_short_mp4)
        if not sanity_check.get("valid", False):
            logger.warning(f"Shorts sanity gate issues: {sanity_check.get('errors')}")

        elapsed = time.time() - start_time
        logger.info(f"=== Autonomous YouTube Short Compiled in {elapsed:.1f}s ===")

        return {
            "project_id": pid,
            "status": "SUCCESS",
            "resolution": f"{width}x{height} @ {fps}fps",
            "duration": round(duration, 3),
            "word_count": extracted["word_count"],
            "master_short": str(master_short_mp4),
            "captions": str(short_captions_srt),
            "metadata": str(short_metadata_md),
            "bumpers_applied": False,
            "sanity_check": sanity_check,
            "shorts_dir": str(shorts_dir),
            "elapsed_seconds": round(elapsed, 2),
        }

    def run(
        self,
        topic: str,
        script_file: str | Path,
        project_id: str | None = None,
        mode: str = "draft",  # 'draft' (1080p@30) or 'master' (4K@60)
        voice: str = "documentary_cinematic",
        shorts: bool = False,
    ) -> dict:
        start_time = time.time()
        script_path = Path(script_file).resolve()
        if not script_path.exists():
            raise FileNotFoundError(f"Script file not found: {script_path}")

        pid = project_id or f"{re.sub(r'[^a-zA-Z0-9_]', '_', topic.lower())}_{int(time.time())}"
        project_dir = PROJECT_ROOT / "projects" / pid
        audio_dir = project_dir / "audio"
        scenes_dir = project_dir / "scenes"
        dist_dir = project_dir / "dist"

        for d in [audio_dir, scenes_dir, dist_dir]:
            d.mkdir(parents=True, exist_ok=True)

        logger.info(f"=== Starting IntuiSim Compilation for: '{topic}' ===")
        logger.info(f"Project Workspace: {project_dir} (Mode: {mode.upper()})")

        # Resolution & FPS profiles
        if mode == "master":
            width, height, fps = 3840, 2160, 60
        else:
            width, height, fps = 1920, 1080, 30

        # Step 1: Script Parsing
        scenes = self.parse_markdown_script(script_path)
        logger.info(f"Parsed {len(scenes)} scenes from script.")

        # Enforce Rule P1: Dedicated Multi-Scene Architecture & Rule M3: Watertight Solid Geometries Gate
        bp_sources = []
        for sc in scenes:
            bp_n = f"{sc['archetype']}.html"
            bp_path = PROJECT_ROOT / "vault" / "math" / bp_n if sc["archetype"] == "kinetic_equation" else PROJECT_ROOT / "vault" / "semiconductors" / bp_n
            bp_sources.append(bp_path)

        bp_gate = self.sanity_gate.check_episode_blueprints(bp_sources)
        if not bp_gate.get("valid", False):
            for err in bp_gate.get("errors", []):
                logger.error(f"[SANITY GATE FAILURE] {err}")
            raise RuntimeError(f"SanityGate Blueprint Check FAILED: {bp_gate.get('errors')}")
        logger.info(f"SanityGate: {bp_gate.get('unique_blueprint_count')} unique dedicated blueprints verified for {len(scenes)} scenes.")

        scene_mp4s = []
        scene_audios = []
        total_duration = 0.0

        bgm_path = PROJECT_ROOT / "assets" / "audio" / "bgm" / "ambient_drone.wav"

        for s in scenes:
            sid = s["scene_id"]
            narration = s["narration"]
            logger.info(f"--- Processing {sid}: '{s['title']}' ---")

            # Step 2: Speech Synthesis with Cognitive Pauses
            voice_wav = audio_dir / f"{sid}_voice.wav"
            if not voice_wav.exists() and (audio_dir / f"{sid}.wav").exists():
                shutil.copyfile(audio_dir / f"{sid}.wav", voice_wav)
            align_json = audio_dir / f"{sid}_alignment.json"
            if voice_wav.exists() and align_json.exists():
                info = sf.info(str(voice_wav))
                duration = round(float(info.duration), 4)
                logger.info(f"Reusing existing voice track for {sid}: {duration:.2f}s")
            else:
                _, duration = self.tts.synthesize(narration, voice_wav, voice=voice)
                logger.info(f"Audio synthesized: {duration:.2f}s")
            s["duration"] = duration
            total_duration += duration

            # Step 3: Forced Alignment & Timing Extraction
            if not align_json.exists():
                self.aligner.align(voice_wav, align_json, fps=fps)

            # Step 4: Subtitle Generation
            srt_path = audio_dir / f"{sid}_captions.srt"
            if not srt_path.exists() or srt_path.stat().st_mtime < align_json.stat().st_mtime:
                export_srt(align_json, srt_path)

            # Step 5: Select Visual Blueprint
            blueprint_name = f"{s['archetype']}.html"
            if s["archetype"] == "kinetic_equation":
                blueprint_src = PROJECT_ROOT / "vault" / "math" / blueprint_name
            else:
                blueprint_src = PROJECT_ROOT / "vault" / "semiconductors" / blueprint_name

            scene_html = scenes_dir / f"{sid}.html"
            shutil.copyfile(blueprint_src, scene_html)

            # Dynamic Audio-Visual Cue Binding Invariant (Directive 1)
            cues = self.extract_scene_cues(align_json, s["archetype"])
            logger.info(f"Dynamic Speech Cues for {sid} ({s['archetype']}): {json.dumps(cues)}")

            raw_html = scene_html.read_text(encoding="utf-8")
            cue_tag = (
                f"\n  <script>\n"
                f"    window.__SCENE_CUES__ = {json.dumps(cues)};\n"
                f"    window.__SCENE_DURATION__ = {duration:.3f};\n"
                f"    window.__SCENE_INDEX__ = {s.get('index', 1)};\n"
                f"    window.__SCENE_ID__ = {json.dumps(sid)};\n"
                f"    window.__SCENE_TITLE__ = {json.dumps(s.get('title', ''))};\n"
                f"  </script>\n"
            )
            if "</body>" in raw_html:
                injected_html = raw_html.replace("</body>", f"{cue_tag}</body>")
            else:
                injected_html = raw_html + cue_tag
            scene_html.write_text(injected_html, encoding="utf-8")

            # Step 6: Pre-Render Sanity Linting
            lint_res = self.sanity_gate.check_scene(scene_html, width=width, height=height)
            if not lint_res.get("valid", False):
                raise RuntimeError(f"Sanity Gate rejected {sid}: {lint_res.get('errors')}")

            # Step 7: Headless Hardware NVENC Rendering (with Cache Gating)
            scene_mp4 = dist_dir / f"{sid}_visual.mp4"
            need_render = True
            if scene_mp4.exists() and scene_mp4.stat().st_size > 10000:
                try:
                    info = self.assembler.get_media_info(scene_mp4)
                    if abs(info.get("duration", 0.0) - duration) < 1.0:
                        logger.info(f"Reusing existing valid visual render for {sid}: {info['duration']:.2f}s")
                        need_render = False
                except Exception:
                    need_render = True

            if need_render:
                self.compiler.render_scene(
                    scene_html, scene_mp4, duration=duration, fps=fps, width=width, height=height
                )
            scene_mp4s.append(scene_mp4)

            # Step 8: Audio Mastering (Sidechain Ducking + -14 LUFS)
            mastered_scene_audio = audio_dir / f"{sid}_mastered.wav"
            if (
                not mastered_scene_audio.exists()
                or mastered_scene_audio.stat().st_size == 0
                or mastered_scene_audio.stat().st_mtime < voice_wav.stat().st_mtime
            ):
                self.audio_master.master_scene_audio(
                    voice_wav=voice_wav,
                    bgm_wav=bgm_path,
                    output_wav=mastered_scene_audio,
                    target_lufs=-14.0,
                )
            else:
                logger.info(f"Reusing existing mastered audio for {sid}")
            scene_audios.append(mastered_scene_audio)

        # Step 9: Final Assembly & Concat with Universal Bumpers (Directive 19)
        logger.info("Assembling final master documentary video with Universal Bumpers...")
        concat_visual_mp4 = dist_dir / "concatenated_visuals.mp4"
        if INTRO_BUMPER.exists() and OUTRO_BUMPER.exists():
            self.assembler.assemble_full_documentary(
                intro_mp4=INTRO_BUMPER,
                scene_mp4s=scene_mp4s,
                outro_mp4=OUTRO_BUMPER,
                output_mp4=concat_visual_mp4
            )
        else:
            self.assembler.concatenate_scenes(scene_mp4s, concat_visual_mp4)

        # Concat master audio with 0.0s timeline drift:
        # Match scene audio acrossfades to the EXACT video xfade transitions
        scenes_audio_combined = dist_dir / "scenes_audio_matched.wav"
        self.assembler.concatenate_audio_matched(
            scene_audios,
            scenes_audio_combined,
            transition_duration=0.6,
        )

        concat_audio_wav = dist_dir / "concatenated_audio.wav"
        all_audios = []
        if INTRO_AUDIO.exists():
            all_audios.append(INTRO_AUDIO)
        all_audios.append(scenes_audio_combined)
        if OUTRO_AUDIO.exists():
            all_audios.append(OUTRO_AUDIO)

        self.assembler.concatenate_audio(all_audios, concat_audio_wav, crossfade_duration=0.0)
        total_duration += (INTRO_DURATION + OUTRO_DURATION)

        # Final Mux
        final_mp4 = project_dir / f"{pid}_master.mp4"
        self.assembler.mux_video_and_audio(concat_visual_mp4, concat_audio_wav, final_mp4)

        # Step 10: Packaging (4K Thumbnail + Metadata + Chapters)
        thumbnail_png = project_dir / "thumbnail_4k.png"
        studio_html = PROJECT_ROOT / "vault" / "semiconductors" / "thumbnail_studio.html"
        if studio_html.exists():
            self.packager.render_thumbnail(studio_html, thumbnail_png, timestamp=0.0)
        else:
            lead_scene = scenes_dir / "scene_001.html"
            self.packager.render_thumbnail(lead_scene, thumbnail_png, timestamp=3.0)

        metadata_md = project_dir / "youtube_metadata.md"
        self.packager.generate_metadata(topic, scenes, metadata_md, intro_offset=INTRO_DURATION)

        # Combine all scene subtitles into master captions with accumulated time offset
        master_srt = project_dir / "master_captions.srt"
        scene_srts_and_durations = [
            (audio_dir / f"{s['scene_id']}_captions.srt", float(s.get("duration", 0.0)))
            for s in scenes
        ]
        combine_srts(
            scene_srts_and_durations,
            master_srt,
            crossfade_offset=0.6,
            intro_offset=INTRO_DURATION,
        )
        srt_lint = validate_srt_file(master_srt)
        if not srt_lint.get("valid", False):
            raise RuntimeError(f"Master subtitle validation FAILED (Rule Y1): {srt_lint.get('errors')}")
        logger.info(f"Master Subtitles Validated (Rule Y1: {srt_lint.get('cues_count')} cues, 0 errors): {master_srt.name}")

        shorts_receipt = None
        if shorts:
            logger.info("Triggering Autonomous YouTube Shorts compilation...")
            shorts_receipt = self.compile_shorts(
                topic=topic,
                script_file=script_path,
                project_id=pid,
                voice=voice,
            )

        elapsed = time.time() - start_time
        logger.info(f"=== IntuiSim Compilation Completed in {elapsed:.1f}s ===")

        receipt = {
            "project_id": pid,
            "status": "SUCCESS",
            "mode": mode,
            "resolution": f"{width}x{height} @ {fps}fps",
            "total_duration": total_duration,
            "master_video": str(final_mp4),
            "thumbnail": str(thumbnail_png),
            "subtitles": str(master_srt),
            "metadata": str(metadata_md),
            "project_dir": str(project_dir),
        }
        if shorts_receipt:
            receipt["short"] = shorts_receipt
        return receipt


Orchestrator = IntuiSimPipeline


def main():
    parser = argparse.ArgumentParser(description="IntuiSim Autonomous Video Compiler")
    parser.add_argument("--topic", required=True, help="Video topic title")
    parser.add_argument("--script", required=True, help="Path to markdown script file")
    parser.add_argument("--mode", default="draft", choices=["draft", "master", "shorts"], help="Render mode")
    parser.add_argument(
        "--voice",
        default="documentary_cinematic",
        help="Voice identifier (e.g. 'documentary_cinematic', 'af_bella', 'edge:en-US-ChristopherNeural')",
    )
    parser.add_argument("--project-id", default=None, help="Optional custom project ID")
    parser.add_argument(
        "--shorts",
        action="store_true",
        help="Compile autonomous 9:16 vertical companion Short (1080x1920 @ 60fps)",
    )

    args = parser.parse_args()
    pipeline = IntuiSimPipeline()

    if args.mode == "shorts" or (args.shorts and "--mode" not in sys.argv):
        result = pipeline.compile_shorts(
            topic=args.topic,
            script_file=args.script,
            project_id=args.project_id,
            voice=args.voice,
        )
    elif args.shorts:
        result = pipeline.run(
            topic=args.topic,
            script_file=args.script,
            project_id=args.project_id,
            mode=args.mode,
            voice=args.voice,
            shorts=True,
        )
    else:
        result = pipeline.run(
            topic=args.topic,
            script_file=args.script,
            project_id=args.project_id,
            mode=args.mode,
            voice=args.voice,
        )

    print("\nINTUISIM PRODUCTION RECEIPT:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
