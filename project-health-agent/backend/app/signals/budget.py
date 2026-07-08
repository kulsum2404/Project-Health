"""
Budget burn signal — Weight: 20%

Computes: Cost Performance Index (CPI) = Earned Value / Actual Cost,
plus burn rate analysis.
Data source: budget/spend columns.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.models import SignalResult

logger = logging.getLogger(__name__)

SIGNAL_NAME = "budget"
DEFAULT_WEIGHT = 0.20

COLUMN_CANDIDATES = {
    "planned_budget": ["planned_budget", "budget", "baseline_cost", "planned_cost", "estimated_cost"],
    "actual_cost": ["actual_cost", "actual_spend", "spend", "cost_to_date", "incurred_cost"],
    "earned_value": ["earned_value", "ev", "value_earned"],
    "planned_value": ["planned_value", "pv", "budgeted_cost_of_work_scheduled", "bcws"],
    "pct_complete": ["pct_complete", "percent_complete", "%_complete", "completion", "progress", "% Complete"],
}


def _find_column(df: pd.DataFrame, mapping: dict[str, str], candidates: list[str]) -> str | None:
    """Find the first matching column from mapping or DataFrame columns."""
    for candidate in candidates:
        if candidate in mapping:
            mapped = mapping[candidate]
            if mapped in df.columns:
                return mapped
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _safe_numeric(series: pd.Series) -> pd.Series:
    """Convert a series to numeric, coercing errors to NaN."""
    return pd.to_numeric(series, errors="coerce")


def compute_budget_signal(
    df: pd.DataFrame,
    mapping: dict[str, str],
) -> SignalResult:
    """
    Compute the budget burn signal.

    CPI = Earned Value / Actual Cost
    - CPI > 1.0 → under budget (good)
    - CPI = 1.0 → on budget
    - CPI < 1.0 → over budget (bad)

    Score is mapped: CPI 1.0+ → 100, CPI 0.5 → 0, linear between.
    """
    budget_col = _find_column(df, mapping, COLUMN_CANDIDATES["planned_budget"])
    actual_col = _find_column(df, mapping, COLUMN_CANDIDATES["actual_cost"])
    ev_col = _find_column(df, mapping, COLUMN_CANDIDATES["earned_value"])
    pv_col = _find_column(df, mapping, COLUMN_CANDIDATES["planned_value"])
    pct_col = _find_column(df, mapping, COLUMN_CANDIDATES["pct_complete"])

    if df.empty:
        logger.warning("Budget signal: empty DataFrame — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No data rows"},
            reason="No data rows found.",
        )

    # We need at minimum budget and actual cost
    if budget_col is None and actual_col is None:
        logger.warning("Budget signal: no budget or actual cost columns — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No budget or actual cost columns found"},
            reason="Budget/cost columns not found in data.",
        )

    # ── Compute totals ─────────────────────────────────────────────────
    total_budget = 0.0
    total_actual = 0.0
    total_ev = 0.0
    total_pv = 0.0

    if budget_col:
        budget_values = _safe_numeric(df[budget_col])
        total_budget = float(budget_values.sum())

    if actual_col:
        actual_values = _safe_numeric(df[actual_col])
        total_actual = float(actual_values.sum())

    # Earned Value: use explicit column or compute from budget × %complete
    if ev_col:
        ev_values = _safe_numeric(df[ev_col])
        total_ev = float(ev_values.sum())
    elif budget_col and pct_col:
        pct_values = _safe_numeric(df[pct_col])
        # Handle percentages expressed as 0-100 or 0-1
        if pct_values.max() > 1.0:
            pct_values = pct_values / 100.0
        budget_values = _safe_numeric(df[budget_col])
        total_ev = float((budget_values * pct_values.fillna(0)).sum())

    # Planned Value: use explicit column or fall back to budget
    if pv_col:
        pv_values = _safe_numeric(df[pv_col])
        total_pv = float(pv_values.sum())
    else:
        total_pv = total_budget  # approximate

    # ── CPI Calculation ────────────────────────────────────────────────
    cpi = 0.0
    if total_actual > 0:
        cpi = total_ev / total_actual if total_ev > 0 else total_budget / total_actual
    elif total_budget > 0:
        cpi = 1.0  # No spend yet, assume on track

    # ── Burn Rate ──────────────────────────────────────────────────────
    burn_rate = 0.0
    if total_budget > 0:
        burn_rate = (total_actual / total_budget) * 100.0

    # ── Score Calculation ──────────────────────────────────────────────
    # CPI >= 1.0 → 100 (under budget)
    # CPI = 0.8 → 60
    # CPI = 0.5 → 0
    # Linear mapping: score = max(0, min(100, (CPI - 0.5) * 200))
    score = max(0.0, min(100.0, (cpi - 0.5) * 200.0))

    details: dict[str, Any] = {
        "total_budget": round(total_budget, 2),
        "total_actual_cost": round(total_actual, 2),
        "earned_value": round(total_ev, 2),
        "planned_value": round(total_pv, 2),
        "cpi": round(cpi, 3),
        "burn_rate_pct": round(burn_rate, 1),
    }

    reason_parts = []
    if cpi >= 1.0:
        reason_parts.append(f"CPI is {cpi:.2f} (under budget).")
    elif cpi >= 0.8:
        reason_parts.append(f"CPI is {cpi:.2f} (slightly over budget).")
    else:
        reason_parts.append(f"CPI is {cpi:.2f} (significantly over budget).")
    reason_parts.append(f"Burn rate: {burn_rate:.0f}% of total budget consumed.")

    logger.info("Budget signal: score=%.1f, CPI=%.3f, burn=%.1f%%", score, cpi, burn_rate)

    return SignalResult(
        name=SIGNAL_NAME,
        score=round(score, 1),
        weight=DEFAULT_WEIGHT,
        available=True,
        details=details,
        reason=" ".join(reason_parts),
    )
