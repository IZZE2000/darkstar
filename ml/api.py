"""
API router for Aurora-based forecasting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd
import pytz

from backend.learning import LearningEngine, get_learning_engine
from ml.weather import calculate_per_array_pv, get_weather_series

if TYPE_CHECKING:
    from datetime import datetime


def _get_engine() -> LearningEngine:
    """Return the shared LearningEngine instance."""
    return get_learning_engine()


def _load_config() -> dict[str, Any]:
    """Load configuration from YAML file."""
    from pathlib import Path

    import yaml

    try:
        with Path("config.yaml").open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


async def get_forecast_slots(
    start_time: datetime,
    end_time: datetime,
    forecast_version: str,
    include_open_meteo: bool = True,
) -> list[dict[str, Any]]:
    """
    Async return forecast slots for the given time window and version using LearningStore.

    When include_open_meteo is True, also fetches Open-Meteo radiation data and calculates
    PV estimates using the formula: PV_kWh = (radiation_W_m2 / 1000) * capacity_kW * efficiency * 0.25h
    """
    engine = _get_engine()
    rows = await engine.store.get_forecasts_range(start_time, forecast_version)

    if not rows:
        return []

    df = pd.DataFrame(rows)
    df["slot_start"] = pd.to_datetime(df["slot_start"], utc=True)
    df = df[
        df["slot_start"] < end_time.astimezone(pytz.UTC if end_time.tzinfo else engine.timezone)
    ]

    if df.empty:
        return []

    df["slot_start"] = df["slot_start"].dt.tz_convert(engine.timezone)

    open_meteo_data: dict[str, dict[str, Any]] = {}
    if include_open_meteo:
        try:
            config = _load_config()
            solar_arrays = config.get("system", {}).get("solar_arrays", [])
            if solar_arrays:
                weather_df = get_weather_series(start_time, end_time, config=config)
                if not weather_df.empty and "shortwave_radiation_w_m2" in weather_df.columns:
                    for ts_idx, row_data in weather_df.iterrows():
                        ts_str = str(ts_idx)
                        radiation = row_data.get("shortwave_radiation_w_m2")
                        total_kwh, per_array = calculate_per_array_pv(radiation, solar_arrays)
                        open_meteo_data[ts_str] = {
                            "open_meteo_kwh": total_kwh,
                            "open_meteo_arrays": per_array if per_array else None,
                        }
        except Exception:
            pass

    records: list[dict[str, Any]] = []
    for raw_row in df.to_dict("records"):
        row: dict[str, Any] = raw_row  # type: ignore[assignment]
        base_pv = float(row.get("pv_forecast_kwh") or 0.0)
        base_load = float(row.get("base_load_forecast_kwh") or row.get("load_forecast_kwh") or 0.0)
        pv_corr = float(row.get("pv_correction_kwh") or 0.0)
        load_corr = float(row.get("load_correction_kwh") or 0.0)

        pv_p10_val: float | None = row.get("pv_p10")
        pv_p90_val: float | None = row.get("pv_p90")
        load_p10_val: float | None = row.get("load_p10")
        load_p90_val: float | None = row.get("load_p90")

        slot_ts = row["slot_start"]
        slot_ts_str = str(slot_ts) if not hasattr(slot_ts, "isoformat") else slot_ts.isoformat()  # type: ignore[union-attr]

        om_entry = open_meteo_data.get(slot_ts_str, {})

        records.append(
            {
                "slot_start": slot_ts_str,
                "base": {"pv_kwh": base_pv, "load_kwh": base_load},
                "correction": {"pv_kwh": pv_corr, "load_kwh": load_corr},
                "final": {"pv_kwh": base_pv + pv_corr, "load_kwh": base_load + load_corr},
                "probabilistic": {
                    "pv_p10": float(pv_p10_val) if pv_p10_val is not None else None,
                    "pv_p90": float(pv_p90_val) if pv_p90_val is not None else None,
                    "load_p10": float(load_p10_val) if load_p10_val is not None else None,
                    "load_p90": float(load_p90_val) if load_p90_val is not None else None,
                },
                "temp_c": row.get("temp_c"),
                "forecast_version": row.get("forecast_version"),
                "open_meteo_kwh": om_entry.get("open_meteo_kwh"),
                "open_meteo_arrays": om_entry.get("open_meteo_arrays"),
            },
        )

    return records
