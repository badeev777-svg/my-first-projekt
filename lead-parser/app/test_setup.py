import asyncio
from app.database import init_db, SessionLocal, Lead, Status
from datetime import datetime, timezone, timedelta

async def create_test_data():
    await init_db(demo=False)
    
    async with SessionLocal() as session:
        # Create some test leads
        test_leads = [
            Lead(
                source="fl",
                source_url="https://test1.com",
                title="Test Lead 1",
                text="Test description",
                budget=100000,
                status=Status.new,
                created_at=datetime.now(timezone.utc),
                relevance_score=85,
                tags="web,design"
            ),
            Lead(
                source="habr",
                source_url="https://test2.com",
                title="Test Lead 2",
                text="Test description",
                budget=50000,
                status=Status.viewed,
                created_at=datetime.now(timezone.utc) - timedelta(days=1),
                relevance_score=92,
                tags="backend"
            ),
            Lead(
                source="kwork",
                source_url="https://test3.com",
                title="Test Lead 3",
                text="Test description",
                budget=75000,
                status=Status.new,
                created_at=datetime.now(timezone.utc) - timedelta(days=3),
                relevance_score=78,
                tags="frontend"
            ),
        ]
        
        for lead in test_leads:
            session.add(lead)
        
        await session.commit()
        print("Test data created")

asyncio.run(create_test_data())
