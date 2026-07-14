"""Pure dynamic topic-block observations.

No business topic is predefined. Labels and block identifiers are inferred
from normalized terms found in the explicitly supplied content and metadata.

This module does not read or mutate short-term, cold, candidate, or Titan
stores.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
import uuid
from collections import Counter
from typing import Iterable, Sequence

from memory.adaptive.contracts import (
    TopicBlockInput,
    TopicBlockObservation,
    TopicBlockRoutingObservation,
    TopicTerm,
    utc_now_iso,
)


_TOKEN_PATTERN = re.compile(
    r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9_'-]+",
    re.UNICODE,
)

# These words are linguistic noise, not predefined domain blocks.
_STOP_WORDS = frozenset(
    {
        "a",
        "ai",
        "ainsi",
        "alors",
        "an",
        "and",
        "au",
        "aucun",
        "aux",
        "avec",
        "avoir",
        "be",
        "car",
        "ce",
        "ces",
        "comme",
        "dans",
        "de",
        "des",
        "do",
        "donc",
        "du",
        "elle",
        "en",
        "est",
        "et",
        "for",
        "from",
        "il",
        "in",
        "is",
        "je",
        "la",
        "le",
        "les",
        "leur",
        "mais",
        "me",
        "memory",
        "mes",
        "mon",
        "ne",
        "not",
        "nous",
        "of",
        "on",
        "or",
        "ou",
        "par",
        "pas",
        "pour",
        "que",
        "qui",
        "sa",
        "sans",
        "se",
        "ses",
        "son",
        "sur",
        "the",
        "to",
        "tu",
        "un",
        "une",
        "with",
        "you",
    }
)


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_topic_term(value: str) -> str:
    """Normalize one term without assigning it to a fixed domain."""

    normalized = unicodedata.normalize(
        "NFKD",
        value.strip().lower(),
    )

    ascii_value = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )

    cleaned = re.sub(
        r"[^a-z0-9_-]+",
        "",
        ascii_value,
    )

    return cleaned.strip("_-")


def extract_topic_terms(
    content: str,
    *,
    metadata_terms: Sequence[str] = (),
    maximum_terms: int = 12,
) -> tuple[TopicTerm, ...]:
    """Extract weighted topic terms from content and metadata.

    Metadata terms receive an additional count because they were explicitly
    supplied by the caller. No domain vocabulary is predefined.
    """

    if maximum_terms <= 0:
        raise ValueError(
            "maximum_terms must be strictly positive."
        )

    frequencies: Counter[str] = Counter()

    for raw_token in _TOKEN_PATTERN.findall(content):
        token = normalize_topic_term(raw_token)

        if (
            len(token) < 3
            or token in _STOP_WORDS
            or token.isdigit()
        ):
            continue

        frequencies[token] += 1

    for raw_term in metadata_terms:
        for raw_token in _TOKEN_PATTERN.findall(
            str(raw_term)
        ):
            token = normalize_topic_term(raw_token)

            if (
                len(token) < 2
                or token in _STOP_WORDS
                or token.isdigit()
            ):
                continue

            frequencies[token] += 2

    if not frequencies:
        return ()

    maximum_count = max(frequencies.values())

    ordered = sorted(
        frequencies.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )[:maximum_terms]

    return tuple(
        TopicTerm(
            term=term,
            count=count,
            weight=_clamp_unit(
                count / maximum_count
            ),
        )
        for term, count in ordered
    )


def select_topic_label(
    terms: Sequence[TopicTerm],
) -> str:
    """Select a deterministic label from observed terms."""

    if not terms:
        return "unclassified"

    return terms[0].term


def build_topic_block_id(
    label: str,
) -> str:
    """Create a deterministic block ID from a dynamic label."""

    normalized = normalize_topic_term(label)

    if not normalized:
        normalized = "unclassified"

    compact = normalized[:48]

    return f"block_{compact}"


def calculate_routing_confidence(
    terms: Sequence[TopicTerm],
) -> float:
    """Estimate how clearly one dominant topic emerged."""

    if not terms:
        return 0.0

    if len(terms) == 1:
        return 1.0

    first = terms[0].weight
    second = terms[1].weight

    dominance = max(0.0, first - second)

    coverage = min(
        1.0,
        math.log2(len(terms) + 1) / 4.0,
    )

    return _clamp_unit(
        0.70 * first
        + 0.20 * dominance
        + 0.10 * coverage
    )


def content_digest(content: str) -> str:
    """Return a non-reversible digest for an observed text."""

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def _routing_explanation(
    label: str,
    terms: Sequence[TopicTerm],
    confidence: float,
) -> tuple[str, ...]:
    term_summary = ", ".join(
        term.term
        for term in terms[:5]
    )

    if not term_summary:
        term_summary = "no significant terms"

    return (
        (
            f"Dynamic label '{label}' was inferred "
            "from the supplied content."
        ),
        (
            f"Strongest observed terms: {term_summary}."
        ),
        (
            f"Routing confidence is {confidence:.4f}; "
            "the routing remains observational only."
        ),
        (
            "No candidate, hot-site memory, cold record, "
            "capacity, expansion, or pruning action was changed."
        ),
    )


def observe_topic_block(
    source: TopicBlockInput,
    *,
    routing_id: str | None = None,
) -> TopicBlockObservation:
    """Infer one immutable, action-free dynamic block observation."""

    source.validate()

    observed_at = (
        source.observed_at
        or utc_now_iso()
    )

    terms = extract_topic_terms(
        source.content,
        metadata_terms=source.metadata_terms,
    )

    label = select_topic_label(terms)
    block_id = build_topic_block_id(label)

    confidence = calculate_routing_confidence(
        terms
    )

    usage_ratio = _clamp_unit(
        source.used_items / source.capacity
    )

    routing = TopicBlockRoutingObservation(
        routing_id=(
            routing_id
            or f"routing_{uuid.uuid4().hex}"
        ),
        block_id=block_id,
        label=label,
        confidence=confidence,
        matched_terms=tuple(
            term.term
            for term in terms
        ),
        content_digest=content_digest(
            source.content
        ),
        explanation=_routing_explanation(
            label,
            terms,
            confidence,
        ),
        observed_at=observed_at,
    )

    return TopicBlockObservation(
        block_id=block_id,
        label=label,
        terms=terms,
        capacity=source.capacity,
        used_items=source.used_items,
        usage_ratio=usage_ratio,
        importance=source.importance,
        observed_item_ids=(
            source.item_id,
        ),
        created_at=observed_at,
        updated_at=observed_at,
        routing=routing,
    )


def term_counts(
    terms: Iterable[TopicTerm],
) -> dict[str, int]:
    """Return raw counts from topic terms."""

    return {
        term.term: term.count
        for term in terms
    }
