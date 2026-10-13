"""Output guardrails for hallucination detection and toxicity filtering."""
from __future__ import annotations

import json
import re
from typing import Any

from ai.guardrails.input_guard import GuardrailResult


class OutputGuardrail:
    """Verifies generated LLM responses for toxicity, hallucinations, and valid format."""

    DEFAULT_TOXIC_TERMS = [
        r"(?i)\b(malware|exploit|backdoor|phishing)\b",
    ]

    def __init__(self, toxic_patterns: list[str] | None = None):
        self.toxic_patterns = toxic_patterns or self.DEFAULT_TOXIC_TERMS

    def check_toxicity(self, text: str) -> list[str]:
        violations = []
        for pat in self.toxic_patterns:
            if re.search(pat, text):
                violations.append(f"Toxic term violation: {pat}")
        return violations

    def check_hallucination(
        self, facts: list[str], source_context: str
    ) -> list[str]:
        """Verify that extracted key terms are grounded in source context."""
        unsupported = []
        for fact in facts:
            if fact.lower() not in source_context.lower():
                unsupported.append(fact)
        return unsupported

    def validate(
        self,
        output_content: str | dict[str, Any],
        source_context: str | None = None,
    ) -> GuardrailResult:
        violations: list[str] = []
        text_to_check = (
            json.dumps(output_content)
            if isinstance(output_content, dict)
            else str(output_content)
        )

        # 1. Toxicity check
        toxic_violations = self.check_toxicity(text_to_check)
        violations.extend(toxic_violations)

        # 2. Hallucination check if source context provided and output is structured skills
        if source_context and isinstance(output_content, dict):
            skills = output_content.get("skills", [])
            skill_names = [
                s.get("name", "") if isinstance(s, dict) else str(s)
                for s in skills
            ]
            unsupported = self.check_hallucination(skill_names, source_context)
            if len(unsupported) > len(skill_names) * 0.5:
                violations.append(
                    f"Excessive hallucination: {len(unsupported)} ungrounded items ({unsupported[:3]})"
                )

        passed = len(violations) == 0
        return GuardrailResult(
            passed=passed,
            violations=violations,
            sanitized_text=text_to_check,
        )
