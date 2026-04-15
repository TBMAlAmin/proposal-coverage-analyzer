from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis import chunk_proposal, extract_requirements  # noqa: E402
from src.benchmark import run_benchmark  # noqa: E402
from src.loaders import Document  # noqa: E402
from src.matching import coverage_summary, score_requirements_against_proposal  # noqa: E402


def make_document(name: str, text: str) -> Document:
    return Document(
        name=name,
        doc_type="TXT",
        text=text,
        page_count=None,
        char_count=len(text),
        word_count=len(text.split()),
    )


class AnalysisTests(unittest.TestCase):
    def test_extract_requirements_finds_modal_statements(self) -> None:
        doc = make_document(
            "rfp.txt",
            """
            [Page 1]
            Submission Requirements

            The proposal must include a delivery timeline, pricing summary, and two case studies.
            The bidder shall describe its data retention and backup procedures.
            The solution should provide role-based access control for administrators and operators.
            """,
        )

        requirements = extract_requirements(doc)
        self.assertEqual(len(requirements), 3)
        self.assertEqual(requirements[0].category, "Submission")
        self.assertEqual(requirements[1].priority, "High")
        self.assertEqual(requirements[2].priority, "Medium")

    def test_chunk_proposal_preserves_sections(self) -> None:
        doc = make_document(
            "proposal.txt",
            """
            Access and user controls

            The system includes role-based permissions for administrators, front-desk staff, and security team members.

            Auditability and reporting

            Every visitor event is recorded with timestamped audit history. Standard dashboards include daily operational summaries and monthly activity reporting.

            Implementation and onboarding

            We propose an implementation timeline of 6 weeks and include onboarding workshops for up to 25 staff members.
            """,
        )

        chunks = chunk_proposal(doc, target_words=20)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual(chunks[0].section_hint, "Access and user controls")
        self.assertIn("implementation timeline", " ".join(chunk.text for chunk in chunks).lower())

    def test_matching_labels_covered_and_missing(self) -> None:
        rfp = make_document(
            "rfp.txt",
            """
            [Page 1]
            Mandatory Requirements

            The proposal must include a delivery timeline and pricing summary.
            The solution must support role-based access control for administrators and operators.
            The bidder shall provide annual ESG reporting.
            """,
        )
        proposal = make_document(
            "proposal.txt",
            """
            Delivery and pricing

            This proposal includes a delivery timeline, implementation plan, and pricing summary.

            Access controls

            The platform provides role-based access control for administrators and operators.
            """,
        )

        requirements = extract_requirements(rfp)
        chunks = chunk_proposal(proposal, target_words=30)
        results = score_requirements_against_proposal(requirements, chunks)
        summary = coverage_summary(results)

        self.assertEqual(results[0].status, "Covered")
        self.assertEqual(results[1].status, "Covered")
        self.assertEqual(results[2].status, "Missing")
        self.assertEqual(summary["covered"], 2)
        self.assertEqual(summary["missing"], 1)

    def test_benchmark_runner_returns_accuracy(self) -> None:
        dataset = ROOT / "data" / "benchmark" / "coverage_benchmark.json"
        report = run_benchmark(dataset)
        self.assertGreater(report["total_cases"], 0)
        self.assertGreater(report["total_items"], 0)
        self.assertGreaterEqual(report["overall_accuracy"], 0.5)


if __name__ == "__main__":
    unittest.main()
