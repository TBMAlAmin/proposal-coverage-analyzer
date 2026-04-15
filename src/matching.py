from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import re

from src.analysis import ProposalChunk, Requirement


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "will",
    "shall",
    "must",
    "should",
}

TOKEN_NORMALIZATION = {
    "administrators": "admin",
    "administrator": "admin",
    "operators": "operator",
    "permissions": "access",
    "controls": "control",
    "reports": "report",
    "reporting": "report",
    "exporting": "export",
    "exports": "export",
    "exported": "export",
    "training": "train",
    "onboarding": "train",
    "timeline": "schedule",
    "delivery": "schedule",
    "backups": "backup",
    "notifications": "notification",
    "alerts": "alert",
    "auditability": "audit",
    "recorded": "record",
    "recording": "record",
    "events": "event",
    "check-in": "checkin",
    "check-out": "checkout",
}


@dataclass
class MatchResult:
    requirement: Requirement
    status: str
    score: float
    confidence: str
    best_chunk: ProposalChunk | None
    evidence_text: str | None
    overlap_terms: list[str]


def score_requirements_against_proposal(
    requirements: list[Requirement], chunks: list[ProposalChunk]
) -> list[MatchResult]:
    if not requirements:
        return []

    chunk_profiles = [_chunk_profile(chunk) for chunk in chunks]
    results: list[MatchResult] = []

    for requirement in requirements:
        req_tokens = _tokenize(requirement.text)
        req_counter = Counter(req_tokens)

        best_score = 0.0
        best_chunk: ProposalChunk | None = None
        best_overlap: list[str] = []

        for chunk, chunk_counter in chunk_profiles:
            score, overlap = _combined_score(req_counter, chunk_counter)
            if score > best_score:
                best_score = score
                best_chunk = chunk
                best_overlap = overlap

        results.append(
            MatchResult(
                requirement=requirement,
                status=_status_from_score(best_score),
                score=round(best_score, 3),
                confidence=_confidence_label(best_score),
                best_chunk=best_chunk,
                evidence_text=_evidence_snippet(best_chunk.text) if best_chunk else None,
                overlap_terms=best_overlap[:8],
            )
        )

    return results


def coverage_summary(results: list[MatchResult]) -> dict[str, int | float]:
    total = len(results)
    covered = sum(result.status == "Covered" for result in results)
    partial = sum(result.status == "Partial" for result in results)
    missing = sum(result.status == "Missing" for result in results)
    score = ((covered * 1.0) + (partial * 0.5)) / total * 100 if total else 0.0
    return {
        "total": total,
        "covered": covered,
        "partial": partial,
        "missing": missing,
        "coverage_score": round(score, 1),
    }


def _chunk_profile(chunk: ProposalChunk) -> tuple[ProposalChunk, Counter[str]]:
    return chunk, Counter(_tokenize(chunk.text))


def _combined_score(
    requirement_counter: Counter[str], chunk_counter: Counter[str]
) -> tuple[float, list[str]]:
    if not requirement_counter or not chunk_counter:
        return 0.0, []

    req_terms = set(requirement_counter)
    chunk_terms = set(chunk_counter)
    overlap = sorted(req_terms & chunk_terms)
    if not overlap:
        return 0.0, []

    lexical_coverage = len(overlap) / len(req_terms)
    cosine = _cosine_similarity(requirement_counter, chunk_counter)

    score = (0.65 * lexical_coverage) + (0.35 * cosine)
    return score, overlap


def _cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    common = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _status_from_score(score: float) -> str:
    if score >= 0.58:
        return "Covered"
    if score >= 0.3:
        return "Partial"
    return "Missing"


def _confidence_label(score: float) -> str:
    if score >= 0.7:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def _evidence_snippet(text: str, max_words: int = 36) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " ..."


def _tokenize(text: str) -> list[str]:
    raw_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]+", text.lower())
    tokens: list[str] = []
    for token in raw_tokens:
        normalized = TOKEN_NORMALIZATION.get(token, token)
        normalized = _light_stem(normalized)
        if normalized not in STOPWORDS and len(normalized) > 2:
            tokens.append(normalized)
    return tokens


def _light_stem(token: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[: -len(suffix)]
    return token
