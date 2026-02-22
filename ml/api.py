"""
API router for Aurora-based forecasting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd
import pytz

from backend.learning import LearningEngine, get_learning_engine

if TYPE_CHECKING:
    from datetime import datetime


def _get_engine() -> LearningEngine:
    """Return the shared LearningEngine instance."""
    return get_learning_engine()


async def get_forecast_slots(
    start_time: datetime,
    end_time: datetime,
    forecast_version: str,
) -> list[dict[str, Any]]:
    """
    Async return forecast slots for the given time window and version using LearningStore.
    """
    engine = _get_engine()
    rows = await engine.store.get_forecasts_range(start_time, forecast_version)

    if not rows:
        return []

    # Filter by end_time and format
    df = pd.DataFrame(rows)
    df["slot_start"] = pd.to_datetime(df["slot_start"], utc=True)
    df = df[
        df["slot_start"] < end_time.astimezone(pytz.UTC if end_time.tzinfo else engine.timezone)
    ]

    if df.empty:
        return []

    # Normalise to the planner timezone
    df["slot_start"] = df["slot_start"].dt.tz_convert(engine.timezone)

    records: list[dict[str, Any]] = []
    row_dict: dict[str, Any]
    for row_dict in df.to_dict("records"):  # type: ignore[assignment]
        base_pv = float(row_dict.get("pv_forecast_kwh") or 0.0)
        base_load = float(
            row_dict.get("base_load_forecast_kwh") or row_dict.get("load_forecast_kwh") or 0.0
        )
        pv_corr = float(row_dict.get("pv_correction_kwh") or 0.0)
        load_corr = float(row_dict.get("load_correction_kwh") or 0.0)

        # Handle probabilistic values safely
        pv_p10_val: float | None = row_dict.get("pv_p10")
        pv_p90_val: float | None = row_dict.get("pv_p90")
        load_p10_val: float | None = row_dict.get("load_p10")
        load_p90_val: float | None = row_dict.get("load_p90")

        records.append(
            {
                "slot_start": row_dict["slot_start"],
                "base": {"pv_kwh": base_pv, "load_kwh": base_load},
                "correction": {"pv_kwh": pv_corr, "load_kwh": load_corr},
                "final": {"pv_kwh": base_pv + pv_corr, "load_kwh": base_load + load_corr},
                "probabilistic": {
                    "pv_p10": float(pv_p10_val) if pv_p10_val is not None else None,
                    "pv_p90": float(pv_p90_val) if pv_p90_val is not None else None,
                    "load_p10": float(load_p10_val) if load_p10_val is not None else None,
                    "load_p90": float(load_p90_val) if load_p90_val is not None else None,
                },
                "temp_c": row_dict.get("temp_c"),
                "forecast_version": row_dict.get("forecast_version"),
            },
        )

    return records
