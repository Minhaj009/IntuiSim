"""
Natural Spoken Math Voiceover Engine for IntuiSim.
Converts mathematical equations, LaTeX symbols, Greek letters, and physical expressions
into conversational, masterclass spoken English with prosodic pauses (em-dashes and commas)
for neural TTS engines (Kokoro ONNX, ElevenLabs, Edge-TTS).
"""

from __future__ import annotations

import re


GREEK_LETTERS = {
    r"\alpha": "alpha",
    r"\beta": "beta",
    r"\gamma": "gamma",
    r"\delta": "delta",
    r"\epsilon": "epsilon",
    r"\varepsilon": "epsilon",
    r"\zeta": "zeta",
    r"\eta": "eta",
    r"\theta": "theta",
    r"\vartheta": "theta",
    r"\iota": "iota",
    r"\kappa": "kappa",
    r"\lambda": "lambda",
    r"\mu": "mu",
    r"\nu": "nu",
    r"\xi": "xi",
    r"\pi": "pi",
    r"\rho": "rho",
    r"\sigma": "sigma",
    r"\tau": "tau",
    r"\upsilon": "upsilon",
    r"\phi": "phi",
    r"\varphi": "phi",
    r"\chi": "chi",
    r"\psi": "psi",
    r"\omega": "omega",
    r"\Gamma": "Gamma",
    r"\Delta": "Delta",
    r"\Theta": "Theta",
    r"\Lambda": "Lambda",
    r"\Xi": "Xi",
    r"\Pi": "Pi",
    r"\Sigma": "Sigma",
    r"\Upsilon": "Upsilon",
    r"\Phi": "Phi",
    r"\Psi": "Psi",
    r"\Omega": "Omega",
}

UNICODE_GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "κ": "kappa", "λ": "lambda", "μ": "mu", "ν": "nu", "π": "pi",
    "ρ": "rho", "σ": "sigma", "τ": "tau", "φ": "phi", "χ": "chi",
    "ψ": "psi", "ω": "omega", "ℏ": "h-bar", "Δ": "Delta", "Γ": "Gamma",
    "Λ": "Lambda", "Ω": "Omega", "Ψ": "Psi",
}

DIGIT_WORDS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}


def _extract_balanced_braces(s: str, start_idx: int) -> tuple[str, int] | None:
    if start_idx >= len(s) or s[start_idx] != "{":
        return None
    depth = 0
    for i in range(start_idx, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start_idx + 1 : i], i + 1
    return None


def _replace_fractions(text: str) -> str:
    text = re.sub(r"\b1/2\b", "one half of", text)
    text = re.sub(r"\b1/4\b", "one fourth of", text)
    text = re.sub(r"\b1/\\sqrt\{2\}\b", "one over root two, times", text)

    while r"\frac" in text:
        idx = text.find(r"\frac")
        brace1_start = text.find("{", idx)
        if brace1_start == -1 or brace1_start > idx + 6:
            break
        num_res = _extract_balanced_braces(text, brace1_start)
        if not num_res:
            break
        num_str, brace2_start = num_res
        den_res = _extract_balanced_braces(text, brace2_start)
        if not den_res:
            break
        den_str, end_pos = den_res

        num_clean = format_spoken_math(num_str).strip()
        den_clean = format_spoken_math(den_str).strip()

        if num_clean == "1":
            spoken_frac = f"one over {den_clean},"
        elif num_clean == "one":
            spoken_frac = f"one over {den_clean},"
        else:
            spoken_frac = f"{num_clean}, over {den_clean},"

        text = text[:idx] + spoken_frac + text[end_pos:]

    return text


def _replace_roots(text: str) -> str:
    while r"\sqrt" in text:
        idx = text.find(r"\sqrt")
        bracket_start = text.find("[", idx)
        opt_root = None
        brace_start = -1
        if bracket_start != -1 and bracket_start < idx + 7:
            bracket_end = text.find("]", bracket_start)
            if bracket_end != -1:
                opt_root = text[bracket_start + 1 : bracket_end].strip()
                brace_start = text.find("{", bracket_end)
        else:
            brace_start = text.find("{", idx)

        if brace_start != -1 and brace_start < idx + 15:
            res = _extract_balanced_braces(text, brace_start)
            if res:
                content, end_pos = res
                content_spoken = format_spoken_math(content).strip()
                if opt_root:
                    spoken_root = f"the {opt_root}-th root of {content_spoken},"
                else:
                    spoken_root = f"the square root of {content_spoken},"
                text = text[:idx] + spoken_root + text[end_pos:]
                continue

        m = re.match(r"\\sqrt\s*(\d+)", text[idx:])
        if m:
            text = text[:idx] + f"root {m.group(1)}" + text[idx + len(m.group(0)):]
        else:
            break

    return text


def _replace_powers(text: str) -> str:
    text = re.sub(r"\^\{2\}|\^2", " squared", text)
    text = re.sub(r"\^\{3\}|\^3", " cubed", text)
    text = re.sub(r"\^\{-1\}", " inverse", text)
    text = re.sub(r"\^\{4\}|\^4", " to the fourth", text)
    text = re.sub(r"\^\{n\}|\^n\b", " to the n", text)
    text = re.sub(r"\^\{\*\}|\^\*", " star", text)
    text = re.sub(r"\^\{\\dagger\}|\^\\dagger", " dagger", text)

    while "^" in text:
        idx = text.find("^")
        brace_start = text.find("{", idx)
        if brace_start != -1 and brace_start == idx + 1:
            res = _extract_balanced_braces(text, brace_start)
            if res:
                power_str, end_pos = res
                power_spoken = format_spoken_math(power_str).strip()
                text = text[:idx] + f" raised to the power of {power_spoken}" + text[end_pos:]
                continue
        break

    return text


def _replace_subscripts(text: str) -> str:
    subs = {
        r"2m_0": "two m-zero",
        r"2m_e": "two m-e",
        r"m_0": "m-zero",
        r"m_e": "m-e",
        r"V_0": "V-zero",
        r"k_B": "k-B",
        r"E_g": "the bandgap, E-gap",
        r"E_n": "E-n",
        r"E_+": "E-plus",
        r"E_-": "E-minus",
        r"k_x": "k-x",
        r"k_y": "k-y",
        r"k_z": "k-z",
        r"V_G": "V-G",
        r"\psi_I": "psi-one",
        r"\psi_{II}": "psi-two",
        r"\psi_+": "psi-plus",
        r"\psi_-": "psi-minus",
    }
    for k, v in subs.items():
        text = text.replace(k, v)

    text = re.sub(r"\b([A-Za-z])_([0-9])\b", r"\1-\2", text)
    text = re.sub(r"\b([A-Za-z])_\{([0-9])\}\b", r"\1-\2", text)
    return text


def _replace_relations_and_prosody(text: str) -> str:
    replacements = [
        (r"\\approx|≈", " — is approximately "),
        (r"\\equiv|≡", " — is identically defined as "),
        (r"\\neq|≠|!=", " — does not equal "),
        (r"\\ll|≪", " — is much less than "),
        (r"\\gg|≫", " — is much greater than "),
        (r"\\le\b|\\leq|≤|<=", " — is less than or equal to "),
        (r"\\ge\b|\\geq|≥|>=", " — is greater than or equal to "),
        (r"\\to\b|\\rightarrow|->|→", " — goes to "),
        (r"\\propto|∝", " — is proportional to "),
        (r"\\pm|±", "plus or minus "),
        (r"\\mp|∓", "minus or plus "),
        (r"\\cdot|·", " dot "),
        (r"\\times|×", " times "),
    ]
    for pat, rep in replacements:
        text = re.sub(pat, rep, text)

    text = re.sub(r"\s*=\s*", " — equals ", text)
    text = re.sub(r"(?<=\w)\s*<\s*(?=\w|\d)", " — is less than ", text)
    text = re.sub(r"(?<=\w)\s*>\s*(?=\w|\d)", " — is greater than ", text)
    return text


def _replace_quantum_and_functions(text: str) -> str:
    text = re.sub(r"\\hat\{H\}|\\hat\s*H|\bH-hat\b", "the Hamiltonian, H-hat,", text)
    text = re.sub(r"\\hat\{T\}|\\hat\s*T|\bT-hat\b", "the translation operator, T-hat,", text)
    text = re.sub(r"\\nabla\^2|\\nabla\^\{2\}", "the Laplacian, del-squared,", text)
    text = re.sub(r"\\nabla", "del", text)
    text = re.sub(r"\\hbar", "h-bar", text)
    text = re.sub(r"\\partial", "partial", text)
    text = re.sub(r"\\infty|∞", "infinity", text)

    text = re.sub(r"\\psi''", "the second spatial derivative of psi,", text)
    text = re.sub(r"\\psi'", "the spatial derivative of psi,", text)

    text = re.sub(r"\\sinh", "hyperbolic sine of", text)
    text = re.sub(r"\\cosh", "hyperbolic cosine of", text)
    text = re.sub(r"\\tanh", "hyperbolic tangent of", text)
    text = re.sub(r"\\sin\^2", "sine squared of", text)
    text = re.sub(r"\\cos\^2", "cosine squared of", text)
    text = re.sub(r"\\sin", "sine of", text)
    text = re.sub(r"\\cos", "cosine of", text)
    text = re.sub(r"\\tan", "tangent of", text)
    text = re.sub(r"\\exp", "exponential of", text)
    text = re.sub(r"\\ln", "natural log of", text)
    text = re.sub(r"\\log", "log of", text)

    while r"e^{" in text:
        idx = text.find(r"e^{")
        brace_start = idx + 2
        res = _extract_balanced_braces(text, brace_start)
        if res:
            exp_content, end_pos = res
            exp_spoken = format_spoken_math(exp_content).strip()
            text = text[:idx] + f"exponential of {exp_spoken}" + text[end_pos:]
        else:
            break

    text = re.sub(r"\|f\(([^)]+)\)\|", r"the absolute value of f of \1", text)
    text = re.sub(r"\|\\psi\^2\||\|\\psi\|", "the probability density, absolute psi squared,", text)
    text = re.sub(r"\|V_G\|", "the absolute value of V-G", text)
    text = re.sub(r"\|([A-Za-z0-9_\\+-]+)\|", r"the absolute value of \1", text)

    return text


def format_spoken_math(text: str) -> str:
    """
    Transforms mathematical notation and LaTeX equations into natural,
    conversational spoken masterclass English with prosodic pauses.
    """
    if not text:
        return ""

    text = re.sub(r"<!--\s*FORMULA:[^>]*-->", "", text)
    text = re.sub(r"<!--.*?-->", "", text)

    text = re.sub(r"\$\$([^\$]+)\$\$", r" \1 ", text)
    text = re.sub(r"\$([^\$]+)\$", r" \1 ", text)
    text = re.sub(r"\\\[(.*?)\\\]", r" \1 ", text)
    text = re.sub(r"\\\((.*?)\\\)", r" \1 ", text)

    kp_pattern = r"P\s*\\frac\{\\sin\(\\alpha\s*a\)\}\{\\alpha\s*a\}\s*\+\s*\\cos\(\\alpha\s*a\)\s*=\s*\\cos\(k\s*a\)"
    text = re.sub(
        kp_pattern,
        "P, times sine of alpha a over alpha a, plus cosine of alpha a — equals cosine of k a",
        text
    )

    text = re.sub(r"\bE\(k\)", "E of k", text)

    text = _replace_subscripts(text)
    text = _replace_roots(text)
    text = _replace_fractions(text)
    text = _replace_powers(text)
    text = _replace_quantum_and_functions(text)

    for latex_sym, spoken_name in GREEK_LETTERS.items():
        text = re.sub(re.escape(latex_sym) + r"(?![a-zA-Z])", spoken_name, text)

    for uni_char, spoken_name in UNICODE_GREEK.items():
        text = text.replace(uni_char, spoken_name)

    text = _replace_relations_and_prosody(text)
    text = re.sub(r"(\bpi|alpha|beta|kappa|gamma|\d+)\s*/\s*([a-zA-Z\d]+)", r"\1 over \2", text)

    text = re.sub(r"—\s*—+", "—", text)
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r",\s*—", " —", text)
    text = re.sub(r"—\s*,", " —", text)
    text = re.sub(r"\s+—\s+", " — ", text)
    text = re.sub(r",\s*\.", ".", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text
