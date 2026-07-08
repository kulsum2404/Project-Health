"""
Monthly synthesis endpoints — trigger synthesis, download pptx.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.config import get_settings
from app.main import get_session
from app.models.models import (
    MonthlyReport,
    MonthlyReportResponse,
    Project,
    WeeklySnapshot,
)
from app.synthesis.ppt_generator import generate_monthly_pptx
from app.synthesis.trend_synthesizer import synthesize_trends

logger = logging.getLogger(__name__)
router = APIRouter(tags=["monthly"])


@router.post("/monthly/synthesize", response_model=MonthlyReportResponse)
async def trigger_monthly_synthesis(
    portfolio_name: str = "Project Portfolio",
    session: Session = Depends(get_session),
) -> MonthlyReportResponse:
    """
    Pull all projects' snapshot history, run cross-project trend synthesis,
    and generate a PPTX executive presentation.
    """
    now = datetime.utcnow()
    period_start = now - timedelta(days=30)

    # Get all active projects
    projects = session.exec(
        select(Project).where(Project.is_active == True)  # noqa: E712
    ).all()

    if not projects:
        raise HTTPException(status_code=404, detail="No active projects found")

    # Collect snapshot history for each project
    project_snapshots: dict[str, list[dict]] = {}
    rag_counts = {"green": 0, "amber": 0, "red": 0}

    for project in projects:
        snapshots = session.exec(
            select(WeeklySnapshot)
            .where(WeeklySnapshot.project_id == project.id)
            .order_by(WeeklySnapshot.created_at.asc())  # type: ignore
        ).all()

        if snapshots:
            latest = snapshots[-1]
            rag_counts[latest.rag_status] = rag_counts.get(latest.rag_status, 0) + 1

            project_snapshots[project.name] = [
                {
                    "date": s.created_at.isoformat(),
                    "rag_status": s.rag_status,
                    "weighted_score": s.weighted_score,
                    "confidence": s.confidence,
                    "schedule_score": s.schedule_score,
                    "budget_score": s.budget_score,
                    "milestone_score": s.milestone_score,
                    "blocker_score": s.blocker_score,
                    "sentiment_score": s.sentiment_score,
                    "signals_used": s.signals_used,
                    "signals_skipped": s.signals_skipped,
                    "signal_details": s.signal_details,
                }
                for s in snapshots
            ]

    # Run cross-project trend synthesis
    try:
        synthesis_data = await synthesize_trends(
            project_snapshots=project_snapshots,
            period_start=period_start,
            period_end=now,
            portfolio_name=portfolio_name,
        )
    except Exception as e:
        logger.error("Trend synthesis failed: %s", e)
        synthesis_data = {
            "risks": ["Synthesis unavailable — LLM error"],
            "wins": [],
            "recommendations": ["Re-run synthesis when LLM service is available"],
            "trends": [],
            "error": str(e),
        }

    # Generate PPTX
    settings = get_settings()
    pptx_filename = f"monthly_report_{now.strftime('%Y%m%d_%H%M%S')}.pptx"
    pptx_path = str(settings.reports_path / pptx_filename)

    try:
        generate_monthly_pptx(
            output_path=pptx_path,
            portfolio_name=portfolio_name,
            period_start=period_start,
            period_end=now,
            project_snapshots=project_snapshots,
            synthesis_data=synthesis_data,
            rag_counts=rag_counts,
        )
    except Exception as e:
        logger.error("PPTX generation failed: %s", e)
        pptx_path = ""

    # Persist report
    report = MonthlyReport(
        created_at=now,
        period_start=period_start,
        period_end=now,
        portfolio_name=portfolio_name,
        synthesis_data=synthesis_data,
        pptx_path=pptx_path,
        total_projects=len(projects),
        green_count=rag_counts.get("green", 0),
        amber_count=rag_counts.get("amber", 0),
        red_count=rag_counts.get("red", 0),
    )

    session.add(report)
    session.commit()
    session.refresh(report)

    logger.info("Monthly report generated: id=%d", report.id)

    return MonthlyReportResponse(
        id=report.id,  # type: ignore
        created_at=report.created_at,
        period_start=report.period_start,
        period_end=report.period_end,
        portfolio_name=report.portfolio_name,
        total_projects=report.total_projects,
        green_count=report.green_count,
        amber_count=report.amber_count,
        red_count=report.red_count,
        synthesis_data=report.synthesis_data,
        has_pptx=bool(report.pptx_path),
    )


@router.get("/monthly/{report_id}/download")
async def download_monthly_report(
    report_id: int,
    session: Session = Depends(get_session),
):
    """Download the generated PPTX file for a monthly report."""
    report = session.get(MonthlyReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Monthly report not found")

    if not report.pptx_path:
        raise HTTPException(status_code=404, detail="No PPTX file available for this report")

    pptx_file = Path(report.pptx_path)
    if not pptx_file.exists():
        raise HTTPException(status_code=404, detail="PPTX file not found on disk")

    return FileResponse(
        path=str(pptx_file),
        filename=pptx_file.name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.get("/monthly/reports", response_model=list[MonthlyReportResponse])
async def list_monthly_reports(
    limit: int = 12,
    session: Session = Depends(get_session),
) -> list[MonthlyReportResponse]:
    """List all monthly reports."""
    reports = session.exec(
        select(MonthlyReport)
        .order_by(MonthlyReport.created_at.desc())  # type: ignore
        .limit(limit)
    ).all()

    return [
        MonthlyReportResponse(
            id=r.id,  # type: ignore
            created_at=r.created_at,
            period_start=r.period_start,
            period_end=r.period_end,
            portfolio_name=r.portfolio_name,
            total_projects=r.total_projects,
            green_count=r.green_count,
            amber_count=r.amber_count,
            red_count=r.red_count,
            synthesis_data=r.synthesis_data,
            has_pptx=bool(r.pptx_path),
        )
        for r in reports
    ]
