from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.analysis import chunk_proposal, extract_requirements
from src.loaders import Document
from src.matching import coverage_summary, score_requirements_against_proposal


@dataclass
class BenchmarkCaseResult:
    name: str
    total: int
    correct: int
    accuracy: float
    covered_expected: int
    partial_expected: int
    missing_expected: int


def run_benchmark(dataset_path: str | Path) -> dict[str, object]:
    cases = json.loads(Path(dataset_path).read_text())
    results: list[BenchmarkCaseResult] = []
    total_items = 0
    total_correct = 0

    for case in cases:
        rfp_doc = _make_document(f"{case['name']}-rfp.txt", case["rfp_text"])
        proposal_doc = _make_document(f"{case['name']}-proposal.txt", case["proposal_text"])
        requirements = extract_requirements(rfp_doc)
        chunks = chunk_proposal(proposal_doc, target_words=45)
        matches = score_requirements_against_proposal(requirements, chunks)
        expected = case["expected_statuses"]

        correct = sum(1 for match in matches if expected.get(match.requirement.requirement_id) == match.status)
        total = len(expected)
        total_items += total
        total_correct += correct

        results.append(
            BenchmarkCaseResult(
                name=case["name"],
                total=total,
                correct=correct,
                accuracy=round(correct / total if total else 0.0, 3),
                covered_expected=sum(value == "Covered" for value in expected.values()),
                partial_expected=sum(value == "Partial" for value in expected.values()),
                missing_expected=sum(value == "Missing" for value in expected.values()),
            )
        )

    return {
        "overall_accuracy": round(total_correct / total_items if total_items else 0.0, 3),
        "total_cases": len(results),
        "total_items": total_items,
        "results": results,
    }


def _make_document(name: str, text: str) -> Document:
    return Document(
        name=name,
        doc_type="TXT",
        text=text,
        page_count=None,
        char_count=len(text),
        word_count=len(text.split()),
    )
