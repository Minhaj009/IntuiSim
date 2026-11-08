import json
import re
from pathlib import Path

class StemLexicon:
    """Pre-processes STEM narration text to correct TTS pronunciation errors."""
    
    def __init__(self, dict_path: Path | None = None):
        if dict_path is None:
            dict_path = Path(__file__).parent / "lexicon.json"
        
        with open(dict_path, "r", encoding="utf-8") as f:
            self.lexicon: dict[str, str] = json.load(f)
            
        # Compile word-boundary regex patterns sorted by length descending
        # to match longer compound terms first (e.g., AlGaAs before GaAs)
        sorted_keys = sorted(self.lexicon.keys(), key=len, reverse=True)
        escaped_keys = [re.escape(k) for k in sorted_keys]
        self.pattern = re.compile(r"\b(" + "|".join(escaped_keys) + r")\b")

    def translate(self, text: str) -> str:
        """Substitutes known STEM terms with their phonetic equivalents."""
        def replace_match(match: re.Match) -> str:
            token = match.group(0)
            return self.lexicon.get(token, token)
            
        return self.pattern.sub(replace_match, text)

if __name__ == "__main__":
    lexicon = StemLexicon()
    sample = "In a 3nm GAAFET, electron transport in AlGaAs reaches 1.5 THz with SiO2 dielectric and Euler calculations."
    translated = lexicon.translate(sample)
    print("Original:  ", sample)
    print("Phonetic:  ", translated)
