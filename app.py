from __future__ import annotations

import csv
from io import StringIO
import re
import textwrap

import streamlit as st

from src.analysis import chunk_proposal, extract_requirements
from src.loaders import Document, load_document
from src.matching import coverage_summary, score_requirements_against_proposal
from src.sample_data import load_sample_documents


st.set_page_config(
    page_title="RFx Coverage Analyzer",
    page_icon="files",
    layout="wide",
)


CUSTOM_CSS = """
<style>
    .stApp {
        background: #171a1f;
        color: #e5e7eb;
    }

    .block-container {
        max-width: 1160px;
        padding-top: 1.4rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #f3f4f6;
        letter-spacing: -0.02em;
    }

    .hero-card,
    .metric-card {
        background: #23272f;
        border: 1px solid #323844;
        border-radius: 14px;
        box-shadow: none;
    }

    .hero-card {
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
    }

    .hero-copy {
        color: #aeb6c2;
        font-size: 0.95rem;
        line-height: 1.55;
        max-width: 700px;
        margin-bottom: 0;
    }

    .metric-card {
        padding: 0.82rem 0.9rem;
    }

    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #98a2b3;
        margin-bottom: 0.25rem;
        font-weight: 700;
    }

    .metric-value {
        font-size: 1.25rem;
        color: #f3f4f6;
        font-weight: 700;
    }

    .caption-note {
        color: #98a2b3;
        font-size: 0.9rem;
    }

    div[data-testid="stFileUploader"] {
        background: #1c2026;
        border: 1px dashed #404957;
        padding: 0.8rem;
        border-radius: 12px;
    }

    div.stButton > button {
        background: #7dd3fc;
        color: #0f172a;
        border: none;
        border-radius: 8px;
        padding: 0.68rem 0.95rem;
        font-weight: 700;
        box-shadow: none;
        opacity: 1 !important;
    }

    div.stButton > button:hover {
        background: #bae6fd;
        color: #0f172a;
    }

    div.stButton > button:focus {
        outline: 2px solid #e0f2fe;
        outline-offset: 2px;
    }

    div.stButton > button p,
    div.stButton > button span,
    div.stButton > button div {
        color: #0f172a !important;
    }

    div[data-baseweb="tab-list"] {
        gap: 0.4rem;
    }

    button[data-baseweb="tab"] {
        border-radius: 8px;
        background: #1c2026;
        color: #d1d5db;
    }

    .hero-title {
        font-size: 1.9rem;
        line-height: 1.08;
        margin: 0 0 0.45rem 0;
        max-width: 700px;
    }

    div[data-testid="stInfo"] {
        background: #20252c;
        border: 1px solid #334155;
        color: #dbe2ea;
    }

    div[data-testid="stExpander"] {
        background: #20252c;
        border: 1px solid #323844;
        border-radius: 12px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #323844;
        border-radius: 12px;
        overflow: hidden;
    }

    .stTextArea textarea {
        background: #1b2026 !important;
        color: #e5e7eb !important;
        border: 1px solid #323844 !important;
    }

    .stMarkdown, .stCaption, label, p, li {
        color: #d1d5db;
    }

    div[data-testid="stFileUploader"] section {
        color: #d1d5db;
    }
</style>
"""


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    _render_header()

    if "rfp_doc" not in st.session_state:
        st.session_state.rfp_doc = None
    if "proposal_doc" not in st.session_state:
        st.session_state.proposal_doc = None

    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        rfp_file = _upload_panel(
            title="RFP or RFQ document",
            help_text="Upload the buyer document you want to review.",
            key="rfp_upload",
        )

    with right_col:
        proposal_file = _upload_panel(
            title="Proposal draft",
            help_text="Upload the response draft you want to compare against the RFx.",
            key="proposal_upload",
        )

    action_col, note_col = st.columns([0.32, 0.68], gap="large")

    with action_col:
        sample_clicked = st.button("Load sample files", use_container_width=True)
    with note_col:
        st.markdown(
            "<p class='caption-note'>"
            "The sample flow lets you test the app instantly before using your own files."
            "</p>",
            unsafe_allow_html=True,
        )

    if sample_clicked:
        try:
            sample_rfp, sample_proposal = load_sample_documents()
            st.session_state.rfp_doc = sample_rfp
            st.session_state.proposal_doc = sample_proposal
        except ValueError as exc:
            st.session_state.rfp_doc = None
            st.session_state.proposal_doc = None
            st.error(str(exc))

    if rfp_file:
        try:
            st.session_state.rfp_doc = load_document(rfp_file, rfp_file.name)
        except ValueError as exc:
            st.session_state.rfp_doc = None
            st.error(str(exc))

    if proposal_file:
        try:
            st.session_state.proposal_doc = load_document(proposal_file, proposal_file.name)
        except ValueError as exc:
            st.session_state.proposal_doc = None
            st.error(str(exc))

    rfp_doc = st.session_state.rfp_doc
    proposal_doc = st.session_state.proposal_doc

    if not rfp_doc and not proposal_doc:
        st.info(
            "Upload either file to preview it right away, or load the built-in sample set to test the full flow."
        )
        return

    _render_document_status(rfp_doc, proposal_doc)

    if rfp_doc and proposal_doc:
        _render_summary(rfp_doc, proposal_doc)
        _render_analysis(rfp_doc, proposal_doc)
        _render_previews(rfp_doc, proposal_doc)
    else:
        st.info("Add the second file when you're ready. For now, you can already inspect the uploaded document below.")
        if rfp_doc:
            _render_requirement_preview(rfp_doc)
        _render_single_document_preview(rfp_doc, proposal_doc)


def _render_header() -> None:
    st.markdown(
        """
        <section class="hero-card">
            <h1 class="hero-title">RFx Proposal Coverage Analyzer</h1>
            <p class="hero-copy">
                Upload a buyer document and a proposal draft to extract readable text, surface key
                requirements, and line them up for review.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _upload_panel(title: str, help_text: str, key: str):
    st.subheader(title)
    st.caption(help_text)
    uploaded = st.file_uploader(
        "Choose a file",
        type=["pdf", "docx", "txt"],
        label_visibility="collapsed",
        key=key,
    )
    return uploaded


def _render_summary(rfp_doc: Document, proposal_doc: Document) -> None:
    st.subheader("Document Snapshot")
    metric_cols = st.columns(6, gap="medium")
    metrics = [
        ("RFP words", f"{rfp_doc.word_count:,}"),
        ("Proposal words", f"{proposal_doc.word_count:,}"),
        ("RFP pages", _display_count(rfp_doc.page_count)),
        ("Proposal pages", _display_count(proposal_doc.page_count)),
        ("RFP type", rfp_doc.doc_type),
        ("Proposal type", proposal_doc.doc_type),
    ]

    for col, (label, value) in zip(metric_cols, metrics):
        with col:
            st.markdown(
                f"""
                <section class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </section>
                """,
                unsafe_allow_html=True,
            )


def _render_analysis(rfp_doc: Document, proposal_doc: Document) -> None:
    requirements = extract_requirements(rfp_doc)
    chunks = chunk_proposal(proposal_doc)
    match_results = score_requirements_against_proposal(requirements, chunks)
    summary = coverage_summary(match_results)

    st.subheader("Review Results")
    metric_cols = st.columns(4, gap="medium")
    metrics = [
        ("Coverage score", f"{summary['coverage_score']}%"),
        ("Covered", str(summary["covered"])),
        ("Partial", str(summary["partial"])),
        ("Missing", str(summary["missing"])),
    ]

    for col, (label, value) in zip(metric_cols, metrics):
        with col:
            st.markdown(
                f"""
                <section class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </section>
                """,
                unsafe_allow_html=True,
            )

    summary_tab, req_tab, chunk_tab = st.tabs(["Coverage", "Requirements", "Proposal Chunks"])
    with summary_tab:
        _render_priority_panel(match_results)
        _render_coverage_export(match_results)
        _render_coverage_table(match_results)
    with req_tab:
        _render_requirements_table(requirements)
    with chunk_tab:
        _render_chunks_view(chunks)


def _render_requirement_preview(rfp_doc: Document) -> None:
    requirements = extract_requirements(rfp_doc)
    if not requirements:
        return
    st.subheader("Detected Requirements")
    st.caption("These are the requirement statements currently detected from the buyer document.")
    _render_requirements_table(requirements[:12])


def _render_document_status(
    rfp_doc: Document | None, proposal_doc: Document | None
) -> None:
    st.subheader("Loaded Documents")
    left_col, right_col = st.columns(2, gap="large")

    with left_col:
        _render_document_card(rfp_doc, "RFP or RFQ")

    with right_col:
        _render_document_card(proposal_doc, "Proposal Draft")


def _render_previews(rfp_doc: Document, proposal_doc: Document) -> None:
    st.subheader("Preview Extracted Text")
    rfp_tab, proposal_tab = st.tabs(["Buyer Document", "Proposal Draft"])
    with rfp_tab:
        _render_document_preview(rfp_doc, "RFP")
    with proposal_tab:
        _render_document_preview(proposal_doc, "Proposal")


def _render_single_document_preview(
    rfp_doc: Document | None, proposal_doc: Document | None
) -> None:
    document = rfp_doc or proposal_doc
    label = "RFP" if rfp_doc else "Proposal"
    if document:
        st.subheader("Preview Extracted Text")
        _render_document_preview(document, label)


def _render_document_card(document: Document | None, label: str) -> None:
    if not document:
        st.markdown(
            f"""
            <section class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="caption-note">No file loaded yet.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <section class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="font-size:1.1rem;">{document.name}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.caption(_describe_document(document))
    st.markdown(_format_document_summary(document))


def _render_document_preview(document: Document, label: str) -> None:
    st.markdown(f"**{document.name}**")
    st.caption(
        f"{label} text extracted successfully. This preview starts from the most useful section we found."
    )
    preview = _best_preview_excerpt(document)
    st.text_area(
        f"{label} preview",
        value=preview,
        height=420,
        disabled=True,
        label_visibility="collapsed",
    )
    with st.expander("Show full extracted text"):
        st.text_area(
            f"{label} full text",
            value=document.text,
            height=520,
            disabled=True,
            label_visibility="collapsed",
        )


def _render_requirements_table(requirements) -> None:
    if not requirements:
        st.info("No clear requirement statements were detected yet.")
        return

    rows = [
        {
            "ID": req.requirement_id,
            "Category": req.category,
            "Priority": req.priority,
            "Page": req.source_page or "n/a",
            "Section": req.section_hint or "General",
            "Requirement": req.text,
        }
        for req in requirements
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_chunks_view(chunks) -> None:
    if not chunks:
        st.info("No proposal chunks were created yet.")
        return

    rows = [
        {
            "Chunk": chunk.chunk_id,
            "Page": chunk.source_page or "n/a",
            "Section": chunk.section_hint or "General",
            "Words": chunk.word_count,
            "Preview": textwrap.shorten(chunk.text, width=180, placeholder=" ..."),
        }
        for chunk in chunks
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_coverage_table(results) -> None:
    if not results:
        st.info("Coverage results will appear here once requirements and proposal chunks are available.")
        return

    status_filter = st.selectbox(
        "Filter by status",
        options=["All", "Missing", "Partial", "Covered"],
        index=0,
        key="coverage_status_filter",
    )

    if status_filter != "All":
        results = [result for result in results if result.status == status_filter]

    results = sorted(results, key=_coverage_sort_key)
    rows = [
        {
            "ID": result.requirement.requirement_id,
            "Status": result.status,
            "Score": result.score,
            "Priority": result.requirement.priority,
            "Category": result.requirement.category,
            "Requirement": result.requirement.text,
            "Evidence page": result.best_chunk.source_page if result.best_chunk else "n/a",
            "Evidence section": result.best_chunk.section_hint if result.best_chunk else "n/a",
            "Matched passage": result.evidence_text or "No matching proposal passage found.",
        }
        for result in results
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_priority_panel(results) -> None:
    urgent = [
        result
        for result in results
        if result.status in {"Missing", "Partial"} and result.requirement.priority == "High"
    ]
    st.caption("Start here: the highest-risk buyer requirements that still need attention.")
    if not urgent:
        st.success("No high-priority gaps were detected in the current review.")
        return

    for result in urgent[:5]:
        st.markdown(
            f"**{result.requirement.requirement_id} · {result.status} · {result.requirement.category}**  \n"
            f"{result.requirement.text}  \n"
            f"Matched passage: {result.evidence_text or 'No matching proposal passage found.'}"
        )


def _render_coverage_export(results) -> None:
    csv_buffer = StringIO()
    fieldnames = [
        "requirement_id",
        "status",
        "score",
        "priority",
        "category",
        "requirement_text",
        "evidence_page",
        "evidence_section",
        "evidence_text",
    ]
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    for result in results:
        writer.writerow(
            {
                "requirement_id": result.requirement.requirement_id,
                "status": result.status,
                "score": result.score,
                "priority": result.requirement.priority,
                "category": result.requirement.category,
                "requirement_text": result.requirement.text,
                "evidence_page": result.best_chunk.source_page if result.best_chunk else "",
                "evidence_section": result.best_chunk.section_hint if result.best_chunk else "",
                "evidence_text": result.evidence_text or "",
            }
        )

    st.download_button(
        "Download review as CSV",
        data=csv_buffer.getvalue(),
        file_name="coverage-review.csv",
        mime="text/csv",
        use_container_width=False,
    )


def _display_count(value: int | None) -> str:
    return str(value) if value is not None else "n/a"


def _coverage_sort_key(result) -> tuple[int, int, float]:
    status_rank = {"Missing": 0, "Partial": 1, "Covered": 2}
    priority_rank = {"High": 0, "Medium": 1, "Normal": 2}
    return (
        status_rank.get(result.status, 3),
        priority_rank.get(result.requirement.priority, 3),
        result.score,
    )


def _describe_document(document: Document) -> str:
    parts = [
        f"{document.doc_type} file",
        f"{document.word_count:,} words",
    ]
    if document.page_count is not None:
        parts.append(f"{document.page_count} pages")
    return " | ".join(parts)


def _format_document_summary(document: Document) -> str:
    title = _extract_title(document) or "No clear title detected."
    issuer = _extract_issuer(document)
    overview = _summarize_document(document)
    topics = _extract_key_topics(document)

    lines = [f"**Document summary**", f"**Title:** {title}", f"**Summary:** {overview}"]
    if issuer:
        lines.insert(2, f"**Issuer:** {issuer}")
    if topics:
        lines.append(f"**Key topics detected:** {', '.join(topics)}")

    return "\n\n".join(lines)


def _summarize_document(document: Document) -> str:
    blocks = _meaningful_blocks(document)
    if not blocks:
        return "The file was loaded, but the extracted text is still too noisy to summarize clearly."

    title = _extract_title(document)
    issuer = _extract_issuer(document)
    subject = _extract_subject_phrase(title or blocks[0])
    topics = _extract_key_topics(document)

    parts: list[str] = []
    if title and subject:
        parts.append(f"This document appears to be titled '{title}' and relates to {subject}.")
    elif title:
        parts.append(f"This document appears to be titled '{title}'.")
    else:
        parts.append("This appears to be an RFx document.")

    if issuer:
        parts.append(f"It appears to be issued by {issuer}.")

    if topics:
        parts.append(f"It covers topics such as {', '.join(topics)}.")

    return " ".join(parts)


def _best_preview_excerpt(document: Document) -> str:
    blocks = _meaningful_blocks(document)
    if not blocks:
        return document.text

    human_blocks = _human_first_blocks(document)
    preview_blocks = human_blocks[:3] if human_blocks else blocks[:3]
    preview_text = "\n\n".join(preview_blocks)
    return preview_text


def _meaningful_blocks(document: Document) -> list[str]:
    page_split = re.split(r"\[Page \d+\]\s*", document.text)
    blocks: list[str] = []

    for page in page_split:
        page = page.strip()
        if not page:
            continue

        for block in page.split("\n\n"):
            normalized = re.sub(r"\s+", " ", block).strip()
            if _is_meaningful_block(normalized):
                blocks.append(normalized)

    scored_blocks = sorted(blocks, key=_block_score, reverse=True)
    return scored_blocks


def _human_first_blocks(document: Document) -> list[str]:
    page_split = re.split(r"\[Page \d+\]\s*", document.text)
    candidates: list[tuple[int, str]] = []

    for page_index, page in enumerate(page_split, start=1):
        page = page.strip()
        if not page:
            continue

        for block in page.split("\n\n"):
            normalized = re.sub(r"\s+", " ", block).strip()
            if _is_meaningful_block(normalized):
                candidates.append((_human_block_score(normalized, page_index), normalized))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [block for score, block in candidates if score > 0]


def _is_meaningful_block(block: str) -> bool:
    lower = block.lower()

    if len(block) < 80:
        return False

    if any(
        phrase in lower
        for phrase in [
            "table of contents",
            "contents page no",
            "index of annexures",
            "list of annexures",
            "list of appendices",
        ]
    ):
        return False

    if "glossary" in lower and len(block) < 160:
        return False

    if lower.startswith(("appendix", "annexure", "annex ", "schedule ")) and len(block) < 240:
        return False

    digit_ratio = sum(char.isdigit() for char in block) / max(len(block), 1)
    if digit_ratio > 0.18:
        return False

    return True


def _block_score(block: str) -> int:
    lower = block.lower()
    score = 0

    for keyword in [
        "request for proposal",
        "request for quotation",
        "request for information",
        "rfq",
        "rfi",
        "procurement",
        "project",
        "scope",
        "scope of work",
        "services",
        "requirements",
        "eligibility",
        "submission",
        "deadline",
        "bid",
        "proposal",
        "supply",
        "contract",
    ]:
        if keyword in lower:
            score += 3

    if len(block) > 180:
        score += 2

    if lower.count(".") >= 2:
        score += 2

    if any(
        phrase in lower
        for phrase in [
            "table of contents",
            "appendix",
            "annexure",
            "schedule of rates",
            "bank guarantee",
            "form of bid",
        ]
    ):
        score -= 10

    return score


def _human_block_score(block: str, page_index: int) -> int:
    lower = block.lower()
    score = 0

    preferred_terms = [
        "executive summary",
        "overview",
        "introduction",
        "background",
        "brief description",
        "letter of invitation",
        "scope",
        "scope of work",
        "project summary",
        "service requirements",
        "eligibility criteria",
        "submission requirements",
        "project",
        "request for proposal",
        "request for quotation",
        "request for information",
        "procurement",
    ]
    dense_terms = [
        "1.1.5",
        "1.1.6",
        "clause",
        "pursuant",
        "thereof",
        "herein",
        "bid security",
        "bank guarantee",
    ]
    avoid_terms = [
        "appendix",
        "list of project-specific clauses",
        "list of bid-specific clauses",
        "footnotes",
        "table of contents",
        "glossary",
        "appendix",
        "annexure",
        "annex ",
        "schedule of rates",
        "form of agreement",
    ]

    for term in preferred_terms:
        if term in lower:
            score += 4

    for term in dense_terms:
        if term in lower:
            score -= 3

    for term in avoid_terms:
        if term in lower:
            score -= 12

    if page_index <= 8:
        score += 3
    elif page_index >= 20:
        score -= 4

    if lower.count(".") >= 2:
        score += 1

    digit_ratio = sum(char.isdigit() for char in block) / max(len(block), 1)
    if digit_ratio > 0.12:
        score -= 4

    if len(block) > 120 and len(block) < 1600:
        score += 2

    if "table of contents" in lower:
        score -= 12

    return score


def _extract_title(document: Document) -> str | None:
    candidate_lines: list[str] = []
    for line in document.text.splitlines()[:40]:
        cleaned = re.sub(r"\s+", " ", line).strip()
        lower = cleaned.lower()
        if not cleaned or len(cleaned) < 12:
            continue
        if "table of contents" in lower or lower == "for official use only":
            continue
        if cleaned.startswith("[Page"):
            continue
        if any(char.isdigit() for char in cleaned[:8]) and "request for" not in lower:
            continue
        if "www." in lower or "@" in lower:
            continue
        if any(
            token in lower
            for token in [
                "request for proposal",
                "request for quotation",
                "request for information",
                "rfp",
                "rfq",
                "rfi",
                "tender",
                "procurement",
            ]
        ):
            candidate_lines.append(cleaned)

    if candidate_lines:
        best = sorted(candidate_lines, key=lambda value: (("request for" not in value.lower()), len(value)))[0]
        return textwrap.shorten(best, width=120, placeholder=" ...")
    return None


def _extract_issuer(document: Document) -> str | None:
    for line in document.text.splitlines()[:40]:
        cleaned = re.sub(r"\s+", " ", line).strip()
        if len(cleaned) < 6:
            continue
        if cleaned.startswith("[Page"):
            continue
        lower = cleaned.lower()
        if any(token in lower for token in ["www.", "@", "fax", "phone"]):
            continue
        if len(cleaned) > 110:
            continue
        if any(
            token in lower
            for token in [
                "government",
                "ministry",
                "department",
                "authority",
                "university",
                "corporation",
                "utility",
                "company",
                "city of",
                "county",
                "cpex",
            ]
        ):
            return cleaned
    return None


def _extract_subject_phrase(text: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", text).strip(" .")
    lower = cleaned.lower()

    patterns = [
        r"request for proposal for (.+)",
        r"request for quotation for (.+)",
        r"request for information for (.+)",
        r"rfp for (.+)",
        r"rfq for (.+)",
        r"rfi for (.+)",
        r"tender for (.+)",
        r"procurement of (.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            subject = match.group(1).strip(" .")
            return subject

    return cleaned if len(cleaned) < 140 else None


def _extract_key_topics(document: Document) -> list[str]:
    text = document.text.lower()
    topic_map = [
        ("bidding process", "bidding process"),
        ("instructions to bidders", "instructions to bidders"),
        ("eligibility criteria", "eligibility criteria"),
        ("bid security", "bid security"),
        ("evaluation of bids", "bid evaluation"),
        ("scope of work", "scope of work"),
        ("technical requirements", "technical requirements"),
        ("commercial terms", "commercial terms"),
        ("pre-bid conference", "pre-bid conference"),
        ("contract", "contract terms"),
        ("submission of bids", "bid submission"),
        ("submission requirements", "submission requirements"),
        ("timeline", "timeline"),
        ("deadline", "deadlines"),
    ]

    found = [label for needle, label in topic_map if needle in text]
    return found[:5]


if __name__ == "__main__":
    main()
