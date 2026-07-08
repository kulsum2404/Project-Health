"""
Project endpoints — upload xlsx, list/get projects, trigger analysis.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from app.config import get_settings
from app.ingestion.loader import get_dataframe_from_project_data, load_xlsx
from app.ingestion.schema_mapper import map_schema_heuristic, map_schema_with_llm, extract_project_metadata_with_llm
from app.main import get_session
from app.models.models import (
    Blocker,
    Project,
    ProjectResponse,
    ProjectUpdate,
    SnapshotResponse,
    UploadResponse,
    WeeklySnapshot,
)
from app.rag.classifier import classify_rag
from app.rag.reasoning import generate_reasoning, generate_signal_explanation
from app.signals.blockers import compute_blocker_signal
from app.signals.budget import compute_budget_signal
from app.signals.milestones import compute_milestone_signal
from app.signals.schedule import compute_schedule_signal
from app.signals.sentiment import compute_sentiment_signal

logger = logging.getLogger(__name__)
router = APIRouter(tags=["projects"])


@router.post("/projects/upload", response_model=UploadResponse)
async def upload_project(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> UploadResponse:
    """
    Upload an xlsx project plan file.
    Returns project_id + detected schema mapping.
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="File must be .xlsx or .xls")

    settings = get_settings()

    # Save file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_")
    save_path = settings.upload_path / f"{timestamp}_{safe_name}"

    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Load and parse
    try:
        project_data = load_xlsx(str(save_path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {e}")

    # Map schema
    try:
        mapping, log = await map_schema_with_llm(
            columns=project_data.columns,
            sample_rows=project_data.sample_rows,
        )
    except Exception:
        # Fall back to heuristic
        mapping, log = map_schema_heuristic(project_data.columns)

    # Extract metadata from all sheets using LLM
    try:
        metadata = await extract_project_metadata_with_llm(project_data.sheets)
        
        manager_name = metadata.get("manager_name") or "Unassigned"
        
        # Parse start and end dates from LLM string to datetime if valid
        start_date_str = metadata.get("start_date")
        end_date_str = metadata.get("end_date")
        
        start_date = pd.to_datetime(start_date_str, errors='coerce').to_pydatetime() if start_date_str else None
        if pd.isna(start_date): start_date = None
            
        end_date = pd.to_datetime(end_date_str, errors='coerce').to_pydatetime() if end_date_str else None
        if pd.isna(end_date): end_date = None
            
    except Exception as e:
        logger.error(f"Failed to extract metadata: {e}")
        manager_name = "Unassigned"
        start_date = None
        end_date = None

    # Create project record
    project = Project(
        name=project_data.project_name,
        description=f"Uploaded from {file.filename}",
        file_path=str(save_path),
        manager_name=manager_name,
        start_date=start_date,
        end_date=end_date,
        schema_mapping=mapping,
        mapping_log=log,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(project)
    session.commit()
    session.refresh(project)

    logger.info("Project created: id=%d, name=%s", project.id, project.name)

    return UploadResponse(
        project_id=project.id,  # type: ignore
        name=project.name,
        detected_mapping=mapping,
        mapping_log=log,
        message=f"Project '{project.name}' created successfully with {len(mapping)} mapped fields.",
    )


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    session: Session = Depends(get_session),
) -> list[ProjectResponse]:
    """List all projects with their latest RAG status."""
    projects = session.exec(select(Project).where(Project.is_active == True)).all()  # noqa: E712

    responses: list[ProjectResponse] = []
    for project in projects:
        # Get latest snapshot
        latest = session.exec(
            select(WeeklySnapshot)
            .where(WeeklySnapshot.project_id == project.id)
            .order_by(WeeklySnapshot.created_at.desc())  # type: ignore
        ).first()

        responses.append(ProjectResponse(
            id=project.id,  # type: ignore
            name=project.name,
            description=project.description,
            manager_name=project.manager_name,
            start_date=project.start_date,
            end_date=project.end_date,
            schema_mapping=project.schema_mapping,
            created_at=project.created_at,
            updated_at=project.updated_at,
            is_active=project.is_active,
            latest_rag_status=latest.rag_status if latest else None,
            latest_score=latest.weighted_score if latest else None,
            latest_confidence=latest.confidence if latest else None,
            latest_reasoning=latest.reasoning if latest else None,
        ))

    return responses


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> ProjectResponse:
    """Get a single project by ID."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    latest = session.exec(
        select(WeeklySnapshot)
        .where(WeeklySnapshot.project_id == project.id)
        .order_by(WeeklySnapshot.created_at.desc())  # type: ignore
    ).first()

    return ProjectResponse(
        id=project.id,  # type: ignore
        name=project.name,
        description=project.description,
        manager_name=project.manager_name,
        start_date=project.start_date,
        end_date=project.end_date,
        schema_mapping=project.schema_mapping,
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_active=project.is_active,
        latest_rag_status=latest.rag_status if latest else None,
        latest_score=latest.weighted_score if latest else None,
        latest_confidence=latest.confidence if latest else None,
        latest_reasoning=latest.reasoning if latest else None,
    )


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    update_data: ProjectUpdate,
    session: Session = Depends(get_session),
) -> ProjectResponse:
    """Update a project's name."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if update_data.name is not None:
        project.name = update_data.name
    if update_data.manager_name is not None:
        project.manager_name = update_data.manager_name
        
    project.updated_at = datetime.utcnow()
    
    session.add(project)
    session.commit()
    
    # We can just call get_project to return the full response
    return await get_project(project_id, session)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    session: Session = Depends(get_session),
):
    """Delete a project and its associated snapshots and blockers."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Cascading deletes are not strictly enforced in basic SQLite SQLModel without
    # explicit cascade configuration, so we manually delete associated records.
    snapshots = session.exec(select(WeeklySnapshot).where(WeeklySnapshot.project_id == project_id)).all()
    for snap in snapshots:
        session.delete(snap)
        
    blockers = session.exec(select(Blocker).where(Blocker.project_id == project_id)).all()
    for b in blockers:
        session.delete(b)

    session.delete(project)
    session.commit()
    return None


@router.post("/projects/{project_id}/analyze", response_model=SnapshotResponse)
async def analyze_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> SnapshotResponse:
    """
    Run signal extraction + RAG classification on a project.
    Persists a new WeeklySnapshot.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load project data
    try:
        project_data = load_xlsx(project.file_path)
        df = get_dataframe_from_project_data(project_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load project data: {e}")

    mapping = project.schema_mapping
    now = datetime.utcnow()

    # ── Run all signal extractors ──────────────────────────────────────
    schedule_signal = compute_schedule_signal(df, mapping, reference_date=now)
    budget_signal = compute_budget_signal(df, mapping)
    milestone_signal = compute_milestone_signal(df, mapping, reference_date=now)
    blocker_signal = compute_blocker_signal(df, mapping, reference_date=now)

    # Sentiment is async (uses LLM)
    sentiment_signal = await compute_sentiment_signal(df, mapping)

    signals = [schedule_signal, budget_signal, milestone_signal, blocker_signal, sentiment_signal]

    # ── Classify RAG ───────────────────────────────────────────────────
    rag_result = classify_rag(signals)

    # ── Generate LLM reasoning ────────────────────────────────────────
    try:
        reasoning = await generate_reasoning(rag_result, project.name)
    except Exception as e:
        logger.error("Reasoning generation failed: %s", e)
        reasoning = f"Reasoning unavailable: {e}"

    # ── Persist snapshot ───────────────────────────────────────────────
    signal_details: dict[str, Any] = {}
    for sig in signals:
        signal_details[sig.name] = {
            "score": sig.score,
            "available": sig.available,
            "details": sig.details,
            "reason": sig.reason,
        }

    snapshot = WeeklySnapshot(
        project_id=project_id,
        created_at=now,
        rag_status=rag_result.status.value,
        weighted_score=rag_result.weighted_score,
        confidence=rag_result.confidence,
        schedule_score=schedule_signal.score if schedule_signal.available else None,
        budget_score=budget_signal.score if budget_signal.available else None,
        milestone_score=milestone_signal.score if milestone_signal.available else None,
        blocker_score=blocker_signal.score if blocker_signal.available else None,
        sentiment_score=sentiment_signal.score if sentiment_signal.available else None,
        signal_details=signal_details,
        signals_used=rag_result.signals_used,
        signals_skipped=rag_result.signals_skipped,
        reasoning=reasoning,
    )

    session.add(snapshot)

    # Update project timestamp
    project.updated_at = now
    session.add(project)

    # Extract and persist blockers
    _persist_blockers(df, mapping, project_id, now, session)

    session.commit()
    session.refresh(snapshot)

    logger.info(
        "Analysis complete: project=%s, status=%s, score=%.1f",
        project.name, rag_result.status.value, rag_result.weighted_score,
    )

    return SnapshotResponse(
        id=snapshot.id,  # type: ignore
        project_id=snapshot.project_id,
        created_at=snapshot.created_at,
        rag_status=snapshot.rag_status,
        weighted_score=snapshot.weighted_score,
        confidence=snapshot.confidence,
        schedule_score=snapshot.schedule_score,
        budget_score=snapshot.budget_score,
        milestone_score=snapshot.milestone_score,
        blocker_score=snapshot.blocker_score,
        sentiment_score=snapshot.sentiment_score,
        signal_details=snapshot.signal_details,
        signals_used=snapshot.signals_used,
        signals_skipped=snapshot.signals_skipped,
        reasoning=snapshot.reasoning,
    )


@router.get("/projects/{project_id}/signal-explanation/{signal_name}")
async def get_signal_explanation_endpoint(
    project_id: int,
    signal_name: str,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """
    Generate an on-demand LLM explanation for a specific signal.
    Looks up the latest snapshot and generates an explanation.
    """
    valid_signals = {"schedule", "budget", "milestones", "blockers", "sentiment"}
    if signal_name not in valid_signals:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid signal name. Must be one of: {', '.join(valid_signals)}",
        )

    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    latest = session.exec(
        select(WeeklySnapshot)
        .where(WeeklySnapshot.project_id == project_id)
        .order_by(WeeklySnapshot.created_at.desc())  # type: ignore
    ).first()

    if not latest:
        raise HTTPException(status_code=404, detail="No analysis snapshots found")

    signal_data = latest.signal_details.get(signal_name)
    if not signal_data:
        raise HTTPException(
            status_code=404,
            detail=f"Signal '{signal_name}' not found in latest snapshot",
        )

    # Check if we already generated an explanation for this signal
    cached_explanation = signal_data.get("llm_explanation")
    if cached_explanation:
        return {"signal_name": signal_name, "explanation": cached_explanation}

    explanation = await generate_signal_explanation(
        signal_name=signal_name,
        signal_data=signal_data,
        overall_score=latest.weighted_score,
        rag_status=latest.rag_status,
        confidence=latest.confidence,
    )

    # Cache the explanation in the database to prevent redundant LLM calls
    # We create a shallow copy and re-assign to trigger SQLAlchemy JSON updates
    new_signal_details = dict(latest.signal_details)
    new_signal_details[signal_name]["llm_explanation"] = explanation
    latest.signal_details = new_signal_details
    session.add(latest)
    session.commit()

    return {"signal_name": signal_name, "explanation": explanation}


def _persist_blockers(
    df: pd.DataFrame,
    mapping: dict[str, str],
    project_id: int,
    now: datetime,
    session: Session,
) -> None:
    """Extract blockers from data and persist them."""
    blocker_col = None
    for candidate in ["blocker", "issue", "risk", "impediment"]:
        if candidate in mapping:
            mapped = mapping[candidate]
            if mapped in df.columns:
                blocker_col = mapped
                break
        if candidate in df.columns:
            blocker_col = candidate
            break

    if blocker_col is None:
        return

    severity_col = None
    for candidate in ["severity", "priority"]:
        if candidate in mapping:
            mapped = mapping[candidate]
            if mapped in df.columns:
                severity_col = mapped
                break
        if candidate in df.columns:
            severity_col = candidate
            break

    for _, row in df.iterrows():
        desc = row.get(blocker_col)
        if pd.isna(desc):
            continue
            
        desc_str = str(desc).strip()
        if desc_str == "":
            continue
            
        # Safeguard: Blockers are text descriptions. If the column was mismapped 
        # to a numeric column (like WBS or task ID), ignore it.
        if desc_str.replace('.', '', 1).isdigit() or len(desc_str) <= 2:
            continue

        severity = "medium"
        if severity_col and pd.notna(row.get(severity_col)):
            severity = str(row[severity_col]).lower().strip()

        blocker = Blocker(
            project_id=project_id,
            description=str(desc).strip(),
            severity=severity,
            created_at=now,
        )
        session.add(blocker)
