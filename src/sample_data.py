from __future__ import annotations

from pathlib import Path

from src.loaders import Document, load_document_from_path


BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_RFP_PATH = BASE_DIR / "data" / "sample_rfp" / "smart-campus-rfp.txt"
SAMPLE_PROPOSAL_PATH = BASE_DIR / "data" / "sample_proposal" / "smart-campus-proposal.txt"


def load_sample_documents() -> tuple[Document, Document]:
    return (
        load_document_from_path(SAMPLE_RFP_PATH),
        load_document_from_path(SAMPLE_PROPOSAL_PATH),
    )
