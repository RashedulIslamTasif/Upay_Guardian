import re
import pandas as pd
from typing import List, Dict

BENGALI_SCAM_KEYWORDS = [
    "ওটিপি", "পিন", "বন্ধ", "লটারি", "পুরস্কার", "ক্যাশ", "রেজিস্ট্রেশন ফি", 
    "ভুল করে", "ফেরত", "জরুরি", "হেল্পলাইন", "এজেন্ট", "টাকা", "কোড"
]

BANGLISH_SCAM_KEYWORDS = [
    "otp", "pin", "verify", "block", "lottery", "prize", "refund",
    "bhul kore", "ferot", "urgent", "customer care", "helpline", "security"
]

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Normalize excessive spaces and retain alphanumeric, bangla unicode block (\u0980-\u09FF)
    text = text.strip()
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"[^\w\s\u0980-\u09FF]", " ", text)
    return re.sub(r"\s+", " ", text).lower()

def extract_keyword_salience(text: str) -> Dict[str, Any]:
    cleaned = clean_text(text)
    matched_bn = [kw for kw in BENGALI_SCAM_KEYWORDS if kw in cleaned]
    matched_bg = [kw for kw in BANGLISH_SCAM_KEYWORDS if kw in cleaned]
    all_matched = matched_bn + matched_bg
    
    return {
        "cleaned_text": cleaned,
        "matched_keywords": all_matched,
        "keyword_count": len(all_matched),
        "has_high_urgency_keyword": any(k in all_matched for k in ["ওটিপি", "otp", "pin", "পিন", "লটারি", "lottery"])
    }