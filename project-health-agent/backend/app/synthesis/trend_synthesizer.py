"""
Cross-project trend synthesizer — identifies patterns across all projects.

Explicitly prompts the LLM to find cross-project patterns rather than
concatenating per-project summaries. This is a stated requirement.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.llm_client import get_llm_client

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are a senior portfolio analyst synthesizing project health data across multiple projects for an executive audience.

You will receive historical snapshot data for all projects in a portfolio. Your job is to identify CROSS-PROJECT PATTERNS — not per-project summaries.

CRITICAL REQUIREMENT: You must look for patterns that span multiple projects. Examples:
- "3 of 5 projects show budget CPI decline in the last 2 weeks, concentrated in vendor-dependent tasks"
- "Schedule slippage is trending upward across the portfolio, with 60% of projects showing increased overdue tasks"
- "Stakeholder sentiment has improved portfolio-wide, correlating with the Q2 milestone completions"

Do NOT simply summarize each project individually. Look for:
1. Common trends (improving/declining signals across projects)
2. Shared risk factors (multiple projects affected by same issue type)
3. Portfolio-level patterns (concentration of problems in specific signal areas)
4. Temporal patterns (acceleration/deceleration of issues over time)

Respond with a JSON object:
{
  "executive_summary": "2-3 sentence portfolio health overview",
  "trends": [
    {"description": "...", "affected_projects": ["..."], "direction": "improving|declining|stable", "severity": "low|medium|high"}
  ],
  "emerging_risks": [
    {"description": "...", "affected_projects": ["..."], "urgency": "low|medium|high|critical"}
  ],
  "notable_wins": [
    {"description": "...", "projects": ["..."]}
  ],
  "recommendations": [
    "Actionable recommendation 1",
    "Actionable recommendation 2",
    "..."
  ],
  "rag_shifts": [
    {"project": "...", "from": "green|amber|red", "to": "green|amber|red", "reason": "..."}
  ]
}

Keep recommendations to 3-5 actionable bullet points.
Base everything on the data provided — do not speculate beyond what the numbers show."""


async def synthesize_trends(
    project_snapshots: dict[str, list[dict[str, Any]]],
    period_start: datetime,
    period_end: datetime,
    portfolio_name: str = "Project Portfolio",
) -> dict[str, Any]:
    """
    Synthesize cross-project trends from all projects' snapshot history.

    Args:
        project_snapshots: Dict mapping project names to their snapshot history.
        period_start: Start of the reporting period.
        period_end: End of the reporting period.
        portfolio_name: Name of the portfolio.

    Returns:
        Structured synthesis data dict.
    """
    if not project_snapshots:
        return {
            "executive_summary": "No project data available for synthesis.",
            "trends": [],
            "emerging_risks": [],
            "notable_wins": [],
            "recommendations": ["Upload and analyze project plans to generate synthesis."],
            "rag_shifts": [],
        }

    # Build the analysis prompt
    portfolio_summary = _build_portfolio_summary(project_snapshots)

    user_prompt = (
        f"Portfolio: {portfolio_name}\n"
        f"Reporting Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}\n"
        f"Total Projects: {len(project_snapshots)}\n\n"
        f"Project Snapshot History:\n{json.dumps(portfolio_summary, indent=2, default=str)}"
    )

    try:
        llm = get_llm_client()
        result = await llm.complete_json(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2048,
            temperature=0.3,
        )

        logger.info("Trend synthesis complete for %d projects", len(project_snapshots))
        return result

    except Exception as e:
        logger.error("Trend synthesis failed: %s", e)
        return _fallback_synthesis(project_snapshots)


def _build_portfolio_summary(
    project_snapshots: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build a compact summary of all projects for the LLM prompt."""
    summary: dict[str, Any] = {}

    for project_name, snapshots in project_snapshots.items():
        if not snapshots:
            continue

        latest = snapshots[-1]
        first = snapshots[0]

        # Calculate trends
        project_info: dict[str, Any] = {
            "total_snapshots": len(snapshots),
            "latest": {
                "date": latest.get("date"),
                "rag_status": latest.get("rag_status"),
                "weighted_score": latest.get("weighted_score"),
                "confidence": latest.get("confidence"),
                "schedule_score": latest.get("schedule_score"),
                "budget_score": latest.get("budget_score"),
                "milestone_score": latest.get("milestone_score"),
                "blocker_score": latest.get("blocker_score"),
                "sentiment_score": latest.get("sentiment_score"),
                "signals_used": latest.get("signals_used"),
                "signals_skipped": latest.get("signals_skipped"),
            },
        }

        # Add trend data if multiple snapshots
        if len(snapshots) >= 2:
            project_info["first_snapshot"] = {
                "date": first.get("date"),
                "rag_status": first.get("rag_status"),
                "weighted_score": first.get("weighted_score"),
            }

            # Score trend
            scores = [s.get("weighted_score", 0) for s in snapshots]
            project_info["score_trend"] = {
                "direction": "improving" if scores[-1] > scores[0] else (
                    "declining" if scores[-1] < scores[0] else "stable"
                ),
                "delta": round(scores[-1] - scores[0], 1),
                "min": round(min(scores), 1),
                "max": round(max(scores), 1),
            }

            # RAG status changes
            rag_history = [s.get("rag_status") for s in snapshots]
            unique_statuses = list(dict.fromkeys(rag_history))
            if len(unique_statuses) > 1:
                project_info["rag_changes"] = rag_history

        # Signal details from latest
        if latest.get("signal_details"):
            project_info["signal_details"] = latest["signal_details"]

        summary[project_name] = project_info

    return summary


def _fallback_synthesis(
    project_snapshots: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Generate a basic deterministic synthesis when LLM is unavailable."""
    rag_counts = {"green": 0, "amber": 0, "red": 0}
    declining_projects: list[str] = []
    improving_projects: list[str] = []

    for name, snapshots in project_snapshots.items():
        if snapshots:
            latest = snapshots[-1]
            status = latest.get("rag_status", "amber")
            rag_counts[status] = rag_counts.get(status, 0) + 1

            if len(snapshots) >= 2:
                first_score = snapshots[0].get("weighted_score", 50)
                last_score = snapshots[-1].get("weighted_score", 50)
                if last_score < first_score - 5:
                    declining_projects.append(name)
                elif last_score > first_score + 5:
                    improving_projects.append(name)

    total = sum(rag_counts.values())
    summary = (
        f"Portfolio has {total} projects: {rag_counts['green']} green, "
        f"{rag_counts['amber']} amber, {rag_counts['red']} red."
    )

    risks = []
    if declining_projects:
        risks.append({
            "description": f"Score declining in: {', '.join(declining_projects)}",
            "affected_projects": declining_projects,
            "urgency": "medium",
        })

    wins = []
    if improving_projects:
        wins.append({
            "description": f"Score improving in: {', '.join(improving_projects)}",
            "projects": improving_projects,
        })

    return {
        "executive_summary": summary,
        "trends": [],
        "emerging_risks": risks,
        "notable_wins": wins,
        "recommendations": ["Review declining projects for intervention opportunities."],
        "rag_shifts": [],
    }
