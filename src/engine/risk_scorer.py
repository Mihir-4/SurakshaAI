"""Risk score combination and level mapping."""

from __future__ import annotations

from src.config import settings


class RiskScorer:
    def level(self, score: float) -> str:
        if score < settings.RISK_LOW_MAX:
            return "low_risk"
        if score < settings.RISK_CAUTION_MAX:
            return "caution"
        if score < settings.RISK_HIGH_MAX:
            return "high_risk"
        return "very_high_risk"

    def combine(
        self,
        ml_probability: float | None = None,
        dl_probability: float | None = None,
        rule_score: float = 0.0,
        rule_hits: list | None = None,
    ) -> float:
        signals = []
        if ml_probability is not None:
            signals.append((float(ml_probability), 0.45))
        if dl_probability is not None:
            signals.append((float(dl_probability), 0.35))
        if rule_score is not None:
            signals.append((float(rule_score), 0.20 if len(signals) else 1.0))
        if not signals:
            return 0.0
        total_weight = sum(w for _, w in signals)
        score = sum(p * w for p, w in signals) / total_weight

        # CRITICAL RULE OVERRIDES:
        # Prevent weak/out-of-distribution ML/DL probabilities from suppressing obvious hard scams.
        if rule_hits:
            hit_flags = {h.flag if hasattr(h, "flag") else str(h) for h in rule_hits}

            # Hard fraud signals -> minimum high_risk score (0.72)
            critical_fraud_flags = {
                "remote_access_app",
                "otp_or_pin_request",
                "upfront_fee",
                "bank_with_link",
                "authority_impersonation",
                "upi_collect_scam",
                "phishing_email_pattern",
            }
            if hit_flags & critical_fraud_flags:
                score = max(score, 0.72)
            elif rule_score >= 0.30:
                score = max(score, 0.55)

            # Verified official bank domain without credential requests -> cap risk score to safe (0.35)
            if "official_bank_domain" in hit_flags and not (hit_flags & {"remote_access_app", "otp_or_pin_request", "upfront_fee"}):
                score = min(score, 0.35)

        return round(max(0.0, min(1.0, score)), 4)
