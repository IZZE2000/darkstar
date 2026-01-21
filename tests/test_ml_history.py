import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from backend.learning.models import Base, LearningRun
from backend.learning.store import LearningStore


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test_learning.db")
    import pytz

    tz = pytz.timezone("Europe/Stockholm")
    store = LearningStore(db_path, tz)

    # Initialize schema for test
    async def init_db():
        async with store.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_db())
    return store


@pytest.mark.asyncio
async def test_log_learning_run_full(store):
    """Test logging a run with all new ARC11 columns."""
    start = datetime.utcnow() - timedelta(minutes=5)

    await store.log_learning_run(
        status="success",
        training_type="automatic",
        models_trained=["model1.lgb", "model2.lgb"],
        duration_seconds=120,
        partial_failure=False,
        started_at=start,
    )

    async with store.AsyncSession() as session:
        stmt = select(LearningRun).limit(1)
        result = await session.execute(stmt)
        run = result.scalar_one()

        assert run.status == "success"
        assert run.training_type == "automatic"
        assert "model1.lgb" in run.models_trained
        assert run.training_duration_seconds == 120
        assert run.partial_failure is False
        assert run.completed_at is not None


@pytest.mark.asyncio
async def test_cleanup_learning_runs(store):
    """Test that cleanup removes old records but keeps recent ones."""
    now = datetime.utcnow()
    old = now - timedelta(days=40)
    recent = now - timedelta(days=10)

    async with store.AsyncSession() as session:
        # Manually add records to bypass log_learning_run logic if needed,
        # but log_learning_run supports started_at
        pass

    await store.log_learning_run(status="old", started_at=old)
    await store.log_learning_run(status="recent", started_at=recent)

    # Cleanup runs older than 30 days
    deleted = await store.cleanup_learning_runs(days_back=30)
    assert deleted == 1

    async with store.AsyncSession() as session:
        stmt = select(func.count(LearningRun.id))
        count = await session.scalar(stmt)
        assert count == 1

        stmt_check = select(LearningRun).limit(1)
        res = await session.execute(stmt_check)
        run = res.scalar_one()
        assert run.status == "recent"


@pytest.mark.asyncio
async def test_partial_failure_logging(store):
    """Test logging a partial failure."""
    await store.log_learning_run(
        status="success",
        partial_failure=True,
        error_message="Some models failed but overall success",
    )

    async with store.AsyncSession() as session:
        run = await session.scalar(select(LearningRun))
        assert run.partial_failure is True
        assert "Some models failed" in run.error_message
