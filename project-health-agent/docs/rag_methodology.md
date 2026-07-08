# Project Health Reporting Methodology

This document outlines the methodology used by the Project Health Agent to determine an auditable, deterministic Red/Amber/Green (RAG) status for projects.

## Overview

The system uses a **Hybrid Deterministic + LLM Approach**:
1. **Deterministic Scoring Engine:** RAG status and a 0-100 health score are computed using strict mathematical rules based on standard project management metrics (CPI, SPI, slippage).
2. **LLM Reasoning Layer:** The AI's only role in classification is writing a plain-English executive summary that explains the math. It does not decide the color, preventing hallucinations.

---

## 1. Signal Extraction & Weights

The overall health score is a weighted average of up to 5 individual signals.

| Signal | Weight | Computation Methodology | Data Sources |
|---|---|---|---|
| **Schedule Slippage** | 30% | Combines % of tasks past due date with the magnitude of critical-path delay in days. Severe critical path delays incur heavy penalties. | Task start/end dates, planned/actual dates, critical path flags |
| **Budget Burn** | 20% | Cost Performance Index (CPI) = Earned Value / Actual Cost. Score is scaled linearly: CPI ≥ 1.0 = 100, CPI 0.5 = 0. | Planned budget, actual cost, % complete |
| **Milestone Health** | 20% | Schedule Performance Index (SPI) = Earned Value / Planned Value, combined with the % of milestones hit on time. | Milestone rows, EV/PV |
| **Blockers & Issues** | 15% | Σ(Severity Weight × Age in Days). Normalized and inverted so fewer/younger blockers = higher score. Critical=8, High=4, Medium=2, Low=1. | Blocker descriptions, severity, created/resolved dates |
| **Stakeholder Sentiment** | 15% | LLM classifies each free-text status entry as Positive (100), Neutral (60), or Negative (20). Averages the classified sentiment. | Status notes, comments, updates |

---

## 2. Graceful Degradation Strategy

Project data is often messy or incomplete. The system handles missing data gracefully:

- If a signal's required columns cannot be mapped (e.g., no budget data), that signal is marked **Unavailable**.
- The weight of the missing signal is **redistributed proportionally** across the remaining available signals.
- A **Confidence Score (0-100%)** is generated based on how many of the 5 signals had usable data.
- The LLM explanation explicitly notes which signals were skipped to maintain transparency with stakeholders.

---

## 3. Thresholds and Overrides

The weighted score (0-100) is translated into a RAG status using thresholds. However, certain severe conditions will immediately override the score.

### Green 🟢
- **Condition:** Weighted Score ≥ 80
- **Constraint:** Must not have any Critical blockers unresolved for > 7 days.

### Amber 🟡
- **Condition:** Weighted Score between 60 and 79.
- **Override Trigger:** Regardless of score, if there is a Medium or High severity blocker unresolved, the status cannot be better than Amber.
- **Fallback:** If *zero* signal data is available, the system defaults to Amber with 0% confidence.

### Red 🔴
- **Condition:** Weighted Score < 60
- **Critical Override 1:** Cost Performance Index (CPI) < 0.8
- **Critical Override 2:** Schedule Performance Index (SPI) < 0.8
- **Critical Override 3:** Any "Critical" severity blocker unresolved for more than 7 days.
