"""Prompt regression harness to prevent accuracy degradation across template revisions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.services.skill_extractor import extract_skills
from core.services.title_canonicalizer import canonicalize_title


class PromptRegressionHarness:
    """Evaluates prompt extraction performance against golden ground truth datasets."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or (Path(__file__).parent / "golden_datasets")

    def evaluate_skill_extraction(self) -> dict[str, Any]:
        golden_file = self.data_dir / "skill_extraction_golden.jsonl"
        if not golden_file.exists():
            return {"error": "Dataset not found"}

        f1_scores = []
        with open(golden_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                text = item["text"]
                expected = {s.lower() for s in item["expected_skills"]}

                extracted = extract_skills(text)
                predicted = {s["name"].lower() for s in extracted}

                tp = len(expected.intersection(predicted))
                fp = len(predicted - expected)
                fn = len(expected - predicted)

                precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                f1 = (
                    (2 * precision * recall) / (precision + recall)
                    if (precision + recall) > 0
                    else 0.0
                )
                f1_scores.append(f1)

        mean_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
        return {
            "test_cases": len(f1_scores),
            "mean_f1": round(mean_f1, 4),
            "passed": mean_f1 >= 0.70,
        }

    def evaluate_title_canonicalization(self) -> dict[str, Any]:
        golden_file = self.data_dir / "title_canonicalization_golden.jsonl"
        if not golden_file.exists():
            return {"error": "Dataset not found"}

        matches = 0
        total = 0
        with open(golden_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                canonical = canonicalize_title(item["raw_title"])
                total += 1
                if canonical == item["expected_canonical"]:
                    matches += 1

        accuracy = matches / total if total > 0 else 0.0
        return {
            "test_cases": total,
            "accuracy": round(accuracy, 4),
            "passed": accuracy >= 0.60,
        }
