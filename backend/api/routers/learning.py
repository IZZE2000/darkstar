import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select

from backend.learning.backfill import BackfillEngine
from backend.learning.models import ConfigVersion, ExecutionLog, LearningDailyMetric, LearningRun, SlotObservation

if TYPE_CHECKING:
    from backend.learning.store import LearningStore

logger = logging.getLogger("darkstar.api.learning")

router = APIRouter(tags=["learning"])


def _get_learning_engine() -> Any:
    """Get the learning engine instance."""
    from backend.learning import get_learning_engine

    return get_learning_engine()


@router.get(
    "/api/learning/status",
    summary="Get Learning Status",
    description="Return learning engine status and metrics.",
)
async def learning_status() -> dict[str, Any]:
    """Return learning engine status and metrics."""
    try:
        engine = _get_learning_engine()
        # get_status is now async
        status = await engine.get_status()
        return cast("dict[str, Any]", status)
    except Exception as e:
        logger.exception("Failed to get learning status")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/api/learning/history",
    summary="Get Learning History",
    description="Return learning engine run history.",
)
async def learning_history(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    """Return learning engine run history using Async SQLAlchemy."""
    try:
        engine = _get_learning_engine()
        store: LearningStore = engine.store

        async with store.AsyncSession() as session:
            stmt = select(LearningRun).order_by(desc(LearningRun.started_at)).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            results = []
            for run in rows:
                results.append(
                    {
                        "id": run.id,
                        "run_date": run.started_at.isoformat() if run.started_at else None,
                        "status": run.status,
                        "metrics": json.loads(run.result_metrics_json)
                        if run.result_metrics_json
                        else None,
                        "config_changes": json.loads(run.params_json) if run.params_json else None,
                    }
                )
            return {"runs": results, "count": len(results)}
    except Exception as e:
        logger.warning(f"Failed to get learning history (DB may be uninitialized): {e}")
        return {"runs": [], "count": 0, "message": f"Learning history unavailable: {e!s}"}


@router.post(
    "/api/learning/train",
    summary="Trigger ML Training",
    description="Trigger manual ML model retraining now.",
)
async def learning_train() -> dict[str, str]:
    """Trigger ML model retraining manually."""
    try:
        from ml.train import train_models

        # Offload to thread since train_models is heavy/sync
        await asyncio.to_thread(train_models)
        return {"status": "success", "message": "ML models retrained successfully"}
    except Exception as e:
        logger.exception("Failed to train models")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/api/learning/run",
    summary="Trigger Learning Run",
    description="Trigger learning orchestration manually.",
)
async def learning_run() -> dict[str, Any]:
    """Trigger learning orchestration manually."""
    try:
        from backend.learning.reflex import AuroraReflex
        from ml.train import train_models

        # NOTE: Reflex and ML Training are CPU-intensive and sync.
        # We still use to_thread for these.
        def _run_heavy_tasks():
            # Run Reflex
            reflex = AuroraReflex()
            report = reflex.run(dry_run=False)

            # Run Training
            train_models(days_back=90, min_samples=100)
            return report

        # Offload to thread to avoid blocking event loop
        reflex_report = await asyncio.to_thread(_run_heavy_tasks)

        return {
            "status": "success",
            "reflex_report": reflex_report,
            "message": "Learning run completed (Reflex + Train)",
        }
    except Exception as e:
        logger.exception("Failed to run learning")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/api/learning/loops",
    summary="Get Learning Loops",
    description="Get status of individual learning loops.",
)
async def learning_loops() -> dict[str, Any]:
    """Get status of individual learning loops (Mocked as real-time status)."""
    # Note: learning_loops table noted in legacy code was not found in schema.
    # Defining known loops for UI compatibility.
    known_loops = ["pv_forecast", "load_forecast", "s_index", "arbitrage"]
    result = {}
    for loop in known_loops:
        result[loop] = {"status": "active", "last_run": None, "error": None}

    return {"loops": result}


@router.get(
    "/api/learning/daily_metrics",
    summary="Get Daily Metrics",
    description="Get latest daily metrics from learning engine.",
)
async def learning_daily_metrics():
    """Get latest daily metrics from learning engine using Async SQLAlchemy."""
    try:
        engine = _get_learning_engine()
        store: LearningStore = engine.store

        async with store.AsyncSession() as session:
            stmt = select(LearningDailyMetric).order_by(desc(LearningDailyMetric.date)).limit(1)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if not row:
                return {"message": "No daily metrics yet"}

            return {
                "date": row.date,
                "pv_error_mean_abs_kwh": row.pv_error_mean_abs_kwh,
                "load_error_mean_abs_kwh": row.load_error_mean_abs_kwh,
                "s_index_base_factor": row.s_index_base_factor,
            }
    except Exception as e:
        logger.warning(f"Failed to get daily metrics: {e}")
        return {"message": f"Daily metrics unavailable: {e!s}"}


@router.get(
    "/api/learning/changes",
    summary="Get Learning Changes",
    description="Return recent learning configuration changes.",
)
async def learning_changes(limit: int = Query(10, ge=1, le=50)) -> dict[str, Any]:
    """Return recent learning configuration changes using Async SQLAlchemy."""
    try:
        engine = _get_learning_engine()
        store: LearningStore = engine.store

        async with store.AsyncSession() as session:
            stmt = select(ConfigVersion).order_by(desc(ConfigVersion.created_at)).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            changes = []
            for change in rows:
                changes.append(
                    {
                        "id": change.id,
                        "created_at": change.created_at.isoformat() if change.created_at else None,
                        "reason": change.reason,
                        "applied": change.applied,
                        "metrics": json.loads(change.metrics_json) if change.metrics_json else None,
                    }
                )
            return {"changes": changes}
    except Exception as e:
        logger.warning(f"Failed to get learning changes: {e}")
        return {"changes": [], "message": f"Learning changes unavailable: {e!s}"}


@router.post(
    "/api/learning/record_observation",
    summary="Record Observation",
    description="Trigger observation recording from current system state.",
)
async def record_observation() -> dict[str, str]:
    """Trigger observation recording from current system state."""
    try:
        from backend.recorder import record_observation_from_current_state

        # record_observation_from_current_state is now async
        await record_observation_from_current_state()
        return {"status": "success", "message": "Observation recorded"}
    except Exception as e:
        logger.exception("Failed to record observation")
        raise HTTPException(status_code=500, detail=str(e)) from e


class GapInfo(BaseModel):
    start_time: str
    end_time: str
    missing_slots: int


class BackfillStatus(BaseModel):
    status: str
    message: str


@router.get(
    "/api/learning/gaps",
    summary="Detect Data Gaps",
    response_model=list[GapInfo],
)
async def get_gaps(days: int = 10):
    """Detect missing observation slots in the last N days."""
    try:
        engine = _get_learning_engine()
        store: LearningStore = engine.store
        tz = store.timezone
        now = datetime.now(tz)
        start_time = now - timedelta(days=days)

        # Truncate to 15-minute boundaries
        start_time = start_time.replace(
            minute=start_time.minute - (start_time.minute % 15), second=0, microsecond=0
        )

        logger.info(f"🔍 Gap detection: now={now}, start_time={start_time}, days={days}")

        # Generate expected slots with consistent timezone format
        expected_slots = set()
        current = start_time
        while current < now:
            # Use same format as database: astimezone + isoformat
            expected_slots.add(current.astimezone(tz).isoformat())
            current += timedelta(minutes=15)

        logger.info(f"📊 Generated {len(expected_slots)} expected slots")
        logger.info(f"📊 Sample expected slots: {list(sorted(expected_slots))[:5]}")

        # Query existing slots
        existing_slots = set()
        async with store.AsyncSession() as session:
            stmt = select(ExecutionLog.slot_start).where(
                ExecutionLog.slot_start >= start_time.astimezone(tz).isoformat(),
                ExecutionLog.slot_start < now.astimezone(tz).isoformat()
            )
            result = await session.execute(stmt)
            for row in result.scalars():
                existing_slots.add(row)

        logger.info(f"📊 Found {len(existing_slots)} existing slots in DB")
        logger.info(f"📊 Sample existing slots: {list(sorted(existing_slots))[:5]}")

        # DEBUG: Check What Slots Exist for Today
        today_str = now.strftime('%Y-%m-%d')
        today_slots = [slot for slot in existing_slots if slot.startswith(today_str)]
        logger.info(f"📊 Today's slots ({len(today_slots)}): {sorted(today_slots)}")

        expected_today = [slot for slot in expected_slots if slot.startswith(today_str)]
        logger.info(f"📊 Expected today ({len(expected_today)}): {sorted(expected_today)[:10]}")

        # Find missing
        missing = sorted(expected_slots - existing_slots)

        logger.info(f"📊 Missing slots: {len(missing)}")
        if missing:
            logger.info(f"📊 First 5 missing: {missing[:5]}")

        if not missing:
            logger.info("✅ No gaps found - returning empty array")
            return []

        # Group into contiguous ranges
        gaps = []
        current_gap_start = missing[0]
        current_gap_end = missing[0]
        count = 1

        for i in range(1, len(missing)):
            curr_dt = datetime.fromisoformat(missing[i])
            prev_dt = datetime.fromisoformat(missing[i - 1])

            if (curr_dt - prev_dt) == timedelta(minutes=15):
                current_gap_end = missing[i]
                count += 1
            else:
                gaps.append(
                    GapInfo(
                        start_time=current_gap_start,
                        end_time=current_gap_end,
                        missing_slots=count,
                    )
                )
                current_gap_start = missing[i]
                current_gap_end = missing[i]
                count = 1

        # Append last gap
        gaps.append(
            GapInfo(
                start_time=current_gap_start,
                end_time=current_gap_end,
                missing_slots=count,
            )
        )

        return gaps

    except Exception as e:
        logger.exception("Failed to detect gaps")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _run_backfill_task():
    """Background task wrapper for backfill."""
    try:
        # Use existing engine if possible, or create new one
        # Because this is a long running task, better to instantiate fresh to avoid binding issues?
        # But instructions said "Reuse BackfillEngine".
        engine = BackfillEngine()
        await engine.run()
    except Exception:
        logger.exception("Background backfill failed")


@router.post(
    "/api/learning/backfill",
    summary="Trigger Backfill",
    response_model=BackfillStatus,
)
async def trigger_backfill(background_tasks: BackgroundTasks):
    """Trigger the backfill process in the background."""
    background_tasks.add_task(_run_backfill_task)
    return BackfillStatus(status="started", message="Backfill process started in background")
