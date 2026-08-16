"""Rule-based fraud signals for explainable risk scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from src.preprocessing.text_cleaner import TextCleaner
from src.preprocessing.feature_engineer import FeatureEngineer


@dataclass
class RuleHit:
    flag: str
    weight: float
    evidence: str


class RuleEngine:
    def __init__(self) -> None:
        self.cleaner = TextCleaner()
        self.features = FeatureEngineer()

    def evaluate_text(self, text: str) -> list[RuleHit]:
        cleaned = self.cleaner.clean(text)
        clean_text = cleaned.get("cleaned_text", "")
        feats = self.features.extract_one(clean_text, text)
        hits: list[RuleHit] = []

        def add(flag: str, weight: float, evidence: str) -> None:
            hits.append(RuleHit(flag=flag, weight=weight, evidence=evidence))

        # Remote access software (AnyDesk, QuickSupport, TeamViewer, RustDesk, Share Screen)
        if re.search(r"\b(anydesk|quick\s*support|teamviewer|rustdesk|remote access|share screen|screen share)\b", text, re.I):
            add("remote_access_app", 0.45, "Message asks for remote access or screen-sharing software.")

        # Explicit OTP/PIN/CVV credential requests
        if feats["has_otp_request"] or re.search(r"\b(tell us the otp|share otp|provide otp|enter pin|share pin|share cvv|card cvv|otp just received)\b", text, re.I):
            add("otp_or_pin_request", 0.40, "Message asks for OTP, PIN, CVV, or card credential sharing.")

        if feats["bank_with_suspicious_url"]:
            add("bank_with_link", 0.30, "Banking language appears with an external link.")
        if feats["has_upfront_fee"]:
            add("upfront_fee", 0.30, "Loan/offer asks for a fee before service.")
        if feats["has_urgency_keyword"]:
            add("urgency_pressure", 0.18, "Message uses urgent blocking/expiry pressure.")
        if feats["has_prize_keyword"]:
            add("prize_or_cashback_lure", 0.18, "Message uses prize/cashback lure language.")
        if feats["url_count"] > 0:
            add("contains_url", 0.12, "Message contains a URL.")
        if re.search(r"\b(1930|cybercrime\.gov\.in|rbi|npci)\b", text, re.I) and (feats["has_credential_request"] or feats["has_upfront_fee"]):
            add("authority_impersonation", 0.30, "Official authority terms appear with credential or fee requests.")

        # UPI collect request / PIN entry scam
        if re.search(
            r"\b(collect request|upi collect|open collect|accept.*collect|approve.*upi|enter.*pin.*receive|enter pin to receive|"
            r"send rs\.?\s*1.*verify|pay rs\.?\s*1.*verify|refund@upi|support@upi|cashback.*pending.*pay)\b",
            text, re.I,
        ):
            add("upi_collect_scam", 0.45, "Message uses UPI collect request or PIN-entry-to-receive scam pattern.")

        # Phishing email patterns: account limited/locked + link, tax refund + credentials, profile locked
        if re.search(
            r"\b(account.*limited|account.*locked|banking profile locked|profile.*locked|mailbox alert|"
            r"income tax refund|verify password|restore access|download.*form.*enter|netbanking password)\b",
            text, re.I,
        ):
            add("phishing_email_pattern", 0.35, "Message uses phishing email account-limited or tax-refund lure pattern.")

        # Check for trusted official bank domain
        if re.search(r"\b(onlinesbi\.sbi|hdfcbank\.com|icicibank\.com|axisbank\.com|bankofbaroda\.in|pnbibanking\.com)\b", text, re.I):
            add("official_bank_domain", -0.30, "Message contains a verified official bank domain.")
        return hits

    def rule_score(self, hits: List[RuleHit]) -> float:
        if not hits:
            return 0.0
        # Noisy-or style combination keeps the score bounded and interpretable.
        safe_prob = 1.0
        for hit in hits:
            safe_prob *= 1.0 - min(max(hit.weight, 0.0), 0.95)
        return round(1.0 - safe_prob, 4)
