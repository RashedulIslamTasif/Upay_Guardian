import re
from typing import Tuple

MAX_TEXT_LENGTH = 1000

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+prompt",
    r"override\s+security",
    r"mark\s+(this\s+)?(as\s+)?safe",
    r"you\s+are\s+now\s+an?\s+unrestricted",
    r"do\s+not\s+apply\s+rules",
    r"bypassing\s+firewall",
    r"drop\s+database",
    r"select\s+\*\s+from"
]

def sanitize_input_text(raw_text: str) -> Tuple[str, bool]:
    """
    Sanitizes untrusted customer input and strips adversarial injection attempts.
    Returns: (cleaned_text, injection_detected_flag)
    """
    if not isinstance(raw_text, str):
        return "", False
        
    text = raw_text.strip()[:MAX_TEXT_LENGTH]
    injection_detected = False
    
    # Check for direct prompt-injection triggers
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            injection_detected = True
            # Neutralize injection string
            text = re.sub(pattern, "[FILTERED_ATTEMPT]", text, flags=re.IGNORECASE)
            
    # Remove control characters and non-printable sequences
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    return cleaned.strip(), injection_detected