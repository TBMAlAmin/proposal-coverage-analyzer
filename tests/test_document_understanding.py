from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import _best_preview_excerpt, _format_document_summary  # noqa: E402
from src.loaders import Document  # noqa: E402


def make_document(name: str, text: str) -> Document:
    return Document(
        name=name,
        doc_type="PDF",
        text=text,
        page_count=3,
        char_count=len(text),
        word_count=len(text.split()),
    )


class DocumentUnderstandingTests(unittest.TestCase):
    def test_summary_handles_classic_rfp(self) -> None:
        doc = make_document(
            "power-rfp.pdf",
            "\n".join(
                [
                    "[Page 1]",
                    "Model Request For Proposal for Agreement for Procurement of Power",
                    "Government of India",
                    "",
                    "[Page 2]",
                    "TABLE OF CONTENTS",
                    "",
                    "[Page 7]",
                    "LETTER OF INVITATION",
                    "This Request for Proposal invites eligible bidders to participate in the procurement process for a power supply project.",
                    "",
                    "[Page 8]",
                    "Introduction",
                    "The utility intends to procure power under a structured bidding process.",
                    "Instructions to bidders, bid security, evaluation of bids, and pre-bid conference details are included.",
                ]
            ),
        )

        summary = _format_document_summary(doc)
        self.assertIn("Government of India", summary)
        self.assertIn("procurement of power", summary.lower())
        self.assertIn("bid evaluation", summary.lower())

    def test_preview_prefers_human_sections_over_appendix(self) -> None:
        doc = make_document(
            "services-rfp.pdf",
            "\n".join(
                [
                    "[Page 1]",
                    "APPENDIX V LIST OF PROJECT-SPECIFIC CLAUSES",
                    "Appendix material and clause references for internal drafting only.",
                    "",
                    "[Page 2]",
                    "Request for Proposal for Managed IT Services",
                    "City Transport Authority",
                    "",
                    "[Page 3]",
                    "Executive Summary",
                    "The authority seeks a managed IT services partner to modernize helpdesk operations, device management, and network monitoring across all depots.",
                    "The document explains the scope of work, service levels, implementation timeline, and submission requirements.",
                ]
            ),
        )

        preview = _best_preview_excerpt(doc)
        self.assertIn("managed it services partner", preview.lower())
        self.assertNotIn("appendix v list of project-specific clauses", preview.lower())

    def test_summary_handles_rfq_language(self) -> None:
        doc = make_document(
            "medical-rfq.pdf",
            "\n".join(
                [
                    "[Page 1]",
                    "Request for Quotation for Supply of Laboratory Consumables",
                    "Hamad Research Center",
                    "",
                    "[Page 2]",
                    "Overview",
                    "This RFQ requests quotations for laboratory consumables for a twelve-month period.",
                    "It includes technical requirements, commercial terms, delivery timelines, and submission requirements.",
                ]
            ),
        )

        summary = _format_document_summary(doc)
        self.assertIn("Request for Quotation", summary)
        self.assertIn("laboratory consumables", summary.lower())
        self.assertIn("technical requirements", summary.lower())


if __name__ == "__main__":
    unittest.main()
