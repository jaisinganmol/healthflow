import re
from typing import Dict, Any, Optional

class SMSParser:
    """
    Robust regex and NLP token extraction for conversational patient SMS check-ins.
    Handles typos, variations in punctuation, casing, spacing, and compound negations.
    """

    @staticmethod
    def parse_scheduling_selection(body: str) -> Optional[str]:
        """
        Extracts slot choice (A, B, C) from incoming text.
        e.g. 'B', 'Option B', 'b.', 'Choice B please'
        """
        if not body:
            return None
        cleaned = body.strip().upper()
        # Direct single letter match
        if cleaned in ["A", "B", "C"]:
            return cleaned
        # Regex search for bounded A, B, or C
        match = re.search(r"\b([A-C])\b", cleaned)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def parse_postop_symptoms(body: str) -> Dict[str, Any]:
        """
        Parses structured symptom survey response:
        Expected format: (1) Pain 1-10, (2) Incision fever/drainage, (3) Calf swelling, (4) SOB, (5) Nausea
        Examples:
          '5, no, no, no, no'
          'Pain is 4, no fever, no swelling, no breathing issues, doing ok'
          '3 no no yes no'
        """
        if not body:
            return {
                "pain_score": 5,
                "fever_or_drainage": False,
                "calf_swelling": False,
                "shortness_of_breath": False,
                "nausea_or_vomiting": False,
                "raw_response": ""
            }

        cleaned = body.strip().lower()

        # 1. Extract Pain Score (1-10)
        pain_score = 5  # default fallback
        pain_match = re.search(r"\b(10|[0-9])(?:\s*(?:/10|out of 10))?\b", cleaned)
        if pain_match:
            pain_score = int(pain_match.group(1))

        # Split into tokens by commas, semicolons, or whitespace
        tokens = [t.strip() for t in re.split(r"[,;\n\s]+", cleaned) if t.strip()]

        def token_indicates_affirmative(token: str) -> bool:
            return token in ["yes", "y", "yeah", "yep", "true", "positive"]

        # Helper to detect whether a target keyword is negated in natural language
        def is_negated(target_pattern: str, text: str) -> bool:
            # Handles "no fever", "no fever or redness", "without fever", "denies redness"
            neg_patterns = [
                rf"\b(?:no|not|denies|without|zero|negative for)\s+(?:\w+\s+){{0,3}}{target_pattern}",
                rf"\b{target_pattern}\s+(?:is|are)?\s*(?:none|zero|absent|negative|fine|normal)\b"
            ]
            return any(re.search(p, text) for p in neg_patterns)

        def has_symptom(positive_kw: str, text: str) -> bool:
            found = bool(re.search(rf"\b{positive_kw}\b", text))
            if not found:
                return False
            return not is_negated(positive_kw, text)

        # Check natural language keywords
        has_fever = has_symptom(r"(?:fever|drainage|pus|redness|infection)", cleaned)
        has_calf = has_symptom(r"(?:calf|leg\s+swelling|calf\s+pain)", cleaned)
        has_sob = has_symptom(r"(?:shortness of breath|sob|trouble breathing|chest pain)", cleaned)
        has_nausea = has_symptom(r"(?:nausea|vomiting|throwing up|nauseous)", cleaned)

        # Handle comma/token separated structured input like: "5, no, no, no, no"
        if len(tokens) >= 5:
            has_fever = has_fever or token_indicates_affirmative(tokens[1])
            has_calf = has_calf or token_indicates_affirmative(tokens[2])
            has_sob = has_sob or token_indicates_affirmative(tokens[3])
            has_nausea = has_nausea or token_indicates_affirmative(tokens[4])

        return {
            "pain_score": pain_score,
            "fever_or_drainage": has_fever,
            "calf_swelling": has_calf,
            "shortness_of_breath": has_sob,
            "nausea_or_vomiting": has_nausea,
            "raw_response": body
        }
