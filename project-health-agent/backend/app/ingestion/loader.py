"""
XLSX loader — reads project plan spreadsheets and returns structured data.

Handles multi-sheet workbooks, validates structure, and produces
typed DataFrames for each data category.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SheetData(BaseModel):
    """Parsed data from a single spreadsheet sheet."""

    name: str
    columns: list[str]
    row_count: int
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)


class ProjectData(BaseModel):
    """Structured data extracted from a project plan xlsx."""

    file_path: str
    project_name: str
    sheets: list[SheetData]
    tasks_df_json: str = ""       # JSON-serialized tasks DataFrame
    budget_df_json: str = ""      # JSON-serialized budget data
    milestones_df_json: str = ""  # JSON-serialized milestones data
    blockers_df_json: str = ""    # JSON-serialized blockers data
    notes_df_json: str = ""       # JSON-serialized notes data
    all_data_json: str = ""       # JSON-serialized combined DataFrame
    columns: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean a DataFrame: strip whitespace, drop fully empty rows/cols."""
    # Drop columns that are entirely NaN
    df = df.dropna(axis=1, how="all")
    # Drop rows that are entirely NaN
    df = df.dropna(axis=0, how="all")
    # Strip whitespace from string columns
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()
        # Replace 'nan' strings back to NaN
        df[col] = df[col].replace("nan", pd.NA)
    return df


def _detect_header_row(df: pd.DataFrame) -> int:
    """
    Detect the header row in a DataFrame that may have title rows above the data.
    Returns the index of the likely header row.
    """
    # Heuristic: the header row is the first row where most cells are non-null
    # and contain text (not numbers)
    for i in range(min(5, len(df))):
        row = df.iloc[i]
        non_null = row.notna().sum()
        total = len(row)
        if non_null / total >= 0.5:
            # Check if cells look like headers (text, not dates/numbers)
            text_count = sum(
                1 for val in row
                if isinstance(val, str) and not val.replace(".", "").replace("-", "").isdigit()
            )
            if text_count / non_null >= 0.5:
                return i
    return 0


def load_xlsx(file_path: str | Path) -> ProjectData:
    """
    Load an xlsx file and return structured ProjectData.

    Handles:
    - Multi-sheet workbooks (merges relevant sheets)
    - Header detection for messy files
    - Empty sheets
    - Date parsing
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.suffix.lower() in (".xlsx", ".xls"):
        raise ValueError(f"Unsupported file format: {file_path.suffix}")

    logger.info("Loading xlsx: %s", file_path)

    # Read all sheets
    try:
        all_sheets = pd.read_excel(
            file_path,
            sheet_name=None,  # Read all sheets
            engine="openpyxl",
        )
    except Exception as e:
        logger.error("Failed to read xlsx: %s", e)
        raise ValueError(f"Failed to read Excel file: {e}") from e

    sheets_info: list[SheetData] = []
    all_dfs: list[pd.DataFrame] = []

    for sheet_name, df in all_sheets.items():
        if df.empty:
            logger.info("Skipping empty sheet: %s", sheet_name)
            continue

        # Clean the DataFrame
        df = _clean_dataframe(df)

        if df.empty:
            continue

        # Detect and fix header row if needed
        if df.columns.dtype == "int64" or all(
            str(c).startswith("Unnamed") for c in df.columns
        ):
            header_idx = _detect_header_row(df)
            if header_idx > 0:
                # Use the detected row as headers
                new_headers = df.iloc[header_idx].astype(str).tolist()
                df = df.iloc[header_idx + 1:].reset_index(drop=True)
                df.columns = new_headers
            elif header_idx == 0:
                new_headers = df.iloc[0].astype(str).tolist()
                df = df.iloc[1:].reset_index(drop=True)
                df.columns = new_headers

        # Clean again after header detection
        df = _clean_dataframe(df)

        if df.empty:
            continue

        # Sanitize column names
        df.columns = [
            str(col).strip().replace("\n", " ").replace("\r", "")
            for col in df.columns
        ]

        # Generate sample rows
        sample = df.head(5).to_dict(orient="records")

        sheets_info.append(SheetData(
            name=str(sheet_name),
            columns=list(df.columns),
            row_count=len(df),
            sample_rows=sample,
        ))

        # Tag with sheet name for multi-sheet tracking
        df["_sheet"] = str(sheet_name)
        all_dfs.append(df)

        logger.info(
            "Sheet '%s': %d rows, %d columns",
            sheet_name, len(df), len(df.columns),
        )

    if not all_dfs:
        raise ValueError("No valid data sheets found in the Excel file")

    # ── Pick the best "tasks" sheet ──────────────────────────────────
    # Heuristic: use the sheet with the most rows that has task-like columns
    TASK_INDICATOR_COLUMNS = {
        "task name", "task_name", "activity", "status", "% complete",
        "start date", "end date", "start", "finish", "duration",
        "baseline start", "baseline finish", "milestone", "phase/milestone",
    }

    best_df: pd.DataFrame | None = None
    best_score = -1

    for sdf in all_dfs:
        norm_cols = {c.lower().strip() for c in sdf.columns}
        task_col_matches = len(norm_cols & TASK_INDICATOR_COLUMNS)
        # Score = number of task-indicator columns * row count
        score = task_col_matches * len(sdf) if task_col_matches >= 2 else 0
        if score > best_score:
            best_score = score
            best_df = sdf

    if best_df is None or best_score == 0:
        # Fall back to the largest sheet
        best_df = max(all_dfs, key=len)

    combined_df = best_df.copy()

    # Clean out #UNPARSEABLE and similar Excel error values
    for col in combined_df.select_dtypes(include=["object"]).columns:
        combined_df[col] = combined_df[col].replace(
            to_replace=r"^#.*$", value=pd.NA, regex=True
        )

    # Extract project name from filename
    project_name = file_path.stem.replace("_", " ").replace("-", " ").title()

    # Prepare sample rows (from combined)
    sample_rows = combined_df.head(10).to_dict(orient="records")
    # Convert any non-serializable types
    for row in sample_rows:
        for key, val in row.items():
            if pd.isna(val):
                row[key] = None
            elif hasattr(val, "isoformat"):
                row[key] = val.isoformat()

    return ProjectData(
        file_path=str(file_path),
        project_name=project_name,
        sheets=sheets_info,
        all_data_json=combined_df.to_json(orient="records", date_format="iso", default_handler=str),
        columns=list(combined_df.columns),
        sample_rows=sample_rows,
    )


def get_dataframe_from_project_data(project_data: ProjectData) -> pd.DataFrame:
    """Reconstruct the combined DataFrame from ProjectData JSON."""
    if project_data.all_data_json:
        import io
        return pd.read_json(io.StringIO(project_data.all_data_json), orient="records")
    return pd.DataFrame()
