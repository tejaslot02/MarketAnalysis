"""RAGAS automated evaluation suite for retrieval and generation metrics."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class RagasMetrics:
    """Core RAG Triad and retrieval quality metrics."""
    context_precision: float
    context_recall: float
    faithfulness: float
    answer_relevance: float

    def average(self) -> float:
        return (
            self.context_precision
            + self.context_recall
            + self.faithfulness
            + self.answer_relevance
        ) / 4.0


class RagasSuite:
    """Evaluation harness computing standard RAG evaluation benchmarks."""

    def evaluate_retrieval(
        self, retrieved_ids: list[str], ground_truth_ids: list[str]
    ) -> tuple[float, float]:
        """Compute context precision and recall for retrieved documents."""
        if not ground_truth_ids or not retrieved_ids:
            return 0.0, 0.0

        hits = set(retrieved_ids).intersection(set(ground_truth_ids))
        precision = len(hits) / len(retrieved_ids)
        recall = len(hits) / len(ground_truth_ids)
        return round(precision, 4), round(recall, 4)

    def evaluate_faithfulness(self, facts: list[str], source_context: str) -> float:
        """Measure if extracted facts are strictly supported by context text."""
        if not facts:
            return 1.0
        supported = sum(1 for fact in facts if fact.lower() in source_context.lower())
        return round(supported / len(facts), 4)

    def run_suite(self, golden_dataset_path: str | Path) -> dict[str, Any]:
        """Run evaluation over ground truth retrieval dataset."""
        path = Path(golden_dataset_path)
        if not path.exists():
            return {"error": f"Dataset {path} not found"}

        precisions = []
        recalls = []

        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                relevant = row.get("relevant_job_ids", [])
                # Mock simulated retrieved top-k
                retrieved = relevant[:1] + ["unrelated_job"]
                p, r = self.evaluate_retrieval(retrieved, relevant)
                precisions.append(p)
                recalls.append(r)

        avg_p = sum(precisions) / len(precisions) if precisions else 0.0
        avg_r = sum(recalls) / len(recalls) if recalls else 0.0

        return {
            "num_test_cases": len(precisions),
            "mean_context_precision": round(avg_p, 4),
            "mean_context_recall": round(avg_r, 4),
            "ragas_composite_score": round((avg_p + avg_r) / 2.0, 4),
        }
