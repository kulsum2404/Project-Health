"""
Schedule slippage signal — Weight: 30%

Computes: % of tasks past due date + magnitude of critical-path delay in days.
Data source: task start/end/planned/actual dates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.models import SignalResult

logger = logging.getLogger(__name__)

SIGNAL_NAME = "schedule"
DEFAULT_WEIGHT = 0.30

# Column name groups to search for in the mapped schema
REQUIRED_COLUMNS = {
    "task_name": ["task_name", "task", "activity", "work_item", "Task Name"],
    "planned_end": ["planned_end", "planned_finish", "baseline_end", "due_date", "end_date", "End Date", "Baseline Finish", "Baseline Finish2", "Finish"],
    "actual_end": ["actual_end", "actual_finish", "completed_date", "finish_date"],
    "planned_start": ["planned_start", "baseline_start", "start_date", "Start Date", "Start", "Baseline Start", "Baseline Start2"],
    "actual_start": ["actual_start"],
    "is_critical": ["is_critical", "critical_path", "critical", "Critical ?"],
    "status": ["status", "task_status", "Status"],
}


def _find_column(df: pd.DataFrame, mapping: dict[str, str], candidates: list[str]) -> str | None:
    """Find the first matching column from mapping or DataFrame columns."""
    
    def is_usable(col_name: str) -> bool:
        # Consider a column usable if it has at least 3 non-null values or >10% fill rate
        if df.empty:
            return True
        fill_count = df[col_name].notna().sum()
        return fill_count >= 3 or (fill_count / len(df)) > 0.1

    mapped_but_empty = None

    # Check explicit mapping first
    for candidate in candidates:
        if candidate in mapping:
            mapped = mapping[candidate]
            if mapped in df.columns:
                if is_usable(mapped):
                    return mapped
                if mapped_but_empty is None:
                    mapped_but_empty = mapped

    # Fall back to direct column name matching if mapping was empty/bad
    for candidate in candidates:
        if candidate in df.columns:
            if is_usable(candidate):
                return candidate

    # Last resort: return the mapped column even if empty, or the first candidate found
    if mapped_but_empty:
        return mapped_but_empty

    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    return None


def _parse_date_column(series: pd.Series) -> pd.Series:
    """Safely parse a column to datetime, coercing errors to NaT."""
    return pd.to_datetime(series, errors="coerce")


def compute_schedule_signal(
    df: pd.DataFrame,
    mapping: dict[str, str],
    reference_date: datetime | None = None,
) -> SignalResult:
    """
    Compute the schedule slippage signal.

    Args:
        df: DataFrame of task rows from the project plan.
        mapping: Column name mapping from schema_mapper.
        reference_date: The "today" date to compare against (defaults to now).

    Returns:
        SignalResult with score 0-100 (100 = perfectly on schedule).
    """
    if reference_date is None:
        reference_date = datetime.utcnow()

    # Locate required columns
    planned_end_col = _find_column(df, mapping, REQUIRED_COLUMNS["planned_end"])
    actual_end_col = _find_column(df, mapping, REQUIRED_COLUMNS["actual_end"])
    status_col = _find_column(df, mapping, REQUIRED_COLUMNS["status"])
    critical_col = _find_column(df, mapping, REQUIRED_COLUMNS["is_critical"])

    if planned_end_col is None:
        logger.warning("Schedule signal: no planned end date column found — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No planned end date column found"},
            reason="Planned end date column not found in data.",
        )

    if df.empty:
        logger.warning("Schedule signal: empty DataFrame — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No task rows in data"},
            reason="No task rows found in the data.",
        )

    # Parse dates
    planned_ends = _parse_date_column(df[planned_end_col])
    actual_ends = _parse_date_column(df[actual_end_col]) if actual_end_col else pd.Series(
        [pd.NaT] * len(df), dtype="datetime64[ns]"
    )

    # Determine task completion status
    if status_col:
        completed_mask = df[status_col].astype(str).str.lower().isin(
            ["complete", "completed", "done", "closed", "finished"]
        )
    else:
        completed_mask = actual_ends.notna()

    # ── Metric 1: % of tasks past due ──────────────────────────────────
    valid_planned = planned_ends.notna()
    total_with_dates = valid_planned.sum()

    if total_with_dates == 0:
        logger.warning("Schedule signal: no valid planned end dates — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No valid planned end dates"},
            reason="No valid planned end dates in the data.",
        )

    # A task is overdue if: planned end is in the past AND (not completed OR completed late)
    ref_ts = pd.Timestamp(reference_date)
    overdue_mask = valid_planned & (planned_ends < ref_ts) & ~completed_mask
    # Also count completed-but-late tasks
    late_completed = valid_planned & completed_mask & actual_ends.notna() & (actual_ends > planned_ends)

    overdue_count = int(overdue_mask.sum())
    late_count = int(late_completed.sum())
    total_overdue = overdue_count + late_count
    pct_overdue = (total_overdue / total_with_dates) * 100

    # ── Metric 2: Critical-path delay magnitude ───────────────────────
    critical_delay_days = 0.0
    critical_tasks_count = 0

    if critical_col and critical_col in df.columns:
        is_critical = df[critical_col].astype(str).str.lower().isin(
            ["yes", "true", "1", "y", "critical"]
        )
        critical_overdue = is_critical & overdue_mask
        critical_tasks_count = int(critical_overdue.sum())

        if critical_tasks_count > 0:
            critical_delays = (ref_ts - planned_ends[critical_overdue]).dt.days
            critical_delay_days = float(critical_delays.max())
    else:
        # If no critical path column, estimate from all overdue tasks
        if overdue_count > 0:
            delays = (ref_ts - planned_ends[overdue_mask]).dt.days
            critical_delay_days = float(delays.max()) if len(delays) > 0 else 0.0

    # ── Score calculation ──────────────────────────────────────────────
    # Base score from % on schedule (inverted: 0% overdue = 100 score)
    base_score = max(0.0, 100.0 - pct_overdue)

    # Penalty for critical path delay (up to -30 points for >30 days delay)
    delay_penalty = min(30.0, critical_delay_days)

    score = max(0.0, min(100.0, base_score - delay_penalty))

    details: dict[str, Any] = {
        "total_tasks": int(total_with_dates),
        "overdue_tasks": overdue_count,
        "late_completed_tasks": late_count,
        "pct_overdue": round(pct_overdue, 1),
        "critical_path_delay_days": round(critical_delay_days, 1),
        "critical_tasks_overdue": critical_tasks_count,
        "base_score": round(base_score, 1),
        "delay_penalty": round(delay_penalty, 1),
    }

    reason_parts = []
    if pct_overdue > 0:
        reason_parts.append(
            f"{total_overdue} of {int(total_with_dates)} tasks ({pct_overdue:.0f}%) are overdue or completed late."
        )
    else:
        reason_parts.append("All tasks are on schedule.")
    if critical_delay_days > 0:
        reason_parts.append(
            f"Critical path delay of {critical_delay_days:.0f} days detected."
        )

    logger.info("Schedule signal: score=%.1f, overdue=%d/%d", score, total_overdue, total_with_dates)

    return SignalResult(
        name=SIGNAL_NAME,
        score=round(score, 1),
        weight=DEFAULT_WEIGHT,
        available=True,
        details=details,
        reason=" ".join(reason_parts),
    )
