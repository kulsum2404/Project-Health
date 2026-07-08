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

REASONING_SYSTEM_PROMPT = """You are a senior project health analyst writing a comprehensive executive analysis for a project's current health status.

You will receive a JSON object containing:
- The RAG status (red/amber/green) determined by our scoring system
- The weighted score (0-100)
- Individual signal scores and details for: schedule, budget, milestones, blockers, and sentiment
- Any override reasons that forced the status
- The weights used for each signal

Your job is to write a DETAILED, multi-paragraph analysis that covers:

**Paragraph 1 — Executive Summary**: State the overall health status, the weighted score, and the primary factors driving it. Mention if any override conditions were triggered.

**Paragraph 2 — Schedule & Milestones Deep Dive**: Analyze the schedule and milestone signals together. Cite specific numbers: how many tasks are overdue, what percentage, any critical path delays, milestone on-time rates. Explain what this means for project delivery.

**Paragraph 3 — Budget & Resource Analysis**: Discuss the CPI, burn rate, earned value vs planned value. Explain whether the project is tracking to budget or heading for a cost overrun. If budget data was limited, note that.

**Paragraph 4 — Risk & Blocker Assessment**: Analyze unresolved blockers — their count, severity distribution, and age. Highlight any critical blockers and their potential impact. If there are no blockers, note that as a positive signal.

**Paragraph 5 — Stakeholder Sentiment**: Discuss the sentiment analysis results — how many entries were classified, the distribution of positive/neutral/negative, and what this indicates about team morale and stakeholder confidence.

**Paragraph 6 — Score Contribution Breakdown**: Explain how each signal's score contributes to the final weighted score. For example: "Schedule (score 85 × weight 30% = 25.5 points), Budget (score 100 × weight 20% = 20.0 points)..." Show the math clearly.

**Paragraph 7 — Key Risks & Recommendations**: Based on the data, identify the top 2-3 risks and provide actionable recommendations for the project manager.

IMPORTANT RULES:
- ONLY reference data from the JSON provided. Do NOT invent or assume any data not present.
- Be factual and specific — cite actual numbers from the signals.
- Do not speculate about causes beyond what the data shows.
- Keep the tone professional — this is for executive stakeholders.
- If signals were skipped, mention this impacts confidence.
- Use clear paragraph breaks between sections.
- Each paragraph should be substantive (3-5 sentences minimum)."""


SIGNAL_EXPLANATION_SYSTEM_PROMPT = """You are a project health analyst explaining a specific scoring factor to a project manager.

You will receive:
- The signal name (e.g. "schedule", "budget", "milestones", "blockers", "sentiment")
- The signal's score (0-100), raw details, and reason
- The signal's weight in the overall scoring model
- The overall project weighted score and RAG status

Write a detailed explanation (4-6 sentences) that covers:
1. WHY this project received this specific score — what exact data points drove it up or down. Do NOT explain what the signal measures in general; the user already knows that.
2. The specific numbers: cite exact counts, percentages, and values from the details (e.g., "44 of 383 milestones are late, bringing your on-time rate to 89%")
3. Show the score math clearly (e.g., "Your score of 89 comes from 89% on-time rate with no SPI adjustment")
4. How this signal's score contributes to the overall weighted score: score × weight = X contribution points out of the total Y
5. Whether this signal is dragging the overall project health DOWN or pushing it UP, and by how many points relative to a perfect 100
6. One specific, actionable recommendation to improve this score

IMPORTANT RULES:
- Do NOT start with a generic definition of the signal. Jump straight into the project-specific analysis.
- ONLY use data from the JSON provided. Never invent data.
- Be specific — cite exact numbers, percentages, and counts from the details.
- Show the math: signal_score × weight = contribution to overall score.
- Keep the tone direct and analytical — speak to the project manager."""


async def generate_reasoning(rag_result: RagResult, project_name: str) -> str:
    """
    Generate a comprehensive plain-English analysis for a RAG classification.

    Args:
        rag_result: The deterministic classification result with all signal data.
        project_name: The project's name for context.

    Returns:
        A multi-paragraph analysis string.
    """
    # Build the structured input for the LLM
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

    input_json = {
        "project_name": project_name,
        "rag_status": rag_result.status.value,
        "weighted_score": rag_result.weighted_score,
        "confidence": rag_result.confidence,
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

    user_prompt = (
        f"Generate a comprehensive health analysis for the following project data:\n\n"
        f"{json.dumps(input_json, indent=2)}"
    )

    try:
        llm = get_llm_client()
        reasoning = await llm.complete(
            system_prompt=REASONING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2048,
        )

        # Clean up any leading/trailing whitespace
        reasoning = reasoning.strip()
        logger.info("Generated reasoning for %s: %d chars", project_name, len(reasoning))
        return reasoning

    except Exception as e:
        logger.error("Failed to generate reasoning for %s: %s", project_name, e)
        # Fall back to a deterministic summary
        return _fallback_reasoning(rag_result, project_name)


async def generate_signal_explanation(
    signal_name: str,
    signal_data: dict,
    overall_score: float,
    rag_status: str,
    confidence: float,
) -> str:
    """
    Generate a targeted LLM explanation for a single signal.

    Args:
        signal_name: The signal identifier (schedule, budget, etc.)
        signal_data: The signal's score, details, reason, and weight info.
        overall_score: The overall weighted project score.
        rag_status: The overall RAG status.
        confidence: The data confidence level.

    Returns:
        A detailed explanation string for this signal.
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
            max_tokens=1024,
        )
        return explanation.strip()

    except Exception as e:
        logger.error("Failed to generate signal explanation for %s: %s", signal_name, e)
        # Fall back to a deterministic explanation
        return _fallback_signal_explanation(signal_name, signal_data, overall_score)


def _fallback_reasoning(rag_result: RagResult, project_name: str) -> str:
    """Generate a comprehensive deterministic reasoning when LLM is unavailable."""
    parts = [
        f"Project '{project_name}' is rated {rag_result.status.value.upper()} "
        f"with a weighted score of {rag_result.weighted_score}/100 "
        f"(confidence: {rag_result.confidence:.0%})."
    ]

    # Calculate weight contributions
    total_available_weight = sum(
        s.weight for s in rag_result.signals if s.available
    )

    # Add detailed signal summaries
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
