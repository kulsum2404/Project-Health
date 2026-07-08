"""Tests for the RAG classifier."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.models import RagStatus, SignalResult
from app.rag.classifier import classify_rag


def _make_signal(
    name: str, score: float, weight: float, available: bool = True, details: dict | None = None
) -> SignalResult:
    return SignalResult(
        name=name,
        score=score,
        weight=weight,
        available=available,
        details=details or {},
        reason=f"{name} test signal",
    )


class TestRagClassifier:
    """Test suite for the deterministic RAG classifier."""

    def test_all_green(self):
        """All signals healthy → GREEN."""
        signals = [
            _make_signal("schedule", 90, 0.30),
            _make_signal("budget", 95, 0.20),
            _make_signal("milestones", 85, 0.20),
            _make_signal("blockers", 100, 0.15),
            _make_signal("sentiment", 80, 0.15),
        ]
        result = classify_rag(signals)

        assert result.status == RagStatus.GREEN
        assert result.weighted_score >= 80
        assert result.confidence == 1.0

    def test_all_red(self):
        """All signals critical → RED."""
        signals = [
            _make_signal("schedule", 20, 0.30),
            _make_signal("budget", 15, 0.20),
            _make_signal("milestones", 30, 0.20),
            _make_signal("blockers", 10, 0.15),
            _make_signal("sentiment", 25, 0.15),
        ]
        result = classify_rag(signals)

        assert result.status == RagStatus.RED
        assert result.weighted_score < 60

    def test_amber_range(self):
        """Moderate scores → AMBER."""
        signals = [
            _make_signal("schedule", 70, 0.30),
            _make_signal("budget", 75, 0.20),
            _make_signal("milestones", 65, 0.20),
            _make_signal("blockers", 80, 0.15),
            _make_signal("sentiment", 60, 0.15),
        ]
        result = classify_rag(signals)

        assert result.status == RagStatus.AMBER

    def test_critical_blocker_override(self):
        """Critical blocker > 7 days forces RED regardless of score."""
        signals = [
            _make_signal("schedule", 90, 0.30),
            _make_signal("budget", 95, 0.20),
            _make_signal("milestones", 85, 0.20),
            _make_signal(
                "blockers", 50, 0.15,
                details={"has_critical_over_7d": True, "has_moderate_unresolved": False},
            ),
            _make_signal("sentiment", 80, 0.15),
        ]
        result = classify_rag(signals)

        assert result.status == RagStatus.RED
        assert any("critical blocker" in r.lower() for r in result.override_reasons)

    def test_cpi_below_threshold(self):
        """CPI < 0.8 forces RED."""
        signals = [
            _make_signal("schedule", 85, 0.30),
            _make_signal(
                "budget", 55, 0.20,
                details={"cpi": 0.65},
            ),
            _make_signal("milestones", 80, 0.20),
            _make_signal("blockers", 90, 0.15),
            _make_signal("sentiment", 85, 0.15),
        ]
        result = classify_rag(signals)

        assert result.status == RagStatus.RED
        assert any("CPI" in r for r in result.override_reasons)

    def test_spi_below_threshold(self):
        """SPI < 0.8 forces RED."""
        signals = [
            _make_signal("schedule", 85, 0.30),
            _make_signal("budget", 90, 0.20),
            _make_signal(
                "milestones", 60, 0.20,
                details={"spi": 0.7},
            ),
            _make_signal("blockers", 90, 0.15),
            _make_signal("sentiment", 85, 0.15),
        ]
        result = classify_rag(signals)

        assert result.status == RagStatus.RED
        assert any("SPI" in r for r in result.override_reasons)

    def test_weight_redistribution_one_missing(self):
        """One signal missing → weights redistributed proportionally."""
        signals = [
            _make_signal("schedule", 90, 0.30),
            _make_signal("budget", 0, 0.20, available=False),
            _make_signal("milestones", 85, 0.20),
            _make_signal("blockers", 100, 0.15),
            _make_signal("sentiment", 80, 0.15),
        ]
        result = classify_rag(signals)

        assert result.confidence == 0.8  # 4/5
        assert "budget" in result.signals_skipped
        assert "schedule" in result.signals_used

    def test_weight_redistribution_three_missing(self):
        """Three signals missing → only two contribute, low confidence."""
        signals = [
            _make_signal("schedule", 90, 0.30),
            _make_signal("budget", 0, 0.20, available=False),
            _make_signal("milestones", 0, 0.20, available=False),
            _make_signal("blockers", 0, 0.15, available=False),
            _make_signal("sentiment", 80, 0.15),
        ]
        result = classify_rag(signals)

        assert result.confidence == 0.4  # 2/5
        assert len(result.signals_skipped) == 3
        assert len(result.signals_used) == 2
        # Score should be weighted average of only available signals
        # schedule weight = 0.30/(0.30+0.15) = 0.667, sentiment = 0.333
        expected = 90 * (0.30 / 0.45) + 80 * (0.15 / 0.45)
        assert abs(result.weighted_score - expected) < 1.0

    def test_no_signals_available(self):
        """All signals unavailable → defaults to AMBER with 0 confidence."""
        signals = [
            _make_signal("schedule", 0, 0.30, available=False),
            _make_signal("budget", 0, 0.20, available=False),
            _make_signal("milestones", 0, 0.20, available=False),
            _make_signal("blockers", 0, 0.15, available=False),
            _make_signal("sentiment", 0, 0.15, available=False),
        ]
        result = classify_rag(signals)

        assert result.status == RagStatus.AMBER
        assert result.confidence == 0.0

    def test_threshold_boundary_green(self):
        """Score exactly at 80 with no blockers → GREEN."""
        signals = [
            _make_signal("schedule", 80, 0.30),
            _make_signal("budget", 80, 0.20),
            _make_signal("milestones", 80, 0.20),
            _make_signal("blockers", 80, 0.15, details={"has_critical_over_7d": False}),
            _make_signal("sentiment", 80, 0.15),
        ]
        result = classify_rag(signals)

        assert result.status == RagStatus.GREEN
        assert result.weighted_score == 80.0

    def test_threshold_boundary_amber(self):
        """Score just below 80 → AMBER."""
        signals = [
            _make_signal("schedule", 79, 0.30),
            _make_signal("budget", 79, 0.20),
            _make_signal("milestones", 79, 0.20),
            _make_signal("blockers", 79, 0.15, details={"has_critical_over_7d": False}),
            _make_signal("sentiment", 79, 0.15),
        ]
        result = classify_rag(signals)

        assert result.status == RagStatus.AMBER
