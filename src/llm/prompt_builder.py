"""Build constrained prompts for safety explanations."""

from __future__ import annotations


class SafetyPromptBuilder:
    def build(self, analysis: dict, language: str = "en") -> str:
        return (
            "You are SurakshaAI, a financial safety assistant. "
            "Explain the risk evidence and recommended actions. "
            "Do not make a new classification; use only the supplied risk score.\n\n"
            f"Language: {language}\n"
            f"Risk score: {analysis.get('risk_score')}\n"
            f"Risk level: {analysis.get('risk_level')}\n"
            f"Channel: {analysis.get('channel')}\n"
            f"Rule flags: {analysis.get('rule_flags', [])}\n"
            f"Evidence: {analysis.get('rule_evidence', [])}\n\n"
            "Return JSON with keys: risk_summary, evidence, immediate_actions, "
            "do_not, safe_alternatives, report_guidance, emergency_contacts."
        )
