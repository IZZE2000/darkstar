"""
End-to-end pipeline for Aurora training and inference.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.learning import LearningEngine, get_learning_engine
from ml.forward import generate_forward_slots


def _get_engine() -> LearningEngine:
    engine: LearningEngine = get_learning_engine()
    return engine


async def run_inference(
    horizon_hours: int = 168,
    forecast_version: str = "aurora",
) -> dict[str, Any]:
    """
    Orchestrate Aurora base forecast and persist results.

    Steps:
        1. Generate base forecasts into slot_forecasts.
    """
    engine = _get_engine()
    tz = engine.timezone

    # Step 1: Base AURORA forecast for full horizon (S-index compatible).
    await generate_forward_slots(horizon_hours=horizon_hours, forecast_version=forecast_version)

    return {
        "status": "ok",
        "forecast_version": forecast_version,
        "horizon_hours": horizon_hours,
        "timestamp": datetime.now(tz).isoformat(),
    }


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(run_inference())
    print(result)
