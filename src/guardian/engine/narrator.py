from typing import Dict, Any, List, Tuple

def generate_customer_message(
    level: str,
    reason_codes: List[str],
    config: Dict[str, Any]
) -> Tuple[str, str]:
    """Generates crystal clear Bangla and English instructions strictly from facts."""
    reasons_cfg = config.get("reason_codes", {})
    
    bn_reasons = []
    en_reasons = []
    for code in reason_codes:
        if code in reasons_cfg:
            bn_reasons.append(reasons_cfg[code]["bn"])
            en_reasons.append(reasons_cfg[code]["en"])
            
    bn_reason_text = " ".join(bn_reasons)
    en_reason_text = " ".join(en_reasons)
    
    if level == "L0":
        return ("লেনদেনটি নিরাপদ বলে মনে হচ্ছে।", "Transaction appears normal.")
    elif level == "L1":
        return (
            f"সতর্কতা: {bn_reason_text} আপনি কি নিশ্চিতভাবে টাকা পাঠাতে চান?",
            f"Advisory: {en_reason_text} Are you sure you wish to proceed?"
        )
    elif level == "L2":
        return (
            f"নিরাপত্তা বিরতি: {bn_reason_text} আপনার একাউন্টের নিরাপত্তার স্বার্থে ১০ মিনিটের একটি বিরতি দেওয়া হয়েছে। পরিচিত কারো সাথে কথা বলুন।",
            f"Cool-off Active: {en_reason_text} A 10-minute hold has been initiated for your security. Verify with someone you trust."
        )
    elif level == "L3":
        return (
            f"যাচাইকরণ প্রয়োজন: {bn_reason_text} এই লেনদেনটি সম্পন্ন করতে আপনার বিশ্বস্ত অভিভাবক/কন্টাক্টের সম্মতি প্রয়োজন।",
            f"Co-Approval Required: {en_reason_text} This transfer requires authorization from your registered trusted contact."
        )
    else:  # L4
        return (
            f"পর্যালোচনাধীন: {bn_reason_text} লেনদেনটি সাময়িকভাবে আটকে রেখে সিকিউরিটি টিমের কাছে পর্যালোচনার জন্য পাঠানো হয়েছে। এটি সরাসরি বাতিল নয়।",
            f"Held for Review: {en_reason_text} Transaction is routed to human security specialists for manual review. Not permanently blocked."
        )

def generate_analyst_narrative(
    context: Dict[str, Any],
    risk_score: float,
    level: str,
    reasons: List[Dict[str, Any]],
    rules_triggered: List[str]
) -> str:
    """Builds an objective, factual audit narrative for fraud investigation teams."""
    uid = context.get("user_id", "UNKNOWN")
    rec = context.get("recipient_id", "UNKNOWN")
    amt = context.get("amount", 0.0)
    baseline = context.get("typical_amount", 0.0)
    vuln = context.get("vulnerability_score", 0.0)
    
    reason_lines = "; ".join([f"{r.get('reason_code')}: {r.get('en')}" for r in reasons])
    rules_text = " | ".join(rules_triggered) if rules_triggered else "None"
    
    return (
        f"DECISION: {level} (Composite Risk: {risk_score:.2f}).\n"
        f"USER: {uid} (Vulnerability Index: {vuln:.2f}) -> RECIPIENT: {rec}.\n"
        f"FINANCIAL CONTEXT: Requested ৳{amt:,.2f} vs typical baseline ৳{baseline:,.2f} "
        f"({round(amt/max(baseline, 1.0), 1)}x baseline).\n"
        f"TRIGGERED HARD RULES: {rules_text}.\n"
        f"PRIMARY ML DRIVERS: {reason_lines or 'General risk threshold elevation'}."
    )