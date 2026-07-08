"""
LLM-assisted column mapping for messy/varying xlsx schemas.

Sends column headers + sample rows to the LLM, gets back a structured
mapping from canonical field names to actual column names.
Falls back to fuzzy heuristic matching if LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from app.llm_client import get_llm_client

logger = logging.getLogger(__name__)

# Canonical field names the system expects
CANONICAL_FIELDS: dict[str, dict[str, Any]] = {
    # Tasks sheet
    "task_name": {"description": "Name or title of the task/activity", "required": True},
    "planned_start": {"description": "Planned/baseline start date", "required": False},
    "planned_end": {"description": "Planned/baseline end date or due date", "required": True},
    "actual_start": {"description": "Actual start date", "required": False},
    "actual_end": {"description": "Actual end/completion date", "required": False},
    "status": {"description": "Task status (e.g., Not Started, In Progress, Complete)", "required": False},
    "is_critical": {"description": "Whether task is on the critical path", "required": False},
    "pct_complete": {"description": "Percentage complete (0-100)", "required": False},
    # Budget fields
    "planned_budget": {"description": "Planned/baseline budget or cost", "required": False},
    "actual_cost": {"description": "Actual cost incurred", "required": False},
    "earned_value": {"description": "Earned value (EV)", "required": False},
    "planned_value": {"description": "Planned value (PV)", "required": False},
    # Milestone fields
    "is_milestone": {"description": "Flag indicating if this row is a milestone", "required": False},
    # Blocker fields
    "blocker": {"description": "Blocker or issue description", "required": False},
    "severity": {"description": "Blocker severity (low/medium/high/critical)", "required": False},
    "created_date": {"description": "Date blocker was raised", "required": False},
    "resolved_date": {"description": "Date blocker was resolved", "required": False},
    # Notes
    "notes": {"description": "Free-text status notes or comments", "required": False},
}

MAPPING_SYSTEM_PROMPT = """You are a data schema analyst specializing in project management spreadsheets.
Given a list of column headers and sample data rows from a project plan spreadsheet, map each column
to the most appropriate canonical field name from the provided list.

Rules:
1. Map each source column to AT MOST one canonical field.
2. Not every source column needs to be mapped — skip irrelevant columns.
3. Not every canonical field will have a match — that's fine.
4. Be conservative: only map when you're reasonably confident.
5. Consider both column name similarity AND sample data values when deciding.
6. DO NOT map purely numeric columns (like IDs or durations) to text description fields like 'blocker', 'task_name', or 'notes'.

Respond with ONLY a JSON object:
{
  "mapping": {
    "<canonical_field_name>": "<actual_column_name>",
    ...
  },
  "unmapped_columns": ["<col1>", "<col2>", ...],
  "notes": ["<any observations about the data>"]
}"""


async def map_schema_with_llm(
    columns: list[str],
    sample_rows: list[dict[str, Any]],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """
    Use LLM to map spreadsheet columns to canonical field names.

    Args:
        columns: List of column header names from the spreadsheet.
        sample_rows: First few rows of data as dicts.

    Returns:
        Tuple of (mapping dict, log entries).
    """
    log: list[dict[str, Any]] = []

    # Build the prompt
    canonical_desc = {
        name: info["description"]
        for name, info in CANONICAL_FIELDS.items()
    }

    user_prompt = (
        f"Canonical fields and their descriptions:\n{json.dumps(canonical_desc, indent=2)}\n\n"
        f"Source columns: {json.dumps(columns)}\n\n"
        f"Sample data rows (first 5):\n{json.dumps(sample_rows[:5], indent=2, default=str)}"
    )

    try:
        llm = get_llm_client()
        result = await llm.complete_json(
            system_prompt=MAPPING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=1024,
        )

        mapping = result.get("mapping", {})
        unmapped = result.get("unmapped_columns", [])
        notes = result.get("notes", [])

        # Validate mapping — ensure mapped columns actually exist
        validated_mapping: dict[str, str] = {}
        for canonical, actual in mapping.items():
            if canonical in CANONICAL_FIELDS and actual in columns:
                validated_mapping[canonical] = actual
                log.append({
                    "action": "mapped",
                    "canonical": canonical,
                    "actual": actual,
                    "method": "llm",
                })
            else:
                log.append({
                    "action": "rejected",
                    "canonical": canonical,
                    "actual": actual,
                    "reason": "canonical or actual column not found",
                    "method": "llm",
                })

        for col in unmapped:
            log.append({
                "action": "unmapped",
                "column": col,
                "method": "llm",
            })

        for note in notes:
            log.append({"action": "note", "message": note, "method": "llm"})

        logger.info("LLM schema mapping: %d fields mapped, %d unmapped columns", len(validated_mapping), len(unmapped))
        return validated_mapping, log

    except Exception as e:
        logger.warning("LLM schema mapping failed: %s — falling back to heuristic", e)
        log.append({
            "action": "llm_fallback",
            "reason": str(e),
            "method": "heuristic",
        })
        return map_schema_heuristic(columns, log)


def map_schema_heuristic(
    columns: list[str],
    log: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """
    Heuristic column mapping using fuzzy string matching.

    Falls back to this when LLM is unavailable.
    """
    if log is None:
        log = []

    # Common aliases for canonical fields
    ALIASES: dict[str, list[str]] = {
        "task_name": ["task", "task_name", "task name", "activity", "work_item", "deliverable", "name", "item"],
        "planned_start": ["planned_start", "baseline_start", "start_date", "start date", "plan_start", "start", "baseline_start2"],
        "planned_end": ["planned_end", "planned_finish", "baseline_end", "due_date", "end_date", "end date", "plan_end", "deadline", "finish", "baseline_finish", "baseline_finish2"],
        "actual_start": ["actual_start", "real_start"],
        "actual_end": ["actual_end", "actual_finish", "completed_date", "finish_date", "completion_date"],
        "status": ["status", "task_status", "state", "progress_status"],
        "is_critical": ["critical", "is_critical", "critical_path", "on_critical_path", "critical_?", "critical ?"],
        "pct_complete": ["pct_complete", "percent_complete", "%_complete", "completion", "progress", "%_complete", "% complete"],
        "planned_budget": ["budget", "planned_budget", "baseline_cost", "planned_cost", "estimated_cost", "total_float", "total float"],
        "actual_cost": ["actual_cost", "actual_spend", "spend", "cost_to_date", "incurred_cost", "cost"],
        "earned_value": ["earned_value", "ev"],
        "planned_value": ["planned_value", "pv"],
        "is_milestone": ["is_milestone", "milestone_flag", "milestone", "phase/milestone"],
        "blocker": ["blocker", "issue", "risk", "impediment", "problem", "blocker_description", "on_hold?", "on hold?", "at_risk?", "at risk?"],
        "severity": ["severity", "priority", "impact", "level"],
        "created_date": ["created_date", "identified_date", "date_raised", "raised_date"],
        "resolved_date": ["resolved_date", "resolution_date", "closed_date", "fixed_date"],
        "notes": ["notes", "comments", "remarks", "status_notes", "status_comment", "status comment", "update", "observation"],
    }

    mapping: dict[str, str] = {}
    used_columns: set[str] = set()

    # Normalize column names for comparison
    normalized_cols = {col: col.lower().strip().replace(" ", "_") for col in columns}

    for canonical, aliases in ALIASES.items():
        best_match: str | None = None
        best_score: float = 0.0

        for col, norm_col in normalized_cols.items():
            if col in used_columns:
                continue

            # Direct match
            if norm_col in aliases:
                best_match = col
                best_score = 1.0
                break

            # Fuzzy match
            for alias in aliases:
                score = SequenceMatcher(None, norm_col, alias).ratio()
                if score > best_score and score >= 0.7:
                    best_score = score
                    best_match = col

        if best_match:
            mapping[canonical] = best_match
            used_columns.add(best_match)
            log.append({
                "action": "mapped",
                "canonical": canonical,
                "actual": best_match,
                "confidence": round(best_score, 2),
                "method": "heuristic",
            })

    # Log unmapped columns
    for col in columns:
        if col not in used_columns:
            log.append({
                "action": "unmapped",
                "column": col,
                "method": "heuristic",
            })

    logger.info("Heuristic schema mapping: %d fields mapped", len(mapping))
    return mapping, log


async def extract_project_metadata_with_llm(sheets: list[Any]) -> dict[str, Any]:
    """
    Extract high-level project metadata (Manager, Start, End dates) across all sheets using LLM.
    """
    log_info = []
    for sheet in sheets:
        log_info.append({
            "sheet_name": sheet.name,
            "columns": sheet.columns,
            "sample_rows": sheet.sample_rows[:5]
        })
        
    prompt = (
        "You are a project management assistant. Below is sample data from multiple sheets of an Excel project file.\n"
        "Your goal is to extract the overall Project Manager name, the Project Start Date, and the Project End Date if they exist in ANY of these sheets.\n"
        "Return ONLY a JSON object exactly matching this schema:\n"
        "{\n"
        "  \"manager_name\": \"Name or null\",\n"
        "  \"start_date\": \"YYYY-MM-DD or null\",\n"
        "  \"end_date\": \"YYYY-MM-DD or null\"\n"
        "}\n\n"
        f"Sheet data: {json.dumps(log_info, default=str)}"
    )
    
    try:
        llm = get_llm_client()
        result = await llm.complete_json(
            system_prompt="You are a project management assistant that extracts project metadata.",
            user_prompt=prompt
        )
        return result
    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return {"manager_name": None, "start_date": None, "end_date": None}
