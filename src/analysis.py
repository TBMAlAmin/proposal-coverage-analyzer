from __future__ import annotations

from dataclasses import dataclass
import re

from src.loaders import Document


REQUIREMENT_VERBS = (
    "must",
    "shall",
    "should",
    "required to",
    "needs to",
    "will need to",
)

SECTION_CATEGORY_RULES = [
    ("submission", "Submission"),
    ("timeline", "Timeline"),
    ("schedule", "Timeline"),
    ("delivery", "Timeline"),
    ("technical", "Technical"),
    ("scope", "Technical"),
    ("service", "Technical"),
    ("compliance", "Compliance"),
    ("security", "Compliance"),
    ("eligibility", "Eligibility"),
    ("qualification", "Eligibility"),
    ("pricing", "Commercial"),
    ("commercial", "Commercial"),
    ("payment", "Commercial"),
    ("contract", "Contract"),
    ("legal", "Contract"),
]


@dataclass
class Requirement:
    requirement_id: str
    text: str
    category: str
    section_hint: str | None
    priority: str
    source_page: int | None


@dataclass
class ProposalChunk:
    chunk_id: str
    text: str
    section_hint: str | None
    source_page: int | None
    word_count: int


def extract_requirements(document: Document) -> list[Requirement]:
    page_blocks = _page_blocks(document.text)
    requirements: list[Requirement] = []
    seen_texts: set[str] = set()
    current_section: str | None = None

    for page_number, block in page_blocks:
        for paragraph in _split_paragraphs(block):
            cleaned = _normalize_text(paragraph)
            if not cleaned:
                continue

            inline_heading, cleaned = _extract_inline_heading(cleaned)
            if inline_heading:
                current_section = inline_heading

            if _looks_like_section_heading(cleaned):
                current_section = cleaned
                continue

            for sentence in _sentence_candidates(cleaned):
                requirement_text = _clean_requirement_sentence(sentence)
                if not _looks_like_requirement(requirement_text):
                    continue
                if requirement_text.lower() in seen_texts:
                    continue

                seen_texts.add(requirement_text.lower())
                requirements.append(
                    Requirement(
                        requirement_id=f"REQ-{len(requirements) + 1:03d}",
                        text=requirement_text,
                        category=_categorize_requirement(requirement_text, current_section),
                        section_hint=current_section,
                        priority=_priority_label(requirement_text),
                        source_page=page_number,
                    )
                )

    return requirements


def chunk_proposal(document: Document, target_words: int = 110) -> list[ProposalChunk]:
    page_blocks = _page_blocks(document.text)
    chunks: list[ProposalChunk] = []
    current_section: str | None = None
    buffer: list[str] = []
    buffer_page: int | None = None

    for page_number, block in page_blocks:
        for paragraph in _split_paragraphs(block):
            cleaned = _normalize_text(paragraph)
            if not cleaned:
                continue

            inline_heading, cleaned = _extract_inline_heading(cleaned)
            if inline_heading:
                current_section = inline_heading
            if not cleaned:
                continue

            if _looks_like_section_heading(cleaned):
                if buffer:
                    chunks.append(
                        _build_chunk(
                            chunk_id=len(chunks) + 1,
                            lines=buffer,
                            section_hint=current_section,
                            page_number=buffer_page,
                        )
                    )
                    buffer = []
                    buffer_page = None
                current_section = cleaned
                continue

            if buffer_page is None:
                buffer_page = page_number
            buffer.append(cleaned)

            if len(" ".join(buffer).split()) >= target_words:
                chunks.append(
                    _build_chunk(
                        chunk_id=len(chunks) + 1,
                        lines=buffer,
                        section_hint=current_section,
                        page_number=buffer_page,
                    )
                )
                buffer = []
                buffer_page = None

    if buffer:
        chunks.append(
            _build_chunk(
                chunk_id=len(chunks) + 1,
                lines=buffer,
                section_hint=current_section,
                page_number=buffer_page,
            )
        )

    return chunks


def _build_chunk(
    chunk_id: int, lines: list[str], section_hint: str | None, page_number: int | None
) -> ProposalChunk:
    text = " ".join(lines).strip()
    return ProposalChunk(
        chunk_id=f"CHUNK-{chunk_id:03d}",
        text=text,
        section_hint=section_hint,
        source_page=page_number,
        word_count=len(text.split()),
    )


def _page_blocks(text: str) -> list[tuple[int | None, str]]:
    matches = list(re.finditer(r"\[Page (\d+)\]", text))
    if not matches:
        return [(None, text)]

    blocks: list[tuple[int | None, str]] = []
    for index, match in enumerate(matches):
        page_number = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append((page_number, block))
    return blocks


def _split_paragraphs(text: str) -> list[str]:
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    parts: list[str] = []
    buffer: list[str] = []

    for line in raw_lines:
        if _looks_like_section_heading(line):
            if buffer:
                parts.append(" ".join(buffer).strip())
                buffer = []
            parts.append(line)
            continue

        buffer.append(line)
        if line.endswith((".", "?", "!", ":")):
            parts.append(" ".join(buffer).strip())
            buffer = []

    if buffer:
        parts.append(" ".join(buffer).strip())

    return [part for part in parts if part]


def _sentence_candidates(text: str) -> list[str]:
    parts = re.split(r"(?<=[.?!;])\s+(?=[A-Z0-9])", text)
    return [part.strip() for part in parts if part.strip()]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_inline_heading(text: str) -> tuple[str | None, str]:
    for suffix in (
        "Requirements",
        "Overview",
        "Summary",
        "Controls",
        "Reporting",
        "Management",
        "Submission",
        "Timeline",
        "Introduction",
    ):
        marker = f"{suffix} "
        if marker in text:
            head, tail = text.split(marker, 1)
            heading = f"{head.strip()} {suffix}".strip()
            tail_words = tail.strip().split()
            if 4 <= len(heading) <= 60 and len(tail_words) >= 3:
                return heading, tail.strip()
    return None, text


def _looks_like_section_heading(text: str) -> bool:
    if len(text) > 90:
        return False
    if any(verb in text.lower() for verb in REQUIREMENT_VERBS):
        return False
    return bool(
        re.fullmatch(r"([A-Z][A-Za-z/&,\- ]+|\d+(\.\d+)*[ ):\-]*[A-Za-z][A-Za-z/&,\- ]+)", text)
    )


def _looks_like_requirement(text: str) -> bool:
    lower = text.lower()
    if len(text) < 35:
        return False
    if any(verb in lower for verb in REQUIREMENT_VERBS):
        return True
    if lower.startswith(("include ", "provide ", "submit ", "describe ", "maintain ")):
        return True
    return False


def _clean_requirement_sentence(text: str) -> str:
    text = re.sub(r"^\d+(\.\d+)*\s*", "", text).strip()
    return text.rstrip(" ;")


def _categorize_requirement(text: str, section_hint: str | None) -> str:
    if section_hint:
        section_lower = section_hint.lower()
        for needle, label in SECTION_CATEGORY_RULES:
            if needle in section_lower:
                return label

    search_space = text.lower()
    for needle, label in SECTION_CATEGORY_RULES:
        if needle in search_space:
            return label
    return "General"


def _priority_label(text: str) -> str:
    lower = text.lower()
    if "must" in lower or "shall" in lower or "required to" in lower:
        return "High"
    if "should" in lower:
        return "Medium"
    return "Normal"
