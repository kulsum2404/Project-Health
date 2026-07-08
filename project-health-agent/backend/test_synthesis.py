import asyncio
from sqlmodel import Session, select
from app.main import get_session
from app.models.models import Project, WeeklySnapshot
from app.synthesis.trend_synthesizer import synthesize_trends
from app.synthesis.ppt_generator import generate_monthly_pptx
from datetime import datetime, timedelta

async def test_synthesis():
    session_gen = get_session()
    session = next(session_gen)
    
    projects = session.exec(select(Project)).all()
    print(f"Projects found: {len(projects)}")
    
    project_snapshots = {}
    rag_counts = {"green": 0, "amber": 0, "red": 0}
    for p in projects:
        snaps = session.exec(select(WeeklySnapshot).where(WeeklySnapshot.project_id == p.id)).all()
        if snaps:
            latest = snaps[-1]
            rag_counts[latest.rag_status] = rag_counts.get(latest.rag_status, 0) + 1
            project_snapshots[p.name] = [{
                "date": s.created_at.isoformat(),
                "rag_status": s.rag_status,
                "weighted_score": s.weighted_score,
                "confidence": s.confidence,
                "schedule_score": s.schedule_score,
                "budget_score": s.budget_score,
                "milestone_score": s.milestone_score,
                "blocker_score": s.blocker_score,
                "sentiment_score": s.sentiment_score,
            } for s in snaps]
            
    print(f"Snapshots collected for {len(project_snapshots)} projects")
    
    try:
        data = await synthesize_trends(
            project_snapshots=project_snapshots,
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            portfolio_name="Test"
        )
        print("Synthesis successful!")
        print(data)
        
        pptx_path = "test_output.pptx"
        try:
            generate_monthly_pptx(
                output_path=pptx_path,
                portfolio_name="Test Portfolio",
                period_start=datetime.utcnow() - timedelta(days=30),
                period_end=datetime.utcnow(),
                project_snapshots=project_snapshots,
                synthesis_data=data,
                rag_counts=rag_counts
            )
            print(f"PPTX generated at {pptx_path}")
        except Exception as e:
            print("PPTX generation error:", e)
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print("Synthesis error:", e)
        
if __name__ == "__main__":
    asyncio.run(test_synthesis())
