"""
SQLModel schemas for the Project Health Agent.

Tables: Project, WeeklySnapshot, Blocker, MonthlyReport
Pydantic models: SignalResult, RagResult, RagStatus
"""

import enum
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlmodel import JSON, Column, Field as SQLField, Relationship, SQLModel


# ── Enums ──────────────────────────────────────────────────────────────────


class RagStatus(str, enum.Enum):
    """Red / Amber / Green health status."""

    RED = "red"
    AMBER = "amber"
    GREEN = "green"


class BlockerSeverity(str, enum.Enum):
    """Severity levels for project blockers."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── SQLModel Tables ───────────────────────────────────────────────────────


class Project(SQLModel, table=True):
    """A tracked project ingested from an xlsx file."""

    __tablename__ = "projects"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    name: str = SQLField(index=True)
    description: str = ""
    file_path: str = ""
    manager_name: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    schema_mapping: dict[str, Any] = SQLField(
        default_factory=dict, sa_column=Column(JSON)
    )
    mapping_log: list[dict[str, Any]] = SQLField(
        default_factory=list, sa_column=Column(JSON)
    )
    custom_weights: Optional[dict[str, float]] = SQLField(
        default_factory=dict, sa_column=Column(JSON)
    )
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    updated_at: datetime = SQLField(default_factory=datetime.utcnow)
    is_active: bool = True

    # Relationships
    snapshots: list["WeeklySnapshot"] = Relationship(back_populates="project")
    blockers: list["Blocker"] = Relationship(back_populates="project")


class WeeklySnapshot(SQLModel, table=True):
    """A point-in-time health snapshot for a project."""

    __tablename__ = "weekly_snapshots"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    project_id: int = SQLField(foreign_key="projects.id", index=True)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)

    # RAG classification
    rag_status: str = ""  # "red" | "amber" | "green"
    weighted_score: float = 0.0
    confidence: float = 0.0  # 0-1 reflecting data completeness

    # Individual signal scores (0-100 each)
    schedule_score: Optional[float] = None
    budget_score: Optional[float] = None
    milestone_score: Optional[float] = None
    blocker_score: Optional[float] = None
    sentiment_score: Optional[float] = None

    # Raw signal details for audit trail
    feedback_score: Optional[int] = 0
    signal_details: dict[str, Any] = SQLField(
        default_factory=dict, sa_column=Column(JSON)
    )
    signals_used: list[str] = SQLField(
        default_factory=list, sa_column=Column(JSON)
    )
    signals_skipped: list[str] = SQLField(
        default_factory=list, sa_column=Column(JSON)
    )

    # LLM-generated reasoning
    reasoning: str = ""

    # Per-signal one-liner summaries (generated alongside reasoning)
    signal_summaries: dict[str, str] = SQLField(
        default_factory=dict, sa_column=Column(JSON)
    )

    # User feedback on reasoning (+1 or -1)
    feedback_score: int = 0

    # Relationship
    project: Optional["Project"] = Relationship(back_populates="snapshots")


class Blocker(SQLModel, table=True):
    """A project blocker / issue extracted from the plan."""

    __tablename__ = "blockers"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    project_id: int = SQLField(foreign_key="projects.id", index=True)
    description: str = ""
    severity: str = "medium"  # low | medium | high | critical
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    is_resolved: bool = False
    age_days: int = 0

    # Relationship
    project: Optional["Project"] = Relationship(back_populates="blockers")


class MonthlyReport(SQLModel, table=True):
    """A generated monthly executive synthesis report."""

    __tablename__ = "monthly_reports"

    id: Optional[int] = SQLField(default=None, primary_key=True)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    period_start: datetime = SQLField(default_factory=datetime.utcnow)
    period_end: datetime = SQLField(default_factory=datetime.utcnow)
    portfolio_name: str = "Project Portfolio"

    # Synthesis results
    synthesis_data: dict[str, Any] = SQLField(
        default_factory=dict, sa_column=Column(JSON)
    )
    pptx_path: str = ""

    # Summary fields
    total_projects: int = 0
    green_count: int = 0
    amber_count: int = 0
    red_count: int = 0


# ── Pydantic Models (non-table) ──────────────────────────────────────────


class SignalResult(BaseModel):
    """Result from a single signal extractor."""

    name: str
    score: float = Field(ge=0, le=100, description="Score 0-100 (higher is healthier)")
    weight: float = Field(ge=0, le=1, description="Default weight for this signal")
    available: bool = True
    details: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class RagResult(BaseModel):
    """Complete RAG classification result."""

    status: RagStatus
    weighted_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    signals: list[SignalResult]
    signals_used: list[str]
    signals_skipped: list[str]
    override_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for threshold overrides (e.g. critical blocker)",
    )


# ── API Response Models ──────────────────────────────────────────────────


class ProjectResponse(BaseModel):
    """API response for a project."""

    id: int
    name: str
    description: str
    manager_name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    schema_mapping: dict[str, Any]
    custom_weights: Optional[dict[str, float]] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    is_active: bool
    latest_rag_status: Optional[str] = None
    latest_score: Optional[float] = None
    latest_confidence: Optional[float] = None
    latest_reasoning: Optional[str] = None


class ProjectUpdate(BaseModel):
    """API request for updating a project."""
    
    name: Optional[str] = None
    manager_name: Optional[str] = None
    custom_weights: Optional[dict[str, float]] = None


class UploadResponse(BaseModel):
    """API response after uploading a project xlsx."""

    project_id: int
    name: str
    detected_mapping: dict[str, Any]
    mapping_log: list[dict[str, Any]]
    message: str
    data_warnings: list[str] = Field(default_factory=list)


class SnapshotResponse(BaseModel):
    """API response for a weekly snapshot."""

    id: int
    project_id: int
    created_at: datetime
    rag_status: str
    weighted_score: float
    confidence: float
    schedule_score: Optional[float]
    budget_score: Optional[float]
    milestone_score: Optional[float]
    blocker_score: Optional[float]
    sentiment_score: Optional[float]
    signal_details: dict[str, Any]
    signals_used: list[str]
    signals_skipped: list[str]
    reasoning: str
    signal_summaries: dict[str, str] = {}
    feedback_score: Optional[int] = 0
    source_file: str = ""
    sheet_count: int = 0
    total_tasks: int = 0


class ReportResponse(BaseModel):
    """API response for the latest RAG report."""

    project_id: int
    project_name: str
    snapshot: SnapshotResponse
    blockers: list[dict[str, Any]]


class MonthlyReportResponse(BaseModel):
    """API response for a monthly synthesis report."""

    id: int
    created_at: datetime
    period_start: datetime
    period_end: datetime
    portfolio_name: str
    total_projects: int
    green_count: int
    amber_count: int
    red_count: int
    synthesis_data: dict[str, Any]
    has_pptx: bool
