import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, cast

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, select

from backend.learning.models import ConfigVersion, LearningDailyMetric, LearningRun

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
        logger.exception("Failed to get learning history")
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
        logger.exception("Failed to get daily metrics")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        logger.exception("Failed to get learning changes")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
