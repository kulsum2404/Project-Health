"""
Generate sample project plan xlsx files for testing.
Run: python -m sample_data.generate_sample
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


def generate_sample_project(
    name: str = "ERP Migration",
    num_tasks: int = 25,
    health: str = "mixed",  # "healthy", "mixed", "troubled"
) -> pd.DataFrame:
    """Generate a realistic project plan DataFrame."""
    random.seed(42)
    base_date = datetime(2025, 1, 6)  # Start of year
    tasks = []

    task_templates = [
        "Requirements Gathering", "Stakeholder Interviews", "System Analysis",
        "Architecture Design", "Database Design", "API Development",
        "Frontend Development", "Integration Testing", "User Acceptance Testing",
        "Data Migration Planning", "Data Migration Execution", "Training Materials",
        "Staff Training Sessions", "Go-Live Planning", "Go-Live Execution",
        "Post-Launch Support", "Performance Optimization", "Security Audit",
        "Documentation Update", "Vendor Coordination", "Infrastructure Setup",
        "Configuration Management", "Change Management", "Risk Assessment",
        "Quality Assurance Review",
    ]

    milestones = [
        "Phase 1 Complete", "Design Approval", "Development Complete",
        "UAT Sign-off", "Go-Live", "Project Closure",
    ]

    severities = ["low", "medium", "high", "critical"]
    statuses_pool = ["Not Started", "In Progress", "Complete", "On Hold"]

    sentiments = {
        "healthy": [
            "Good progress this week, all deliverables on track",
            "Team morale is high, ahead of schedule on key tasks",
            "Stakeholders expressed satisfaction with demo",
            "Risks being actively managed, no escalation needed",
            "Budget is under control, no concerns",
        ],
        "mixed": [
            "Some delays in vendor deliverables, being monitored",
            "Team is stretched thin across multiple projects",
            "Budget is slightly over forecast but manageable",
            "Key resource on leave, temporary coverage arranged",
            "Client requested scope change, evaluating impact",
        ],
        "troubled": [
            "Critical delay in API development, blocking downstream tasks",
            "Budget overrun of 30%, escalation meeting scheduled",
            "Key stakeholder expressed dissatisfaction with progress",
            "Vendor missed deadline for third time, considering alternatives",
            "Team burnout concerns, overtime for past 3 weeks",
        ],
    }

    for i in range(min(num_tasks, len(task_templates))):
        template = task_templates[i]
        start_offset = i * 5 + random.randint(0, 10)
        duration = random.randint(5, 20)

        planned_start = base_date + timedelta(days=start_offset)
        planned_end = planned_start + timedelta(days=duration)

        # Determine if task is complete/in-progress/not started
        now = datetime(2025, 6, 15)
        if planned_end < now - timedelta(days=30):
            status = "Complete"
        elif planned_start < now:
            status = random.choice(["In Progress", "Complete", "Complete"])
        else:
            status = "Not Started"

        # Add delays based on health
        actual_start = planned_start
        actual_end = None

        if status == "Complete":
            if health == "healthy":
                delay = random.randint(-2, 1)
            elif health == "mixed":
                delay = random.randint(-1, 5)
            else:
                delay = random.randint(2, 15)
            actual_end = planned_end + timedelta(days=delay)
            actual_start = planned_start + timedelta(days=max(0, random.randint(-1, delay // 2)))

        # Budget
        planned_cost = random.randint(5000, 50000)
        if health == "healthy":
            actual_cost = planned_cost * random.uniform(0.8, 1.0)
        elif health == "mixed":
            actual_cost = planned_cost * random.uniform(0.9, 1.15)
        else:
            actual_cost = planned_cost * random.uniform(1.1, 1.5)

        pct_complete = 100 if status == "Complete" else (
            random.randint(20, 80) if status == "In Progress" else 0
        )
        earned_value = planned_cost * (pct_complete / 100)

        is_critical = "Yes" if i % 4 == 0 else "No"
        is_milestone = "Yes" if template in milestones else "No"

        # Blockers
        blocker = ""
        blocker_severity = ""
        if health == "troubled" and random.random() < 0.3:
            blocker = random.choice([
                "Blocked by vendor delay",
                "Resource unavailable",
                "Dependency on external API not met",
                "Critical bug in integration layer",
                "Waiting for client approval",
            ])
            blocker_severity = random.choice(["high", "critical"])
        elif health == "mixed" and random.random() < 0.15:
            blocker = random.choice([
                "Minor dependency delay",
                "Waiting for environment setup",
                "Pending design review",
            ])
            blocker_severity = random.choice(["low", "medium"])

        notes = random.choice(sentiments.get(health, sentiments["mixed"]))

        tasks.append({
            "Task Name": template,
            "Planned Start": planned_start.strftime("%Y-%m-%d"),
            "Planned End": planned_end.strftime("%Y-%m-%d"),
            "Actual Start": actual_start.strftime("%Y-%m-%d") if actual_start and status != "Not Started" else "",
            "Actual End": actual_end.strftime("%Y-%m-%d") if actual_end else "",
            "Status": status,
            "% Complete": pct_complete,
            "Is Critical": is_critical,
            "Is Milestone": is_milestone,
            "Planned Budget": planned_cost,
            "Actual Cost": round(actual_cost, 2) if status != "Not Started" else 0,
            "Earned Value": round(earned_value, 2),
            "Planned Value": planned_cost,
            "Blocker": blocker,
            "Severity": blocker_severity,
            "Notes": notes,
        })

    # Add milestone rows
    for j, ms in enumerate(milestones[:4]):
        ms_date = base_date + timedelta(days=(j + 1) * 30)
        now = datetime(2025, 6, 15)
        ms_status = "Complete" if ms_date < now - timedelta(days=10) else "In Progress"

        tasks.append({
            "Task Name": ms,
            "Planned Start": "",
            "Planned End": ms_date.strftime("%Y-%m-%d"),
            "Actual Start": "",
            "Actual End": (ms_date + timedelta(days=random.randint(-2, 5))).strftime("%Y-%m-%d") if ms_status == "Complete" else "",
            "Status": ms_status,
            "% Complete": 100 if ms_status == "Complete" else random.randint(50, 90),
            "Is Critical": "Yes",
            "Is Milestone": "Yes",
            "Planned Budget": 0,
            "Actual Cost": 0,
            "Earned Value": 0,
            "Planned Value": 0,
            "Blocker": "",
            "Severity": "",
            "Notes": f"Milestone: {ms}",
        })

    return pd.DataFrame(tasks)


def create_sample_files() -> None:
    """Create sample xlsx files in the sample_data directory."""
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)

    projects = [
        ("ERP_Migration_Project", "healthy"),
        ("Cloud_Infrastructure_Upgrade", "mixed"),
        ("CRM_Implementation", "troubled"),
    ]

    for filename, health in projects:
        df = generate_sample_project(name=filename.replace("_", " "), health=health)
        filepath = output_dir / f"{filename}.xlsx"
        df.to_excel(filepath, index=False, engine="openpyxl")
        print(f"Created: {filepath} ({len(df)} rows)")


if __name__ == "__main__":
    create_sample_files()
