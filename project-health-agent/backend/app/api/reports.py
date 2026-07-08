"""
Report endpoints — latest RAG report and historical snapshots.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.main import get_session
from app.models.models import (
    Blocker,
    Project,
    ReportResponse,
    SnapshotResponse,
    WeeklySnapshot,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["reports"])


@router.get("/projects/{project_id}/report", response_model=ReportResponse)
async def get_latest_report(
    project_id: int,
    session: Session = Depends(get_session),
) -> ReportResponse:
    """Get the latest RAG status + reasoning + confidence for a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    latest = session.exec(
        select(WeeklySnapshot)
        .where(WeeklySnapshot.project_id == project_id)
        .order_by(WeeklySnapshot.created_at.desc())  # type: ignore
    ).first()

    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No analysis snapshots found. Run /api/projects/{id}/analyze first.",
        )

    # Get blockers
    blockers = session.exec(
        select(Blocker)
        .where(Blocker.project_id == project_id)
        .where(Blocker.is_resolved == False)  # noqa: E712
    ).all()

    blocker_data = [
        {
            "id": b.id,
            "description": b.description,
            "severity": b.severity,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "age_days": b.age_days,
        }
        for b in blockers
    ]

    snapshot_response = SnapshotResponse(
        id=latest.id,  # type: ignore
        project_id=latest.project_id,
        created_at=latest.created_at,
        rag_status=latest.rag_status,
        weighted_score=latest.weighted_score,
        confidence=latest.confidence,
        schedule_score=latest.schedule_score,
        budget_score=latest.budget_score,
        milestone_score=latest.milestone_score,
        blocker_score=latest.blocker_score,
        sentiment_score=latest.sentiment_score,
        signal_details=latest.signal_details,
        signals_used=latest.signals_used,
        signals_skipped=latest.signals_skipped,
        reasoning=latest.reasoning,
    )

    return ReportResponse(
        project_id=project_id,
        project_name=project.name,
        snapshot=snapshot_response,
        blockers=blocker_data,
    )


@router.get("/projects/{project_id}/history", response_model=list[SnapshotResponse])
async def get_project_history(
    project_id: int,
    limit: int = 52,
    session: Session = Depends(get_session),
) -> list[SnapshotResponse]:
    """Get time series of snapshots for trend charts."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    snapshots = session.exec(
        select(WeeklySnapshot)
        .where(WeeklySnapshot.project_id == project_id)
        .order_by(WeeklySnapshot.created_at.asc())  # type: ignore
        .limit(limit)
    ).all()

    return [
        SnapshotResponse(
            id=s.id,  # type: ignore
            project_id=s.project_id,
            created_at=s.created_at,
            rag_status=s.rag_status,
            weighted_score=s.weighted_score,
            confidence=s.confidence,
            schedule_score=s.schedule_score,
            budget_score=s.budget_score,
            milestone_score=s.milestone_score,
            blocker_score=s.blocker_score,
            sentiment_score=s.sentiment_score,
            signal_details=s.signal_details,
            signals_used=s.signals_used,
            signals_skipped=s.signals_skipped,
            reasoning=s.reasoning,
        )
        for s in snapshots
    ]
