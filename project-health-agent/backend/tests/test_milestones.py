"""Tests for the milestone signal extractor."""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.signals.milestones import compute_milestone_signal


class TestMilestoneSignal:
    """Test suite for milestone health signal computation."""

    def test_all_on_time(self):
        """All milestones on time → high score."""
        df = pd.DataFrame({
            "Task Name": ["MS 1", "MS 2", "MS 3"],
            "Planned End": ["2025-03-01", "2025-06-01", "2025-09-01"],
            "Actual End": ["2025-02-28", "2025-05-30", "2025-08-31"],
            "Status": ["Complete", "Complete", "Complete"],
            "Is Milestone": ["Yes", "Yes", "Yes"],
        })
        mapping = {
            "planned_date": "Planned End",
            "actual_date": "Actual End",
            "status": "Status",
            "is_milestone": "Is Milestone",
        }
        ref = datetime(2025, 10, 1)
        result = compute_milestone_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert result.score >= 90
        assert result.details["pct_on_time"] == 100.0

    def test_all_late(self):
        """All milestones late → low score."""
        df = pd.DataFrame({
            "Task Name": ["MS 1", "MS 2", "MS 3"],
            "Planned End": ["2025-01-01", "2025-02-01", "2025-03-01"],
            "Actual End": ["2025-02-01", "2025-03-15", "2025-05-01"],
            "Status": ["Complete", "Complete", "Complete"],
            "Is Milestone": ["Yes", "Yes", "Yes"],
        })
        mapping = {
            "planned_date": "Planned End",
            "actual_date": "Actual End",
            "status": "Status",
            "is_milestone": "Is Milestone",
        }
        ref = datetime(2025, 6, 1)
        result = compute_milestone_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert result.score < 30
        assert result.details["late_count"] == 3

    def test_mixed_milestones(self):
        """Mix of on-time and late → intermediate score."""
        df = pd.DataFrame({
            "Task Name": ["MS 1", "MS 2", "MS 3", "MS 4"],
            "Planned End": ["2025-03-01", "2025-04-01", "2025-05-01", "2025-12-01"],
            "Actual End": ["2025-02-28", "2025-04-15", None, None],
            "Status": ["Complete", "Complete", "In Progress", "Not Started"],
            "Is Milestone": ["Yes", "Yes", "Yes", "Yes"],
        })
        mapping = {
            "planned_date": "Planned End",
            "actual_date": "Actual End",
            "status": "Status",
            "is_milestone": "Is Milestone",
        }
        ref = datetime(2025, 6, 1)
        result = compute_milestone_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert 30 < result.score < 90

    def test_empty_dataframe(self):
        """Empty DataFrame → signal unavailable."""
        df = pd.DataFrame(columns=["Task Name", "Planned End"])
        result = compute_milestone_signal(df, {})

        assert result.available is False

    def test_no_planned_date_column(self):
        """No planned date column → signal unavailable."""
        df = pd.DataFrame({
            "Task Name": ["MS 1"],
            "Status": ["In Progress"],
        })
        result = compute_milestone_signal(df, {})

        assert result.available is False

    def test_single_milestone(self):
        """Single milestone should compute normally."""
        df = pd.DataFrame({
            "Task Name": ["Key Milestone"],
            "Planned End": ["2025-12-01"],
            "Actual End": ["2025-11-30"],
            "Status": ["Complete"],
            "Is Milestone": ["Yes"],
        })
        mapping = {
            "planned_date": "Planned End",
            "actual_date": "Actual End",
            "status": "Status",
            "is_milestone": "Is Milestone",
        }
        ref = datetime(2025, 12, 15)
        result = compute_milestone_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert result.score >= 90

    def test_with_spi_data(self):
        """Milestones with EV/PV data should include SPI in scoring."""
        df = pd.DataFrame({
            "Task Name": ["MS 1", "MS 2"],
            "Planned End": ["2025-03-01", "2025-06-01"],
            "Actual End": ["2025-02-28", "2025-05-30"],
            "Status": ["Complete", "Complete"],
            "Is Milestone": ["Yes", "Yes"],
            "Earned Value": [50000, 30000],
            "Planned Value": [50000, 40000],
        })
        mapping = {
            "planned_date": "Planned End",
            "actual_date": "Actual End",
            "status": "Status",
            "is_milestone": "Is Milestone",
            "earned_value": "Earned Value",
            "planned_value": "Planned Value",
        }
        ref = datetime(2025, 7, 1)
        result = compute_milestone_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert result.details["has_spi_data"] is True
        assert result.details["spi"] is not None
