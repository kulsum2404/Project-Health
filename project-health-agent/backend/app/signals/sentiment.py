"""
Stakeholder sentiment signal — Weight: 15%

Uses LLM to classify free-text status/comment entries as
positive / neutral / negative, then aggregates into a 0-100 score.
Data source: notes/comments columns.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd

from app.llm_client import get_llm_client
from app.models import SignalResult

logger = logging.getLogger(__name__)

SIGNAL_NAME = "sentiment"
DEFAULT_WEIGHT = 0.15

COLUMN_CANDIDATES = [
    "notes", "comments", "status_notes", "status_comment",
    "remarks", "update", "status_update", "narrative",
    "description", "observation", "feedback",
    "Status Comment", "Comments",
]

SENTIMENT_SCORES = {
    "positive": 100.0,
    "neutral": 60.0,
    "negative": 20.0,
}

CLASSIFICATION_SYSTEM_PROMPT = """You are a sentiment classifier for project management status updates.
For each text entry provided, classify its sentiment as exactly one of: "positive", "neutral", or "negative".

Classification guidelines:
- "positive": Progress on track, milestones achieved, good team morale, risks mitigated
- "neutral": Routine updates, status quo, minor issues being addressed, factual statements
- "negative": Delays, budget overruns, team concerns, unresolved blockers, stakeholder dissatisfaction

Respond with ONLY a JSON array of objects, each with "index" (int) and "sentiment" (string).
Do NOT include any text outside the JSON array."""


def _find_notes_columns(df: pd.DataFrame, mapping: dict[str, str]) -> list[str]:
    """Find all columns that likely contain free-text notes."""
    found: list[str] = []

    def is_usable(col_name: str) -> bool:
        if df.empty:
            return True
        fill_count = df[col_name].notna().sum()
        # Accept column if it has at least 1 non-null value for sentiment
        if fill_count == 0:
            logger.warning(f"Sentiment signal: mapped column '{col_name}' is 100% empty. Skipping and trying next synonym.")
            return False
        return True

    # Check mapping first (canonical key "notes")
    if "notes" in mapping:
        mapped = mapping["notes"]
        if mapped in df.columns and is_usable(mapped):
            found.append(mapped)

    # Check mapping backwards (if mapping maps alias -> canonical, which it does)
    for candidate in COLUMN_CANDIDATES:
        if candidate in mapping:
            mapped = mapping[candidate]
            if mapped in df.columns and is_usable(mapped) and mapped not in found:
                found.append(mapped)

    # Direct column matching
    for candidate in COLUMN_CANDIDATES:
        if candidate in df.columns and candidate not in found:
            if is_usable(candidate):
                found.append(candidate)
        else:
            # Case-insensitive match
            for col in df.columns:
                if candidate.lower() == str(col).lower() and col not in found:
                    if is_usable(str(col)):
                        found.append(str(col))

    return found


async def compute_sentiment_signal(
    df: pd.DataFrame,
    mapping: dict[str, str],
) -> SignalResult:
    """
    Compute the stakeholder sentiment signal using LLM classification.

    Collects all free-text entries, sends them to the LLM for classification,
    and aggregates the results into a 0-100 score.
    """
    if df.empty:
        logger.warning("Sentiment signal: empty DataFrame — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No data rows"},
            reason="No data rows found.",
        )

    notes_cols = _find_notes_columns(df, mapping)

    if not notes_cols:
        logger.warning("Sentiment signal: no notes/comments columns found — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No notes/comments columns found"},
            reason="No notes or comments columns found in data.",
        )

    # Collect all non-empty text entries
    entries: list[dict[str, Any]] = []
    for col in notes_cols:
        for idx, val in df[col].items():
            if pd.notna(val):
                text = str(val).strip()
                if len(text) > 5:  # skip very short entries
                    entries.append({
                        "index": len(entries),
                        "text": text[:500],  # truncate long entries
                        "source_column": col,
                    })

    if not entries:
        logger.info("Sentiment signal: no substantive text entries found")
        return SignalResult(
            name=SIGNAL_NAME,
            score=60.0,  # neutral default
            weight=DEFAULT_WEIGHT,
            available=True,
            details={"reason": "No substantive text entries", "entry_count": 0},
            reason="No substantive status notes or comments found; assuming neutral sentiment.",
        )

    # ── LLM Classification ─────────────────────────────────────────────
    try:
        llm = get_llm_client()

        # Build the prompt with entries
        entry_texts = [
            {"index": e["index"], "text": e["text"]}
            for e in entries[:50]  # limit to 50 entries for token efficiency
        ]

        user_prompt = (
            "Classify the sentiment of each project status update below.\n\n"
            f"Entries:\n{json.dumps(entry_texts, indent=2)}"
        )

        result = await llm.complete_json(
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        # Parse classifications
        classifications = result if isinstance(result, list) else result.get("classifications", [])

    except Exception as e:
        logger.error("Sentiment signal: LLM classification failed: %s", e)
        # Fall back to neutral
        return SignalResult(
            name=SIGNAL_NAME,
            score=60.0,
            weight=DEFAULT_WEIGHT,
            available=True,
            details={
                "reason": f"LLM classification failed: {e}",
                "entry_count": len(entries),
                "fallback": True,
            },
            reason="Sentiment analysis unavailable due to LLM error; defaulting to neutral.",
        )

    # ── Aggregate sentiment scores ─────────────────────────────────────
    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
    classified_count = 0

    for item in classifications:
        sentiment = str(item.get("sentiment", "neutral")).lower()
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1
            classified_count += 1

    if classified_count == 0:
        return SignalResult(
            name=SIGNAL_NAME,
            score=60.0,
            weight=DEFAULT_WEIGHT,
            available=True,
            details={"reason": "No valid classifications returned", "entry_count": len(entries)},
            reason="Sentiment classification returned no valid results; defaulting to neutral.",
        )

    # Weighted average of sentiment scores
    total_score = sum(
        SENTIMENT_SCORES[sent] * count
        for sent, count in sentiment_counts.items()
    )
    score = total_score / classified_count

    details: dict[str, Any] = {
        "entry_count": len(entries),
        "classified_count": classified_count,
        "sentiment_distribution": sentiment_counts,
        "columns_used": notes_cols,
    }

    # Build reason
    dominant = max(sentiment_counts, key=lambda k: sentiment_counts[k])
    reason = (
        f"Analyzed {classified_count} status entries: "
        f"{sentiment_counts['positive']} positive, "
        f"{sentiment_counts['neutral']} neutral, "
        f"{sentiment_counts['negative']} negative. "
        f"Overall sentiment is {dominant}."
    )

    logger.info(
        "Sentiment signal: score=%.1f, distribution=%s",
        score, sentiment_counts,
    )

    return SignalResult(
        name=SIGNAL_NAME,
        score=round(score, 1),
        weight=DEFAULT_WEIGHT,
        available=True,
        details=details,
        reason=reason,
    )
