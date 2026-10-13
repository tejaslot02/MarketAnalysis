"""CLI script to run prompt regression evaluations and generate benchmark reports."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("DICTIONARY_DIR", str(REPO_ROOT / "data" / "dictionaries"))

from evals.prompt_regression import PromptRegressionHarness
from evals.ragas_suite import RagasSuite


def main():
    print("=======================================================")
    print("  Enterprise GenAI Prompt & Retrieval Evaluation Suite ")
    print("=======================================================")

    harness = PromptRegressionHarness()
    ragas = RagasSuite()

    skill_eval = harness.evaluate_skill_extraction()
    title_eval = harness.evaluate_title_canonicalization()

    retrieval_dataset = (
        Path(__file__).parent.parent
        / "evals"
        / "golden_datasets"
        / "retrieval_relevance_golden.jsonl"
    )
    ragas_eval = ragas.run_suite(retrieval_dataset)

    timestamp = datetime.now(timezone.utc).isoformat()
    report = {
        "timestamp": timestamp,
        "skill_extraction": skill_eval,
        "title_canonicalization": title_eval,
        "ragas_retrieval": ragas_eval,
        "overall_status": (
            "PASSED"
            if skill_eval.get("passed") and title_eval.get("passed")
            else "FAILED"
        ),
    }

    report_dir = Path(__file__).parent.parent / "evals" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"eval_report_{timestamp.replace(':', '-')[:19]}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nSkill Extraction F1 Score: {skill_eval.get('mean_f1')} (Passed: {skill_eval.get('passed')})")
    print(f"Title Canonicalization Accuracy: {title_eval.get('accuracy')} (Passed: {title_eval.get('passed')})")
    print(f"RAGAS Retrieval Composite Score: {ragas_eval.get('ragas_composite_score')}")
    print(f"\nOverall Quality Gate Status: {report['overall_status']}")
    print(f"Full report written to: {report_file}")


if __name__ == "__main__":
    main()
