"""
LLM reasoning layer — generates plain-English explanations.

The RAG color always comes from the deterministic classifier.
The LLM's only job is to write comprehensive explanations grounded
in the structured signal JSON it receives.
"""

from __future__ import annotations

import json
import logging

from app.llm_client import get_llm_client
from app.models.models import RagResult

logger = logging.getLogger(__name__)

# ── New concise prompt matching the reference report style ────────────────

REASONING_SYSTEM_PROMPT = """You are a senior project health analyst writing a concise weekly health report.

You will receive a JSON object containing:
- The RAG status (red/amber/green) determined by our scoring system
- The weighted score (0-100)
- Individual signal scores and details for: schedule, budget, milestones, blockers, and sentiment
- Any override reasons that forced the status
- The weights used for each signal

Your job is to return a valid JSON object with the following fields:

{
  "executive_summary": "...",
  "discrepancy_reason": "...",
  "signal_summaries": {
    "schedule": "...",
    "budget": "...",
    "milestones": "...",
    "blockers": "...",
    "sentiment": "..."
  }
}

RULES FOR discrepancy_reason:
- If the input JSON has `discrepancy_flag = true`, you MUST provide a one-sentence explanation of why the self-reported status differs from our computed RAG status, grounded in the specific signals driving the gap (e.g. "Self-reported: Green. Computed: Red. Driven by 13 critical-path tasks stalled beyond baseline that aren't reflected in the summary status.")
- If `discrepancy_flag = false`, return an empty string or null.

RULES FOR executive_summary:
- Provide a highly detailed, comprehensive executive summary.
- Lead with the most critical findings.
- Use "quoted phrases" to highlight key data from the source file (e.g., "Schedule Health: Green" or "At Risk: High"). These will be rendered as colored highlights in the UI.
- Cite specific numbers: tasks overdue, days behind, milestones missed, unresolved blockers.
- If a signal was excluded (e.g., no budget data), mention it.
- Tone: professional, analytical, and highly detailed.

RULES FOR signal_summaries:
- Provide a detailed summary for each individual signal.
- For each AVAILABLE signal, write a comprehensive explanation of the key findings.
- Cite specific numbers extensively (e.g., "13 critical-path tasks are Not Started and already 41–63 days behind baseline").
- For UNAVAILABLE/SKIPPED signals, write "Signal excluded — [reason]." (e.g., "Signal excluded — no cost columns detected in source file.")
- Explain the precise impact on the project's overall health.

IMPORTANT:
- ONLY reference data from the JSON provided. Do NOT invent data.
- Be factual — cite actual numbers from the signal details.
- The response MUST be valid JSON. No markdown code fences."""


SIGNAL_EXPLANATION_SYSTEM_PROMPT = """You are a project health analyst explaining a specific scoring factor to a project manager.

You will receive:
- The signal name (e.g. "schedule", "budget", "milestones", "blockers", "sentiment")
- The signal's score (0-100), raw details, and reason
- The signal's weight in the overall scoring model
- The overall project weighted score and RAG status

Write a concise explanation (2-3 sentences) that covers:
1. The key data points driving this specific score — cite exact numbers
2. Whether this signal is helping or hurting the overall project health
3. One specific, actionable recommendation

IMPORTANT RULES:
- Do NOT start with a generic definition of the signal. Jump straight into the analysis.
- ONLY use data from the JSON provided. Never invent data.
- Be specific — cite exact numbers, percentages, and counts.
- Keep it punchy and direct — speak to the project manager."""


async def generate_reasoning(rag_result: RagResult, project_name: str) -> str:
    """
    Generate a concise structured analysis for a RAG classification.

    Returns the executive_summary as a string (the signal_summaries
    are returned separately via generate_signal_summaries).
    """
    input_json = _build_reasoning_input(rag_result, project_name)

    user_prompt = (
        f"Generate a concise health analysis for the following project data:\n\n"
        f"{json.dumps(input_json, indent=2)}"
    )

    try:
        llm = get_llm_client()
        raw = await llm.complete_json(
            system_prompt=REASONING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2048,
        )

        executive_summary = raw.get("executive_summary", "")

        logger.info("Generated reasoning for %s: %d chars", project_name, len(executive_summary))
        return executive_summary

    except Exception as e:
        logger.error("Failed to generate reasoning for %s: %s", project_name, e)
        return _fallback_reasoning(rag_result, project_name)


async def generate_signal_summaries(rag_result: RagResult, project_name: str) -> dict[str, str]:
    """
    Generate per-signal one-liner summaries.

    Returns a dict like {"schedule": "...", "budget": "...", ...}.
    """
    input_json = _build_reasoning_input(rag_result, project_name)

    user_prompt = (
        f"Generate a concise health analysis for the following project data:\n\n"
        f"{json.dumps(input_json, indent=2)}"
    )

    try:
        llm = get_llm_client()
        raw = await llm.complete_json(
            system_prompt=REASONING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2048,
        )

        summaries = raw.get("signal_summaries", {})
        logger.info("Generated signal summaries for %s: %s", project_name, list(summaries.keys()))
        return summaries

    except Exception as e:
        logger.error("Failed to generate signal summaries for %s: %s", project_name, e)
        return _fallback_signal_summaries(rag_result)


async def generate_reasoning_and_summaries(
    rag_result: RagResult, project_name: str
) -> tuple[str, dict[str, str]]:
    """
    Generate both the executive summary and per-signal summaries in a single LLM call.

    Returns (executive_summary, signal_summaries_dict).
    """
    input_json = _build_reasoning_input(rag_result, project_name)

    user_prompt = (
        f"Generate a concise health analysis for the following project data:\n\n"
        f"{json.dumps(input_json, indent=2)}"
    )

    try:
        llm = get_llm_client()
        raw = await llm.complete_json(
            system_prompt=REASONING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2048,
        )

        executive_summary = raw.get("executive_summary", "")
        signal_summaries = raw.get("signal_summaries", {})
        
        if rag_result.discrepancy_flag:
            rag_result.discrepancy_reason = raw.get("discrepancy_reason", "")

        logger.info(
            "Generated reasoning+summaries for %s: summary=%d chars, signals=%s",
            project_name, len(executive_summary), list(signal_summaries.keys()),
        )
        return executive_summary, signal_summaries

    except Exception as e:
        logger.error("Failed to generate reasoning for %s: %s", project_name, e)
        return (
            _fallback_reasoning(rag_result, project_name),
            _fallback_signal_summaries(rag_result),
        )


async def generate_signal_explanation(
    signal_name: str,
    signal_data: dict,
    overall_score: float,
    rag_status: str,
    confidence: float,
) -> str:
    """
    Generate a targeted LLM explanation for a single signal.
    """
    input_json = {
        "signal_name": signal_name,
        "signal_score": signal_data.get("score", 0),
        "signal_available": signal_data.get("available", False),
        "signal_details": signal_data.get("details", {}),
        "signal_reason": signal_data.get("reason", ""),
        "overall_weighted_score": overall_score,
        "rag_status": rag_status,
        "confidence": confidence,
    }

    user_prompt = (
        f"Explain the '{signal_name}' signal score for this project:\n\n"
        f"{json.dumps(input_json, indent=2)}"
    )

    try:
        llm = get_llm_client()
        explanation = await llm.complete(
            system_prompt=SIGNAL_EXPLANATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=512,
        )
        return explanation.strip()

    except Exception as e:
        logger.error("Failed to generate signal explanation for %s: %s", signal_name, e)
        return _fallback_signal_explanation(signal_name, signal_data, overall_score)


# ── Private helpers ───────────────────────────────────────────────────────


def _build_reasoning_input(rag_result: RagResult, project_name: str) -> dict:
    """Build the structured JSON input sent to the LLM."""
    signal_data = {}
    for signal in rag_result.signals:
        signal_data[signal.name] = {
            "score": signal.score,
            "weight": signal.weight,
            "available": signal.available,
            "details": signal.details,
            "reason": signal.reason,
        }

    # Calculate weight contributions for the LLM
    total_available_weight = sum(
        s.weight for s in rag_result.signals if s.available
    )
    weight_contributions = {}
    for signal in rag_result.signals:
        if signal.available and total_available_weight > 0:
            redistributed_weight = signal.weight / total_available_weight
            contribution = signal.score * redistributed_weight
            weight_contributions[signal.name] = {
                "original_weight_pct": round(signal.weight * 100, 1),
                "redistributed_weight_pct": round(redistributed_weight * 100, 1),
                "contribution_points": round(contribution, 1),
            }

    return {
        "project_name": project_name,
        "rag_status": rag_result.status.value,
        "weighted_score": rag_result.weighted_score,
        "confidence": rag_result.confidence,
        "self_reported_status": rag_result.self_reported_status,
        "discrepancy_flag": rag_result.discrepancy_flag,
        "signals_used": rag_result.signals_used,
        "signals_skipped": rag_result.signals_skipped,
        "signal_data": signal_data,
        "weight_contributions": weight_contributions,
        "override_reasons": rag_result.override_reasons,
        "thresholds": {
            "green": ">= 80",
            "amber": "60 - 79.9",
            "red": "< 60 or override triggered",
        },
    }


def _fallback_reasoning(rag_result: RagResult, project_name: str) -> str:
    """Generate a concise deterministic reasoning when LLM is unavailable."""
    parts = [
        f"Project '{project_name}' is rated {rag_result.status.value.upper()} "
        f"with a weighted score of {rag_result.weighted_score}/100 "
        f"(confidence: {rag_result.confidence:.0%})."
    ]

    total_available_weight = sum(
        s.weight for s in rag_result.signals if s.available
    )

    for signal in rag_result.signals:
        if signal.available:
            if total_available_weight > 0:
                redistributed_weight = signal.weight / total_available_weight
                contribution = signal.score * redistributed_weight
                parts.append(
                    f"{signal.name.title()} (score: {signal.score}/100, "
                    f"weight: {redistributed_weight:.0%}, "
                    f"contributes {contribution:.1f} points): {signal.reason}"
                )
            else:
                parts.append(f"{signal.name.title()}: {signal.reason}")

    if rag_result.signals_skipped:
        parts.append(
            f"Note: {', '.join(rag_result.signals_skipped)} signal(s) were "
            f"unavailable due to missing data."
        )

    if rag_result.override_reasons:
        parts.append(f"Status overrides: {'; '.join(rag_result.override_reasons)}.")

    return " ".join(parts)


def _fallback_signal_summaries(rag_result: RagResult) -> dict[str, str]:
    """Generate deterministic per-signal summaries when LLM is unavailable."""
    summaries = {}
    for signal in rag_result.signals:
        if signal.available:
            summaries[signal.name] = signal.reason
        else:
            summaries[signal.name] = f"Signal excluded — {signal.reason}"
    return summaries


def _fallback_signal_explanation(
    signal_name: str,
    signal_data: dict,
    overall_score: float,
) -> str:
    """Generate a basic signal explanation when LLM is unavailable."""
    score = signal_data.get("score", 0)
    reason = signal_data.get("reason", "No data available.")
    details = signal_data.get("details", {})

    detail_items = []
    for k, v in details.items():
        if k != "reason" and not isinstance(v, (dict, list)):
            detail_items.append(f"{k.replace('_', ' ').title()}: {v}")

    detail_str = ". ".join(detail_items) if detail_items else "No additional details."

    return (
        f"The {signal_name} signal scored {score}/100. {reason} "
        f"Key metrics: {detail_str} "
        f"This signal contributes to the overall weighted score of {overall_score}/100."
    )
