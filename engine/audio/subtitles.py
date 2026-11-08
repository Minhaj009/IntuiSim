"""
SubRip (SRT) subtitle generator from alignment JSON metadata.
Produces natural, sentence-aware, broadcast-grade subtitle cards with balanced line formatting.
Guarantees 100% strict compliance with YouTube caption ingest standards.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ARTICLES = {"a", "an", "the"}
PREPOSITIONS = {
    "between", "into", "under", "toward", "with", "in",
    "for", "from", "on", "at", "by", "about", "through",
}
QUALIFIERS = {
    "electrostatic", "electric", "silicon", "diamond", "cubic",
    "face", "interior", "drift", "diffusion", "thermal", "applied",
}
CONJUNCTIONS = {
    "and", "or", "but", "nor", "yet", "so", "because",
    "although", "when", "while", "where", "which", "that",
    "if", "as", "since",
}


def _format_srt_timestamp(seconds: float) -> str:
    total_ms = int(round(max(0.0, seconds) * 1000))
    ms = total_ms % 1000
    tot_s = total_ms // 1000
    s = tot_s % 60
    tot_m = tot_s // 60
    m = tot_m % 60
    h = tot_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_srt_timestamp(ts_str: str) -> float:
    parts = ts_str.strip().split(":")
    if len(parts) != 3:
        return 0.0
    h = int(parts[0])
    m = int(parts[1])
    s_ms = parts[2].replace(".", ",").split(",")
    s = int(s_ms[0])
    ms = int(s_ms[1]) if len(s_ms) > 1 else 0
    return h * 3600.0 + m * 60.0 + s + ms / 1000.0


def _balance_lines(text: str, max_chars_per_line: int = 42) -> str:
    """Wraps text into 1 or 2 visually balanced lines for readability."""
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= max_chars_per_line or " " not in clean:
        return clean

    mid = len(clean) // 2
    spaces = [i for i, c in enumerate(clean) if c == " "]
    if not spaces:
        return clean
    best_sp = min(spaces, key=lambda i: abs(i - mid))
    line1 = clean[:best_sp].strip()
    line2 = clean[best_sp + 1:].strip()
    return f"{line1}\n{line2}"


def _clean_token(token: str) -> str:
    """Strips outer punctuation and normalizes to lowercase."""
    return re.sub(r"^[^\w]+|[^\w]+$", "", token).lower()


def _find_best_split(s_words: list[dict]) -> int:
    """
    Finds the optimal linguistic boundary index to split a list of words.
    Uses distance penalties and linguistic scoring (punctuation, articles,
    prepositions, qualifiers, conjunctions, infinitives).
    """
    target = len(s_words) // 2
    c_start = max(3, target - 5)
    c_end = min(len(s_words) - 3, target + 5) + 1
    window = range(c_start, c_end)
    if not window:
        return max(1, min(len(s_words) - 1, target))

    def _score(cand: int) -> float:
        score = -3.5 * abs(cand - target)

        w_prev_raw = s_words[cand - 1].get("word", "").strip()
        w_prev = _clean_token(w_prev_raw)

        # Boundary punctuation bonus
        if w_prev_raw.endswith((",", ";", ":", "—")):
            score += 85.0
        # Article penalty: NEVER split after an article
        if w_prev in ARTICLES:
            score -= 100.0
        # Preposition penalty
        if w_prev in PREPOSITIONS:
            score -= 45.0
        # Qualifier penalty
        if w_prev in QUALIFIERS:
            score -= 55.0

        w_cand_raw = s_words[cand].get("word", "").strip()
        w_cand = _clean_token(w_cand_raw)

        # Conjunction bonus
        if w_cand in CONJUNCTIONS:
            score += 60.0
        # Infinitive bonus
        if w_cand == "to":
            score += 35.0
        # Preposition phrase starter bonus
        if w_cand in PREPOSITIONS:
            score += 25.0

        return score

    return max(window, key=lambda c: (_score(c), -abs(c - target)))


def _split_sentence_recursively(s_words: list[dict], max_words: int = 14) -> list[list[dict]]:
    """Recursively splits a sentence's words into syntactically coherent chunks of <= max_words."""
    if len(s_words) <= max_words:
        return [s_words]
    idx = _find_best_split(s_words)
    return _split_sentence_recursively(s_words[:idx], max_words) + _split_sentence_recursively(s_words[idx:], max_words)


def export_srt(
    alignment_json_path: str | Path,
    output_srt_path: str | Path,
    max_words_per_card: int = 14,
    min_duration: float = 1.2,
) -> Path:
    """
    Exports clean, sentence-aware SRT subtitles from Whisper alignment JSON.
    Groups words into coherent full-sentence or major-clause cards with balanced wrapping.
    Guarantees strictly positive, non-overlapping durations compliant with YouTube.
    """
    json_path = Path(alignment_json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Alignment JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    srt_path = Path(output_srt_path)
    srt_path.parent.mkdir(parents=True, exist_ok=True)

    words = data.get("words", [])

    # Fallback to segments if word-level data is unavailable
    if not words:
        segments = data.get("segments", [])
        raw_cards = []
        for seg in segments:
            st = float(seg.get("start", 0.0))
            et = float(seg.get("end", 0.0))
            txt = seg.get("text", "").strip()
            if txt:
                raw_cards.append({"start": st, "end": et, "text": txt})
    else:
        # 1. Group words into natural grammatical sentences
        sentences: list[list[dict]] = []
        curr_sent: list[dict] = []
        for w in words:
            curr_sent.append(w)
            wt = w.get("word", "").strip()
            if wt.endswith((".", "?", "!")):
                sentences.append(curr_sent)
                curr_sent = []
        if curr_sent:
            sentences.append(curr_sent)

        # 2. Decompose sentences into balanced, multi-clause cards
        raw_cards = []
        for s_words in sentences:
            parts = _split_sentence_recursively(s_words, max_words=max_words_per_card)
            for part in parts:
                if not part:
                    continue
                st = float(part[0].get("start", 0.0))
                et = float(part[-1].get("end", 0.0))
                txt = " ".join(w.get("word", "").strip() for w in part)
                raw_cards.append({"start": st, "end": et, "text": txt})

    # 3. Clean up cards: merge orphan 1-word cards if duration is tiny
    merged_cards: list[dict] = []
    for c in raw_cards:
        if not c["text"].strip():
            continue
        words_in_card = c["text"].split()
        if len(words_in_card) <= 2 and merged_cards and (c["end"] - c["start"] < 0.8):
            # Merge with previous card if close
            prev = merged_cards[-1]
            if c["start"] - prev["end"] < 1.0:
                prev["end"] = max(prev["end"], c["end"])
                prev["text"] = prev["text"] + " " + c["text"]
                continue
        merged_cards.append(c)

    # 4. Enforce strict monotonic, positive duration and avoid overlapping
    for i in range(len(merged_cards)):
        c = merged_cards[i]
        # Guarantee start is valid
        if i > 0:
            prev_end = merged_cards[i - 1]["end"]
            if c["start"] < prev_end:
                c["start"] = prev_end + 0.01

        # Enforce minimum duration
        dur = c["end"] - c["start"]
        if dur < min_duration:
            target_end = c["start"] + min_duration
            if i + 1 < len(merged_cards):
                next_start = merged_cards[i + 1]["start"]
                if next_start > c["start"] + 0.2:
                    c["end"] = min(target_end, next_start - 0.02)
                else:
                    c["end"] = c["start"] + 0.2
            else:
                c["end"] = target_end

        # Hard invariant: end MUST be greater than start by at least 150ms
        if c["end"] <= c["start"] + 0.15:
            c["end"] = c["start"] + 0.20

    # 5. Format into valid SubRip SRT
    srt_blocks = []
    for idx, c in enumerate(merged_cards, 1):
        st_str = _format_srt_timestamp(c["start"])
        et_str = _format_srt_timestamp(c["end"])
        clean_text = c["text"].replace("<", "").replace(">", "").strip()
        fmt_txt = _balance_lines(clean_text)
        srt_blocks.append(f"{idx}\n{st_str} --> {et_str}\n{fmt_txt}\n")

    srt_path.write_text("\n".join(srt_blocks).strip() + "\n", encoding="utf-8")
    return srt_path


def export_shorts_srt(
    alignment_json_path: str | Path,
    output_srt_path: str | Path,
    max_words: int = 3,
    min_duration: float = 0.3,
) -> Path:
    """
    Exports punchy, kinetic 1-3 word subtitle cards optimized for vertical YouTube Shorts.
    Guarantees strictly positive, non-overlapping durations compliant with YouTube.
    """
    json_path = Path(alignment_json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"Alignment JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    srt_path = Path(output_srt_path)
    srt_path.parent.mkdir(parents=True, exist_ok=True)

    words = data.get("words", [])
    raw_cards: list[dict[str, Any]] = []

    if not words:
        segments = data.get("segments", [])
        for seg in segments:
            seg_words = seg.get("text", "").split()
            st = float(seg.get("start", 0.0))
            et = float(seg.get("end", 0.0))
            dur = max(0.1, et - st)
            w_count = max(1, len(seg_words))
            step = dur / w_count
            for i in range(0, len(seg_words), max_words):
                chunk = seg_words[i:i + max_words]
                chunk_st = st + i * step
                chunk_et = st + min(len(seg_words), i + max_words) * step
                raw_cards.append({
                    "start": chunk_st,
                    "end": chunk_et,
                    "text": " ".join(chunk).upper(),
                })
    else:
        for i in range(0, len(words), max_words):
            chunk = words[i:i + max_words]
            if not chunk:
                continue
            chunk_st = float(chunk[0].get("start", 0.0))
            chunk_et = float(chunk[-1].get("end", 0.0))
            chunk_txt = " ".join(w.get("word", "").strip() for w in chunk).strip().upper()
            if chunk_txt:
                raw_cards.append({
                    "start": chunk_st,
                    "end": chunk_et,
                    "text": chunk_txt,
                })

    # Enforce strictly positive, non-overlapping timestamps
    for i in range(len(raw_cards)):
        c = raw_cards[i]
        if i > 0:
            prev_end = raw_cards[i - 1]["end"]
            if c["start"] < prev_end:
                c["start"] = prev_end + 0.01

        dur = c["end"] - c["start"]
        if dur < min_duration:
            target_end = c["start"] + min_duration
            if i + 1 < len(raw_cards):
                next_start = raw_cards[i + 1]["start"]
                if next_start > c["start"] + 0.15:
                    c["end"] = min(target_end, next_start - 0.01)
                else:
                    c["end"] = c["start"] + 0.15
            else:
                c["end"] = target_end

        if c["end"] <= c["start"] + 0.10:
            c["end"] = c["start"] + 0.15

    srt_blocks = []
    for idx, c in enumerate(raw_cards, 1):
        st_str = _format_srt_timestamp(c["start"])
        et_str = _format_srt_timestamp(c["end"])
        clean_text = c["text"].replace("<", "").replace(">", "").strip()
        srt_blocks.append(f"{idx}\n{st_str} --> {et_str}\n{clean_text}\n")

    srt_path.write_text("\n".join(srt_blocks).strip() + "\n", encoding="utf-8")
    return srt_path



def combine_srts(
    scene_srts_and_durations: list[tuple[str | Path, float]],
    output_master_srt: str | Path,
    crossfade_offset: float = 0.6,
    intro_offset: float = 3.5,
) -> Path:
    """
    Combines multiple scene SRT files into a single continuous master SRT,
    correctly applying accumulated time offsets, intro bumper delay,
    and sequential cue indexing. Guarantees 0 negative durations and 0 overlaps.
    """
    out_path = Path(output_master_srt)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    parsed_cues: list[dict[str, Any]] = []
    curr_offset = intro_offset

    for srt_file, duration in scene_srts_and_durations:
        f_path = Path(srt_file)
        if not f_path.exists():
            continue
        content = f_path.read_text(encoding="utf-8").strip()
        raw_blocks = re.split(r"\n\s*\n", content)

        for rb in raw_blocks:
            lines = [l.strip() for l in rb.strip().split("\n") if l.strip()]
            if len(lines) >= 3 and "-->" in lines[1]:
                t_parts = lines[1].split("-->")
                st = _parse_srt_timestamp(t_parts[0]) + curr_offset
                et = _parse_srt_timestamp(t_parts[1]) + curr_offset
                txt = "\n".join(lines[2:])
                clean_txt = txt.replace("<", "").replace(">", "").strip()

                parsed_cues.append({
                    "start": st,
                    "end": et,
                    "text": clean_txt,
                })

        curr_offset += max(0.0, duration - crossfade_offset)

    # Post-process parsed_cues to enforce YouTube compliance:
    # 1. Monotonic start times
    # 2. Strict start < end (min duration 150ms)
    # 3. Non-overlapping: prev_end <= curr_start
    final_blocks: list[str] = []
    prev_end = 0.0

    for idx, cue in enumerate(parsed_cues, 1):
        st = cue["start"]
        et = cue["end"]

        # Ensure cue starts after previous cue
        if st < prev_end:
            st = prev_end + 0.02

        if et <= st + 0.15:
            et = st + 0.20

        # Prevent overlap with next cue if known
        if idx < len(parsed_cues):
            next_raw_st = parsed_cues[idx]["start"]
            if next_raw_st > st + 0.2:
                et = min(et, next_raw_st - 0.02)
            else:
                et = st + 0.20

        prev_end = et

        st_str = _format_srt_timestamp(st)
        et_str = _format_srt_timestamp(et)
        final_blocks.append(f"{idx}\n{st_str} --> {et_str}\n{cue['text']}\n")

    out_path.write_text("\n".join(final_blocks).strip() + "\n", encoding="utf-8")
    return out_path


def validate_srt_file(srt_path: str | Path) -> dict[str, Any]:
    """
    Validates an SRT file against YouTube's strict ingestion standards.
    Returns {"valid": bool, "errors": list[str], "cues_count": int}.
    """
    p = Path(srt_path)
    if not p.exists():
        return {"valid": False, "errors": [f"File not found: {p}"], "cues_count": 0}

    content = p.read_text(encoding="utf-8").strip()
    if not content:
        return {"valid": False, "errors": ["File is empty"], "cues_count": 0}

    blocks = re.split(r"\n\s*\n", content)
    errors = []
    prev_end = -1.0

    for i, b in enumerate(blocks):
        lines = [l.strip() for l in b.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            errors.append(f"Block {i+1} has fewer than 3 lines")
            continue

        # Check index
        if not lines[0].isdigit() or int(lines[0]) != i + 1:
            errors.append(f"Block {i+1} index mismatch: expected {i+1}, got {lines[0]}")

        # Check timecode line
        m = re.match(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})$", lines[1])
        if not m:
            errors.append(f"Block {i+1} invalid timestamp format: {lines[1]}")
            continue

        sh, sm, ss, sms = map(int, m.groups()[:4])
        eh, em, es, ems = map(int, m.groups()[4:])
        st = sh * 3600.0 + sm * 60.0 + ss + sms / 1000.0
        et = eh * 3600.0 + em * 60.0 + es + ems / 1000.0

        if et <= st:
            errors.append(f"Block {i+1} non-positive duration: start={st:.3f}s, end={et:.3f}s")
        if et - st < 0.10:
            errors.append(f"Block {i+1} duration too short (<100ms): {et-st:.3f}s")
        if st < prev_end - 0.005:
            errors.append(f"Block {i+1} backwards/overlapping timestamp: start={st:.3f}s, prev_end={prev_end:.3f}s")

        prev_end = et

        # Check text
        text = " ".join(lines[2:])
        if "<" in text or ">" in text:
            errors.append(f"Block {i+1} contains unescaped angle brackets/HTML: {text}")
        if not text.strip():
            errors.append(f"Block {i+1} empty text")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "cues_count": len(blocks),
    }
