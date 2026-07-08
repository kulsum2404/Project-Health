"""Tests for the schedule signal extractor."""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.signals.schedule import compute_schedule_signal


class TestScheduleSignal:
    """Test suite for schedule slippage signal computation."""

    def test_all_on_schedule(self):
        """All tasks on schedule → score should be close to 100."""
        df = pd.DataFrame({
            "Task Name": ["Task A", "Task B", "Task C"],
            "Planned End": ["2025-12-01", "2025-12-15", "2025-12-30"],
            "Actual End": ["2025-11-28", "2025-12-14", "2025-12-29"],
            "Status": ["Complete", "Complete", "Complete"],
        })
        mapping = {
            "task_name": "Task Name",
            "planned_end": "Planned End",
            "actual_end": "Actual End",
            "status": "Status",
        }
        ref = datetime(2025, 11, 1)
        result = compute_schedule_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert result.score >= 90
        assert result.name == "schedule"

    def test_all_overdue(self):
        """All tasks overdue → score should be low."""
        df = pd.DataFrame({
            "Task Name": ["Task A", "Task B", "Task C"],
            "Planned End": ["2025-01-01", "2025-01-15", "2025-02-01"],
            "Status": ["In Progress", "In Progress", "Not Started"],
        })
        mapping = {
            "task_name": "Task Name",
            "planned_end": "Planned End",
            "status": "Status",
        }
        ref = datetime(2025, 6, 15)
        result = compute_schedule_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert result.score < 30
        assert result.details["overdue_tasks"] == 3

    def test_mixed_status(self):
        """Mix of on-time and late tasks → intermediate score."""
        df = pd.DataFrame({
            "Task Name": ["Task A", "Task B", "Task C", "Task D"],
            "Planned End": ["2025-03-01", "2025-06-01", "2025-09-01", "2025-12-01"],
            "Actual End": ["2025-02-28", None, None, None],
            "Status": ["Complete", "In Progress", "In Progress", "Not Started"],
        })
        mapping = {
            "task_name": "Task Name",
            "planned_end": "Planned End",
            "actual_end": "Actual End",
            "status": "Status",
        }
        ref = datetime(2025, 7, 1)
        result = compute_schedule_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert 20 < result.score < 90

    def test_missing_planned_end_column(self):
        """No planned end column → signal should be unavailable."""
        df = pd.DataFrame({
            "Task Name": ["Task A", "Task B"],
            "Status": ["In Progress", "Complete"],
        })
        result = compute_schedule_signal(df, {})

        assert result.available is False
        assert result.score == 0

    def test_empty_dataframe(self):
        """Empty DataFrame → signal should be unavailable."""
        df = pd.DataFrame(columns=["Task Name", "Planned End", "Status"])
        result = compute_schedule_signal(df, {})

        assert result.available is False

    def test_single_row(self):
        """Single task row should compute normally."""
        df = pd.DataFrame({
            "Task Name": ["Only Task"],
            "Planned End": ["2025-12-01"],
            "Status": ["In Progress"],
        })
        mapping = {"planned_end": "Planned End", "status": "Status"}
        ref = datetime(2025, 6, 1)
        result = compute_schedule_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert result.score == 100.0  # not yet due

    def test_critical_path_delay(self):
        """Critical path delay should apply penalty."""
        df = pd.DataFrame({
            "Task Name": ["Critical Task", "Normal Task"],
            "Planned End": ["2025-01-01", "2025-06-01"],
            "Status": ["In Progress", "In Progress"],
            "Is Critical": ["Yes", "No"],
        })
        mapping = {
            "planned_end": "Planned End",
            "status": "Status",
            "is_critical": "Is Critical",
        }
        ref = datetime(2025, 6, 15)
        result = compute_schedule_signal(df, mapping, reference_date=ref)

        assert result.available is True
        assert result.details["critical_path_delay_days"] > 0
        assert result.details["critical_tasks_overdue"] == 1

    def test_all_dates_nat(self):
        """All dates are NaT → signal should be unavailable."""
        df = pd.DataFrame({
            "Task Name": ["Task A", "Task B"],
            "Planned End": [None, None],
        })
        mapping = {"planned_end": "Planned End"}
        result = compute_schedule_signal(df, mapping)

        assert result.available is False
