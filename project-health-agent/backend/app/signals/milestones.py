"""
Milestone health signal — Weight: 20%

Computes: Schedule Performance Index (SPI) = Earned Value / Planned Value,
and % milestones hit on time.
Data source: milestone rows in the project plan.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd

from app.models import SignalResult

logger = logging.getLogger(__name__)

SIGNAL_NAME = "milestones"
DEFAULT_WEIGHT = 0.20

COLUMN_CANDIDATES = {
    "milestone_name": ["milestone_name", "milestone", "deliverable", "phase", "Phase/Milestone"],
    "planned_date": ["planned_date", "planned_end", "due_date", "target_date", "baseline_end", "End Date", "Baseline Finish", "Baseline Finish2"],
    "actual_date": ["actual_date", "actual_end", "completed_date", "finish_date"],
    "status": ["status", "milestone_status", "state", "Status"],
    "is_milestone": ["is_milestone", "milestone_flag", "type", "Phase/Milestone"],
    "earned_value": ["earned_value", "ev"],
    "planned_value": ["planned_value", "pv"],
}


def _find_column(df: pd.DataFrame, mapping: dict[str, str], candidates: list[str]) -> str | None:
    def is_usable(col_name: str) -> bool:
        # Consider a column usable if it has at least 3 non-null values or >10% fill rate
        if df.empty:
            return True
        fill_count = df[col_name].notna().sum()
        if fill_count == 0:
            logger.warning(f"Milestones signal: mapped column '{col_name}' is 100% empty. Skipping and trying next synonym.")
            return False
        return fill_count >= 1 or (fill_count / len(df)) > 0.051

    mapped_but_empty = None

    for candidate in candidates:
        if candidate in mapping:
            mapped = mapping[candidate]
            if mapped in df.columns:
                if is_usable(mapped):
                    return mapped
                if mapped_but_empty is None:
                    mapped_but_empty = mapped

    for candidate in candidates:
        if candidate in df.columns:
            if is_usable(candidate):
                return candidate

    if mapped_but_empty:
        return mapped_but_empty

    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    return None


def compute_milestone_signal(
    df: pd.DataFrame,
    mapping: dict[str, str],
    reference_date: datetime | None = None,
) -> SignalResult:
    """
    Compute the milestone health signal.

    Combines SPI (if EV/PV data available) with % milestones on time.
    Score 0-100 (100 = all milestones on time, SPI ≥ 1.0).
    """
    if reference_date is None:
        reference_date = datetime.utcnow()

    if df.empty:
        logger.warning("Milestone signal: empty DataFrame — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No data rows"},
            reason="No data rows found.",
        )

    # Try to isolate milestone rows (vs regular tasks)
    milestone_col = _find_column(df, mapping, COLUMN_CANDIDATES["is_milestone"])
    type_col = _find_column(df, mapping, COLUMN_CANDIDATES["milestone_name"])

    milestone_df = df
    if milestone_col and milestone_col in df.columns:
        is_ms = df[milestone_col].astype(str).str.lower().isin(
            ["yes", "true", "1", "y", "milestone"]
        )
        if is_ms.any():
            milestone_df = df[is_ms]
    elif type_col and type_col in df.columns:
        # Check for 'milestone' in a type/name column
        is_ms = df[type_col].astype(str).str.lower().str.contains("milestone", na=False)
        if is_ms.any():
            milestone_df = df[is_ms]

    planned_col = _find_column(milestone_df, mapping, COLUMN_CANDIDATES["planned_date"])
    actual_col = _find_column(milestone_df, mapping, COLUMN_CANDIDATES["actual_date"])
    status_col = _find_column(milestone_df, mapping, COLUMN_CANDIDATES["status"])
    ev_col = _find_column(milestone_df, mapping, COLUMN_CANDIDATES["earned_value"])
    pv_col = _find_column(milestone_df, mapping, COLUMN_CANDIDATES["planned_value"])

    if planned_col is None:
        logger.warning("Milestone signal: no planned date column — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No planned date column found for milestones"},
            reason="Milestone planned date column not found.",
        )

    # Parse dates
    planned_dates = pd.to_datetime(milestone_df[planned_col], errors="coerce")
    actual_dates = (
        pd.to_datetime(milestone_df[actual_col], errors="coerce")
        if actual_col
        else pd.Series([pd.NaT] * len(milestone_df), dtype="datetime64[ns]")
    )

    valid_milestones = planned_dates.notna()
    total_milestones = int(valid_milestones.sum())

    if total_milestones == 0:
        logger.warning("Milestone signal: no valid milestone dates — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No valid milestone dates"},
            reason="No valid milestone dates found.",
        )

    # Determine completion
    ref_ts = pd.Timestamp(reference_date)

    if status_col:
        completed_mask = milestone_df[status_col].astype(str).str.lower().isin(
            ["complete", "completed", "done", "closed", "finished"]
        )
    else:
        completed_mask = actual_dates.notna()

    # ── % milestones on time ───────────────────────────────────────────
    # On time = completed before or on planned date, or not yet due
    not_yet_due = valid_milestones & (planned_dates >= ref_ts) & ~completed_mask
    on_time_completed = (
        valid_milestones
        & completed_mask
        & actual_dates.notna()
        & (actual_dates <= planned_dates)
    )
    # Completed without actual date — assume on time if status says done
    completed_no_date = valid_milestones & completed_mask & actual_dates.isna()

    on_time_count = int(on_time_completed.sum()) + int(not_yet_due.sum()) + int(completed_no_date.sum())
    pct_on_time = (on_time_count / total_milestones) * 100.0

    # Late milestones
    late_mask = valid_milestones & (
        (completed_mask & actual_dates.notna() & (actual_dates > planned_dates))
        | (~completed_mask & (planned_dates < ref_ts))
    )
    late_count = int(late_mask.sum())

    # ── SPI Calculation ────────────────────────────────────────────────
    spi = 1.0
    has_spi = False

    if ev_col and pv_col:
        ev_values = pd.to_numeric(milestone_df[ev_col], errors="coerce")
        pv_values = pd.to_numeric(milestone_df[pv_col], errors="coerce")
        total_ev = float(ev_values.sum())
        total_pv = float(pv_values.sum())
        if total_pv > 0:
            spi = total_ev / total_pv
            has_spi = True

    # ── Score Calculation ──────────────────────────────────────────────
    # Blend SPI score and on-time percentage
    ontime_score = pct_on_time  # 0-100

    if has_spi:
        # SPI score: 1.0+ → 100, 0.5 → 0
        spi_score = max(0.0, min(100.0, (spi - 0.5) * 200.0))
        score = (ontime_score * 0.6) + (spi_score * 0.4)
    else:
        score = ontime_score

    score = max(0.0, min(100.0, score))

    details: dict[str, Any] = {
        "total_milestones": total_milestones,
        "on_time_count": on_time_count,
        "late_count": late_count,
        "pct_on_time": round(pct_on_time, 1),
        "spi": round(spi, 3) if has_spi else None,
        "has_spi_data": has_spi,
    }

    reason_parts = []
    reason_parts.append(f"{on_time_count} of {total_milestones} milestones on time ({pct_on_time:.0f}%).")
    if late_count > 0:
        reason_parts.append(f"{late_count} milestones are late.")
    if has_spi:
        reason_parts.append(f"SPI is {spi:.2f}.")

    logger.info("Milestone signal: score=%.1f, on_time=%d/%d", score, on_time_count, total_milestones)

    return SignalResult(
        name=SIGNAL_NAME,
        score=round(score, 1),
        weight=DEFAULT_WEIGHT,
        available=True,
        details=details,
        reason=" ".join(reason_parts),
    )
