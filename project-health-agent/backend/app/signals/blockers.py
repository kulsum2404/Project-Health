"""
Blockers signal — Weight: 15%

Computes: Σ(severity_weight × age_in_days) normalized, capped.
Data source: blocker/issue notes or status columns.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any

import pandas as pd

from app.models import SignalResult

logger = logging.getLogger(__name__)

SIGNAL_NAME = "blockers"
DEFAULT_WEIGHT = 0.15

SEVERITY_WEIGHTS: dict[str, float] = {
    "low": 1.0,
    "medium": 2.0,
    "high": 4.0,
    "critical": 8.0,
}

# Maximum raw score before normalization (caps impact of extreme values)
MAX_RAW_SCORE = 200.0

COLUMN_CANDIDATES = {
    "blocker_desc": [
        "blocker", "issue", "risk", "blocker_description", "issue_description",
        "impediment", "problem", "concern", "Status Comment",
    ],
    "severity": ["severity", "priority", "impact", "level", "Priority"],
    "created_date": ["created_date", "identified_date", "date_raised", "date", "Start Date"],
    "resolved_date": ["resolved_date", "resolution_date", "closed_date"],
    "status": ["status", "blocker_status", "issue_status", "state", "Status", "On Hold?", "At Risk?"],
}


def _find_column(df: pd.DataFrame, mapping: dict[str, str], candidates: list[str]) -> str | None:
    def is_usable(col_name: str) -> bool:
        if df.empty:
            return True
        fill_count = df[col_name].notna().sum()
        if fill_count == 0:
            logger.warning(f"Blocker signal: mapped column '{col_name}' is 100% empty. Skipping and trying next synonym.")
            return False
        return fill_count >= 3 or (fill_count / len(df)) > 0.1

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


def _infer_severity(text: str) -> str:
    """Heuristic severity inference from text when no severity column exists."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["critical", "blocked", "showstopper", "urgent"]):
        return "critical"
    if any(kw in text_lower for kw in ["high", "major", "severe", "significant"]):
        return "high"
    if any(kw in text_lower for kw in ["low", "minor", "trivial"]):
        return "low"
    return "medium"


def compute_blocker_signal(
    df: pd.DataFrame,
    mapping: dict[str, str],
    reference_date: datetime | None = None,
) -> SignalResult:
    """
    Compute the blockers signal.

    Lower raw score = healthier (fewer/less severe blockers).
    Output score is inverted: 100 = no blockers, 0 = severe blockers.
    """
    if reference_date is None:
        reference_date = datetime.utcnow()

    if df.empty:
        # No data — could mean no blockers (good) or no data
        logger.info("Blocker signal: empty DataFrame — assuming no blockers")
        return SignalResult(
            name=SIGNAL_NAME,
            score=100.0,
            weight=DEFAULT_WEIGHT,
            available=True,
            details={"total_blockers": 0, "unresolved": 0, "reason": "No blocker data rows"},
            reason="No blockers reported.",
        )

    desc_col = _find_column(df, mapping, COLUMN_CANDIDATES["blocker_desc"])
    severity_col = _find_column(df, mapping, COLUMN_CANDIDATES["severity"])
    created_col = _find_column(df, mapping, COLUMN_CANDIDATES["created_date"])
    resolved_col = _find_column(df, mapping, COLUMN_CANDIDATES["resolved_date"])
    status_col = _find_column(df, mapping, COLUMN_CANDIDATES["status"])

    if desc_col is None and severity_col is None and status_col is None:
        logger.warning("Blocker signal: no blocker-related columns found — signal unavailable")
        return SignalResult(
            name=SIGNAL_NAME,
            score=0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No blocker-related columns found"},
            reason="No blocker columns found in data.",
        )

    # A row should only be considered a blocker if it has a description or severity.
    # Otherwise, we might mistakenly treat normal tasks as blockers if they just have a Start Date.
    mask = pd.Series([False] * len(df), index=df.index)
    has_blocker_data = False
    
    if desc_col:
        desc_mask = df[desc_col].notna() & (df[desc_col] != "")
        if desc_mask.any():
            mask = mask | desc_mask
            has_blocker_data = True
            
    if severity_col:
        sev_mask = df[severity_col].notna() & (df[severity_col] != "")
        if sev_mask.any():
            mask = mask | sev_mask
            has_blocker_data = True

    if not has_blocker_data:
        return SignalResult(
            name=SIGNAL_NAME,
            score=0.0,
            weight=DEFAULT_WEIGHT,
            available=False,
            details={"reason": "No populated blocker description or severity columns found"},
            reason="Blocker columns not found in data.",
        )

    blocker_df = df[mask]
    total_blockers = len(blocker_df)

    if total_blockers == 0:
        return SignalResult(
            name=SIGNAL_NAME,
            score=100.0,
            weight=DEFAULT_WEIGHT,
            available=True,
            details={"total_blockers": 0, "unresolved": 0},
            reason="No blockers reported.",
        )

    # Determine resolution status
    ref_ts = pd.Timestamp(reference_date)

    if status_col:
        resolved_mask = blocker_df[status_col].astype(str).str.lower().isin(
            ["resolved", "closed", "done", "fixed", "complete", "completed"]
        )
    elif resolved_col:
        resolved_dates = pd.to_datetime(blocker_df[resolved_col], errors="coerce")
        resolved_mask = resolved_dates.notna()
    else:
        resolved_mask = pd.Series([False] * len(blocker_df), index=blocker_df.index)

    unresolved_df = blocker_df[~resolved_mask]
    unresolved_count = len(unresolved_df)

    if unresolved_count == 0:
        return SignalResult(
            name=SIGNAL_NAME,
            score=95.0,  # Minor deduction for having had blockers
            weight=DEFAULT_WEIGHT,
            available=True,
            details={
                "total_blockers": total_blockers,
                "unresolved": 0,
                "all_resolved": True,
            },
            reason=f"All {total_blockers} blockers have been resolved.",
        )

    # ── Compute severity × age score ───────────────────────────────────
    severities: list[str] = []
    ages: list[float] = []
    has_critical_over_7d = False
    has_moderate_unresolved = False
    critical_count = 0

    for idx, row in unresolved_df.iterrows():
        # Severity
        if severity_col and pd.notna(row.get(severity_col)):
            sev = str(row[severity_col]).lower().strip()
            if sev not in SEVERITY_WEIGHTS:
                sev = _infer_severity(sev)
        elif desc_col and pd.notna(row.get(desc_col)):
            sev = _infer_severity(str(row[desc_col]))
        else:
            sev = "medium"
        severities.append(sev)

        # Age
        if created_col and pd.notna(row.get(created_col)):
            created = pd.to_datetime(row[created_col], errors="coerce")
            if pd.notna(created):
                age = max(1.0, (ref_ts - created).days)
            else:
                age = 7.0  # default assumption
        else:
            age = 7.0
        ages.append(age)

        # Check critical thresholds
        if sev == "critical":
            critical_count += 1
            if age > 7:
                has_critical_over_7d = True
        if sev in ("medium", "high") and not has_moderate_unresolved:
            has_moderate_unresolved = True

    # Weighted sum using logarithmic age weighting
    raw_score = sum(
        SEVERITY_WEIGHTS.get(sev, 2.0) * math.log(1 + age)
        for sev, age in zip(severities, ages)
    )

    # Normalize and invert (cap at MAX_RAW_SCORE)
    capped = min(raw_score, MAX_RAW_SCORE)
    score = max(0.0, 100.0 - (capped / MAX_RAW_SCORE * 100.0))

    details: dict[str, Any] = {
        "total_blockers": total_blockers,
        "unresolved": unresolved_count,
        "critical_count": critical_count,
        "has_critical_over_7d": has_critical_over_7d,
        "has_moderate_unresolved": has_moderate_unresolved,
        "raw_weighted_score": round(raw_score, 1),
        "severity_distribution": {
            sev: severities.count(sev) for sev in set(severities)
        },
    }

    reason_parts = [f"{unresolved_count} unresolved blockers out of {total_blockers} total."]
    if ages:
        oldest_age = int(max(ages))
        reason_parts.append(f"Oldest unresolved blocker is {oldest_age} days old.")
    if critical_count > 0:
        reason_parts.append(f"{critical_count} critical blocker(s).")
    if has_critical_over_7d:
        reason_parts.append("Critical blocker unresolved for more than 7 days.")

    logger.info(
        "Blocker signal: score=%.1f, unresolved=%d, critical=%d",
        score, unresolved_count, critical_count,
    )

    return SignalResult(
        name=SIGNAL_NAME,
        score=round(score, 1),
        weight=DEFAULT_WEIGHT,
        available=True,
        details=details,
        reason=" ".join(reason_parts),
    )
