"""
API router for Aurora-based forecasting and Antares model parameters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pandas as pd
import pytz

from backend.learning import LearningEngine, get_learning_engine

# Lazy import for experimental simulation module (not included in production Docker)
if TYPE_CHECKING:
    from datetime import datetime

    from ml.simulation.dataset import AntaresSlotRecord


def _get_engine() -> LearningEngine:
    """Return the shared LearningEngine instance."""
    engine = get_learning_engine()
    # No need for isinstance check if type hint is enforced by get_learning_engine
    return cast("LearningEngine", engine)


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
    for row in df.to_dict("records"):
        base_pv = float(row.get("pv_forecast_kwh") or 0.0)
        base_load = float(row.get("base_load_forecast_kwh") or row.get("load_forecast_kwh") or 0.0)
        pv_corr = float(row.get("pv_correction_kwh") or 0.0)
        load_corr = float(row.get("load_correction_kwh") or 0.0)

        records.append(
            {
                "slot_start": row["slot_start"].isoformat(),
                "base": {"pv_kwh": base_pv, "load_kwh": base_load},
                "correction": {"pv_kwh": pv_corr, "load_kwh": load_corr},
                "final": {"pv_kwh": base_pv + pv_corr, "load_kwh": base_load + load_corr},
                "probabilistic": {
                    "pv_p10": (float(row.get("pv_p10")) if row.get("pv_p10") is not None else None),
                    "pv_p90": (float(row.get("pv_p90")) if row.get("pv_p90") is not None else None),
                    "load_p10": (
                        float(row.get("load_p10")) if row.get("load_p10") is not None else None
                    ),
                    "load_p90": (
                        float(row.get("load_p90")) if row.get("load_p90") is not None else None
                    ),
                },
                "temp_c": row.get("temp_c"),
                "forecast_version": row.get("forecast_version"),
            },
        )

    return records


def get_antares_slots(dataset_version: str = "v1") -> pd.DataFrame:
    """
    Return the Antares v1 simulation training dataset as a DataFrame.

    - Currently supports dataset_version=\"v1\" only.
    - Wraps `build_antares_training_dataset` and converts records to a stable
      tabular form for downstream training/analysis.

    Note: This function requires the ml.simulation module which is not
    included in production Docker builds.
    """
    # Lazy import - only available in development environment
    from ml.simulation.dataset import build_antares_training_dataset

    if dataset_version != "v1":
        raise ValueError(f"Unsupported dataset_version: {dataset_version}")

    records: list[AntaresSlotRecord] = build_antares_training_dataset()
    if not records:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for rec in records:
        rows.append(
            {
                "episode_id": rec.episode_id,
                "episode_date": rec.episode_date,
                "system_id": rec.system_id,
                "data_quality_status": rec.data_quality_status,
                "slot_start": rec.slot_start,
                "import_price_sek_kwh": rec.import_price_sek_kwh,
                "export_price_sek_kwh": rec.export_price_sek_kwh,
                "load_kwh": rec.load_kwh,
                "pv_kwh": rec.pv_kwh,
                "import_kwh": rec.import_kwh,
                "export_kwh": rec.export_kwh,
                "batt_charge_kwh": rec.batt_charge_kwh,
                "batt_discharge_kwh": rec.batt_discharge_kwh,
                "soc_start_percent": rec.soc_start_percent,
                "soc_end_percent": rec.soc_end_percent,
                "battery_masked": rec.battery_masked,
                "dataset_version": dataset_version,
            }
        )

    return pd.DataFrame(rows)
