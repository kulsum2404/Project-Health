"""
Deterministic RAG classifier — the core health-scoring engine.

Takes signal results from all 5 extractors, applies weight redistribution
for missing signals, computes a weighted score, and applies threshold rules
to determine Red/Amber/Green status.

The LLM never determines the RAG status. It only writes explanations
(see reasoning.py).
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.models import RagResult, RagStatus, SignalResult

logger = logging.getLogger(__name__)

# Default weights (must sum to 1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    "schedule": 0.30,
    "budget": 0.20,
    "milestones": 0.20,
    "blockers": 0.15,
    "sentiment": 0.15,
}

# Thresholds
GREEN_THRESHOLD = 80.0
AMBER_THRESHOLD = 60.0
CPI_SPI_RED_THRESHOLD = 0.8
CRITICAL_BLOCKER_AGE_THRESHOLD = 7  # days


def classify_rag(signals: list[SignalResult]) -> RagResult:
    """
    Compute the RAG status from signal results.

    1. Filter to available signals.
    2. Redistribute weights proportionally.
    3. Compute weighted score.
    4. Apply threshold rules with override conditions.
    5. Compute confidence.

    Args:
        signals: List of SignalResult from all 5 extractors.

    Returns:
        RagResult with status, score, confidence, and audit trail.
    """
    # Separate available vs skipped signals
    available: list[SignalResult] = []
    skipped: list[SignalResult] = []

    for signal in signals:
        if signal.available:
            available.append(signal)
        else:
            skipped.append(signal)

    signals_used = [s.name for s in available]
    signals_skipped = [s.name for s in skipped]

    logger.info(
        "RAG classifier: %d signals available, %d skipped. Used: %s, Skipped: %s",
        len(available), len(skipped), signals_used, signals_skipped,
    )

    # ── Handle edge case: no available signals ─────────────────────────
    if not available:
        logger.warning("RAG classifier: no signals available — defaulting to Amber")
        return RagResult(
            status=RagStatus.AMBER,
            weighted_score=50.0,
            confidence=0.0,
            signals=signals,
            signals_used=[],
            signals_skipped=signals_skipped,
            override_reasons=["No signal data available — defaulting to Amber"],
        )

    # ── Redistribute weights ───────────────────────────────────────────
    total_available_weight = sum(
        DEFAULT_WEIGHTS.get(s.name, 0.0) for s in available
    )

    if total_available_weight == 0:
        total_available_weight = 1.0  # safety

    redistributed_weights: dict[str, float] = {}
    for signal in available:
        original_weight = DEFAULT_WEIGHTS.get(signal.name, 0.0)
        redistributed_weights[signal.name] = original_weight / total_available_weight

    # ── Compute weighted score ─────────────────────────────────────────
    weighted_score = sum(
        signal.score * redistributed_weights[signal.name]
        for signal in available
    )
    weighted_score = round(max(0.0, min(100.0, weighted_score)), 1)

    # ── Confidence ─────────────────────────────────────────────────────
    confidence = len(available) / len(signals) if signals else 0.0
    confidence = round(confidence, 2)

    # ── Apply threshold rules ──────────────────────────────────────────
    override_reasons: list[str] = []

    # Extract specific signal details for override checks
    blocker_details = _get_signal_details("blockers", available)
    budget_details = _get_signal_details("budget", available)
    milestone_details = _get_signal_details("milestones", available)

    # Check for critical blocker override (force RED)
    has_critical_over_7d = False
    if blocker_details:
        has_critical_over_7d = blocker_details.get("has_critical_over_7d", False)

    # Check CPI/SPI thresholds
    cpi_below_threshold = False
    spi_below_threshold = False

    if budget_details:
        cpi = budget_details.get("cpi", 1.0)
        if cpi is not None and cpi < CPI_SPI_RED_THRESHOLD:
            cpi_below_threshold = True

    if milestone_details:
        spi = milestone_details.get("spi")
        if spi is not None and spi < CPI_SPI_RED_THRESHOLD:
            spi_below_threshold = True

    # Check for moderate blocker (Amber condition)
    has_moderate_unresolved = False
    if blocker_details:
        has_moderate_unresolved = blocker_details.get("has_moderate_unresolved", False)

    # ── Determine status ───────────────────────────────────────────────
    # RED conditions
    if weighted_score < AMBER_THRESHOLD:
        status = RagStatus.RED
        override_reasons.append(f"Weighted score ({weighted_score}) below {AMBER_THRESHOLD}")
    elif has_critical_over_7d:
        status = RagStatus.RED
        override_reasons.append("Critical blocker unresolved for more than 7 days")
    elif cpi_below_threshold:
        status = RagStatus.RED
        override_reasons.append(f"CPI ({budget_details.get('cpi', 'N/A')}) below {CPI_SPI_RED_THRESHOLD}")
    elif spi_below_threshold:
        status = RagStatus.RED
        override_reasons.append(f"SPI ({milestone_details.get('spi', 'N/A')}) below {CPI_SPI_RED_THRESHOLD}")
    # GREEN conditions
    elif weighted_score >= GREEN_THRESHOLD and not has_critical_over_7d:
        status = RagStatus.GREEN
    # AMBER: everything else
    else:
        status = RagStatus.AMBER
        if has_moderate_unresolved:
            override_reasons.append("Moderate or high severity blocker unresolved")
        if weighted_score < GREEN_THRESHOLD:
            override_reasons.append(
                f"Weighted score ({weighted_score}) between {AMBER_THRESHOLD} and {GREEN_THRESHOLD}"
            )

    logger.info(
        "RAG classifier: status=%s, score=%.1f, confidence=%.2f, overrides=%s",
        status.value, weighted_score, confidence, override_reasons,
    )

    return RagResult(
        status=status,
        weighted_score=weighted_score,
        confidence=confidence,
        signals=signals,
        signals_used=signals_used,
        signals_skipped=signals_skipped,
        override_reasons=override_reasons,
    )


def _get_signal_details(name: str, signals: list[SignalResult]) -> dict[str, Any]:
    """Extract the details dict for a named signal, or empty dict if not found."""
    for signal in signals:
        if signal.name == name:
            return signal.details
    return {}
