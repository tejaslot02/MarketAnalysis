"""Input guardrails for prompt injection detection and PII redaction."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class GuardrailResult:
    """Outcome of guardrail evaluation."""
    passed: bool
    violations: list[str] = field(default_factory=list)
    sanitized_text: str = ""


class InputGuardrail:
    """Defensive input filter analyzing text before passing to LLMs."""

    DEFAULT_INJECTION_PATTERNS = [
        r"(?i)ignore (all )?(previous|above) instructions",
        r"(?i)system override",
        r"(?i)reveal (system|hidden) prompt",
        r"(?i)you are now (dan|evil|unrestricted)",
        r"(?i)developer mode activated",
        r"(?i)disregard (all )?safety",
        r"(?i)print internal (api key|credentials|database)",
    ]

    DEFAULT_PII_PATTERNS = {
        "email": (r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED_EMAIL]"),
        "phone": (r"(?:\+?1[-. ]?)?\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}", "[REDACTED_PHONE]"),
        "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
        "credit_card": (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED_CREDIT_CARD]"),
    }

    def __init__(self, policy_dir: Path | None = None):
        self.injection_patterns = list(self.DEFAULT_INJECTION_PATTERNS)
        self.pii_patterns = dict(self.DEFAULT_PII_PATTERNS)

        if policy_dir:
            self._load_policies(policy_dir)

    def _load_policies(self, policy_dir: Path) -> None:
        inj_file = policy_dir / "injection_policy.yaml"
        if inj_file.exists():
            try:
                with open(inj_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "blocked_patterns" in data:
                        self.injection_patterns = data["blocked_patterns"]
            except Exception:
                pass

        pii_file = policy_dir / "pii_policy.yaml"
        if pii_file.exists():
            try:
                with open(pii_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "pii_patterns" in data:
                        for k, v in data["pii_patterns"].items():
                            self.pii_patterns[k] = (v["regex"], v["redact_with"])
            except Exception:
                pass

    def check_injection(self, text: str) -> list[str]:
        """Detect prompt injection attempts."""
        violations = []
        for pat in self.injection_patterns:
            if re.search(pat, text):
                violations.append(f"Prompt injection detected: pattern '{pat}'")
        return violations

    def redact_pii(self, text: str) -> tuple[str, list[str]]:
        """Identify and redact personally identifiable information."""
        sanitized = text
        detected = []
        for pii_type, (regex, replacement) in self.pii_patterns.items():
            if re.search(regex, sanitized):
                detected.append(pii_type)
                sanitized = re.sub(regex, replacement, sanitized)
        return sanitized, detected

    def validate(self, text: str) -> GuardrailResult:
        """Execute complete input guardrail validation."""
        if not text:
            return GuardrailResult(passed=True, sanitized_text="")

        injection_violations = self.check_injection(text)
        sanitized, pii_detected = self.redact_pii(text)

        all_violations = list(injection_violations)
        if pii_detected:
            all_violations.append(f"PII detected and redacted: {', '.join(pii_detected)}")

        # Block if prompt injection detected
        passed = len(injection_violations) == 0

        return GuardrailResult(
            passed=passed,
            violations=all_violations,
            sanitized_text=sanitized,
        )
