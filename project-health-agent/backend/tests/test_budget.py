"""Tests for the budget signal extractor."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.signals.budget import compute_budget_signal


class TestBudgetSignal:
    """Test suite for budget burn signal computation."""

    def test_under_budget(self):
        """CPI > 1.0 → high score (under budget)."""
        df = pd.DataFrame({
            "Planned Budget": [10000, 20000, 15000],
            "Actual Cost": [8000, 18000, 12000],
            "% Complete": [100, 100, 100],
        })
        mapping = {
            "planned_budget": "Planned Budget",
            "actual_cost": "Actual Cost",
            "pct_complete": "% Complete",
        }
        result = compute_budget_signal(df, mapping)

        assert result.available is True
        assert result.score >= 80
        assert result.details["cpi"] > 1.0

    def test_over_budget(self):
        """CPI < 1.0 → lower score."""
        df = pd.DataFrame({
            "Planned Budget": [10000, 20000],
            "Actual Cost": [15000, 30000],
            "% Complete": [80, 70],
        })
        mapping = {
            "planned_budget": "Planned Budget",
            "actual_cost": "Actual Cost",
            "pct_complete": "% Complete",
        }
        result = compute_budget_signal(df, mapping)

        assert result.available is True
        assert result.score < 60
        assert result.details["cpi"] < 1.0

    def test_exactly_on_budget(self):
        """CPI = 1.0 → score should be 100."""
        df = pd.DataFrame({
            "Planned Budget": [10000],
            "Actual Cost": [10000],
            "% Complete": [100],
        })
        mapping = {
            "planned_budget": "Planned Budget",
            "actual_cost": "Actual Cost",
            "pct_complete": "% Complete",
        }
        result = compute_budget_signal(df, mapping)

        assert result.available is True
        assert result.score == 100.0

    def test_no_budget_columns(self):
        """Missing budget/cost columns → signal unavailable."""
        df = pd.DataFrame({
            "Task Name": ["Task A"],
            "Status": ["In Progress"],
        })
        result = compute_budget_signal(df, {})

        assert result.available is False

    def test_empty_dataframe(self):
        """Empty DataFrame → signal unavailable."""
        df = pd.DataFrame(columns=["Planned Budget", "Actual Cost"])
        result = compute_budget_signal(df, {})

        assert result.available is False

    def test_zero_actual_cost(self):
        """Zero actual cost (project not started) → CPI should be 1.0."""
        df = pd.DataFrame({
            "Planned Budget": [50000],
            "Actual Cost": [0],
            "% Complete": [0],
        })
        mapping = {
            "planned_budget": "Planned Budget",
            "actual_cost": "Actual Cost",
            "pct_complete": "% Complete",
        }
        result = compute_budget_signal(df, mapping)

        assert result.available is True
        assert result.details["cpi"] == 1.0

    def test_percentage_as_decimal(self):
        """Handle % complete expressed as 0-1 instead of 0-100."""
        df = pd.DataFrame({
            "Planned Budget": [10000],
            "Actual Cost": [5000],
            "% Complete": [0.50],
        })
        mapping = {
            "planned_budget": "Planned Budget",
            "actual_cost": "Actual Cost",
            "pct_complete": "% Complete",
        }
        result = compute_budget_signal(df, mapping)

        assert result.available is True
        # EV = 10000 * 0.5 = 5000; CPI = 5000/5000 = 1.0
        assert result.details["cpi"] == 1.0

    def test_burn_rate(self):
        """Verify burn rate calculation."""
        df = pd.DataFrame({
            "Planned Budget": [100000],
            "Actual Cost": [75000],
            "% Complete": [60],
        })
        mapping = {
            "planned_budget": "Planned Budget",
            "actual_cost": "Actual Cost",
            "pct_complete": "% Complete",
        }
        result = compute_budget_signal(df, mapping)

        assert result.available is True
        assert result.details["burn_rate_pct"] == 75.0
