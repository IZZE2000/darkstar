"""
Weather data fetching and processing for Aurora.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytz
import requests
import yaml

# Simple in-memory cache with TTL (5 minutes)
_weather_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_CACHE_TTL_SECONDS = 300.0  # 5 minutes


def _load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """Load configuration from YAML file."""
    with Path(config_path).open(encoding="utf-8") as handle:
        result: dict[str, Any] = yaml.safe_load(handle) or {}
        return result


def get_weather_series(
    start_time: datetime,
    end_time: datetime,
    config: dict[str, Any] | None = None,
    *,
    config_path: str = "config.yaml",
) -> pd.DataFrame:
    """
    Fetch hourly outdoor weather data from Open-Meteo for the given window.

    Returns a DataFrame indexed by timezone-aware datetimes in the planner
    timezone with some or all of the following float columns:
        - temp_c: 2m air temperature in °C
        - cloud_cover_pct: total cloud cover in percent
        - shortwave_radiation_w_m2: shortwave radiation

    This helper is best-effort and will return an empty DataFrame if the
    request fails or contains no usable data.
    """
    cfg: dict[str, Any] = config or _load_config(config_path)
    system_cfg: dict[str, Any] = cfg.get("system", {}) or {}
    loc_cfg: dict[str, Any] = system_cfg.get("location", {}) or {}

    latitude = float(loc_cfg.get("latitude", 59.3))
    longitude = float(loc_cfg.get("longitude", 18.1))
    timezone_name: str = cfg.get("timezone", "Europe/Stockholm")
    tz = pytz.timezone(timezone_name)

    start_local = start_time.astimezone(tz)
    end_local = end_time.astimezone(tz)
    start_date_obj = start_local.date()
    end_date_obj = end_local.date()
    today_local = datetime.now(tz).date()

    # --- Cache Lookup ---
    cache_key = f"{latitude:.2f}_{longitude:.2f}_{start_date_obj}_{end_date_obj}"
    now_ts = time.time()
    if cache_key in _weather_cache:
        cached_ts, cached_df = _weather_cache[cache_key]
        if now_ts - cached_ts < _CACHE_TTL_SECONDS:
            return cached_df.copy()

    try:
        hourly_params: list[str] = [
            "temperature_2m",
            "cloud_cover",
            "shortwave_radiation",
        ]
        hourly_param_str = ",".join(hourly_params)

        if end_date_obj <= today_local:
            url = "https://archive-api.open-meteo.com/v1/archive"
            # Open-Meteo archive API typically supports data up to yesterday.
            archive_end = min(end_date_obj, today_local - timedelta(days=1))
            if archive_end < start_date_obj:
                return pd.DataFrame(dtype="float64")
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date_obj.isoformat(),
                "end_date": archive_end.isoformat(),
                "hourly": hourly_param_str,
                "timezone": timezone_name,
            }
        else:
            url = "https://api.open-meteo.com/v1/forecast"
            days_ahead = max(1, (end_local.date() - today_local).days + 1)
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": hourly_param_str,
                "forecast_days": days_ahead,
                "timezone": timezone_name,
            }

        # Reduced timeout from 20s to 5s to fail fast
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()  # type: ignore[assignment]
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Warning: Failed to fetch weather data from Open-Meteo: {exc}")
        return pd.DataFrame(dtype="float64")

    hourly: dict[str, Any] = payload.get("hourly") or {}
    times: list[Any] = hourly.get("time") or []
    temps: list[Any] = hourly.get("temperature_2m") or []
    clouds: list[Any] = hourly.get("cloud_cover") or []
    sw_rad: list[Any] = hourly.get("shortwave_radiation") or []

    if not times:
        return pd.DataFrame(dtype="float64")

    dt_index = pd.to_datetime(times)
    dt_index = dt_index.tz_localize("UTC") if dt_index.tz is None else dt_index.tz_convert("UTC")
    dt_index = dt_index.tz_convert(tz)

    data: dict[str, list[float]] = {}
    if temps and len(temps) == len(times):
        data["temp_c"] = temps
    if clouds and len(clouds) == len(times):
        data["cloud_cover_pct"] = clouds
    if sw_rad and len(sw_rad) == len(times):
        data["shortwave_radiation_w_m2"] = sw_rad

    if not data:
        return pd.DataFrame(dtype="float64")

    df = pd.DataFrame(data, index=dt_index).astype("float64")

    # REV F67: Resample from hourly to 15-minute resolution via linear interpolation.
    # This ensures all slots (Bug #1) get weather data (radiation/temp/clouds).
    if not df.empty and len(df) > 1:
        # We resample BEFORE filtering to start/end so that boundary points
        # are used for interpolation of the edge slots.
        df = df.resample("15min").interpolate(method="linear")

    df = df[(df.index >= start_local) & (df.index < end_local)]

    # --- Cache Store ---
    _weather_cache[cache_key] = (time.time(), df.copy())

    return df


def get_weather_volatility(
    start_time: datetime,
    end_time: datetime,
    config: dict[str, Any] | None = None,
    *,
    config_path: str = "config.yaml",
) -> dict[str, float]:
    """
    Calculate normalized volatility scores for cloud cover and temperature.

    Volatility is defined as:
        min(1.0, standard_deviation / normalization_factor)
    where normalization_factor is 40.0 for cloud cover (percent) and
    5.0 for temperature (deg C).

    The function returns a dictionary:
        {
            "cloud_volatility": float,
            "temp_volatility": float,
        }
    with each value in the range [0.0, 1.0].
    """
    df = get_weather_series(start_time, end_time, config=config, config_path=config_path)

    if df.empty:
        return {"cloud_volatility": 0.0, "temp_volatility": 0.0}

    cloud_std = float(df["cloud_cover_pct"].std()) if "cloud_cover_pct" in df.columns else 0.0
    temp_std = float(df["temp_c"].std()) if "temp_c" in df.columns else 0.0

    cloud_norm = 20.0
    temp_norm = 5.0

    cloud_volatility = 0.0
    temp_volatility = 0.0

    if cloud_std > 0.0 and cloud_norm > 0.0:
        cloud_volatility = min(1.0, cloud_std / cloud_norm)

    if temp_std > 0.0 and temp_norm > 0.0:
        temp_volatility = min(1.0, temp_std / temp_norm)

    return {
        "cloud_volatility": float(cloud_volatility),
        "temp_volatility": float(temp_volatility),
    }


def get_temperature_series(
    start_time: datetime,
    end_time: datetime,
    config: dict[str, Any] | None = None,
    *,
    config_path: str = "config.yaml",
) -> pd.Series:
    """Compatibility wrapper returning only the temp_c series."""
    df = get_weather_series(start_time, end_time, config=config, config_path=config_path)
    if df.empty or "temp_c" not in df.columns:
        return pd.Series(dtype="float64")
    series = df["temp_c"].copy()
    series.name = "temp_c"
    return series


def calculate_pv_from_radiation(
    radiation_w_m2: float | None,
    capacity_kw: float,
    efficiency: float = 0.85,
    slot_hours: float = 0.25,
) -> float | None:
    """
    Calculate PV production estimate from shortwave radiation.

    Formula: PV_kWh = (radiation_W_m2 / 1000) * capacity_kW * efficiency * slot_hours

    Args:
        radiation_w_m2: Shortwave radiation in W/m² (from Open-Meteo)
        capacity_kw: Total DC peak power in kilowatts
        efficiency: System efficiency factor (default 0.85, accounts for inverter,
                    wiring, temperature losses)
        slot_hours: Duration of the time slot in hours (default 0.25 = 15 minutes)

    Returns:
        Estimated PV production in kWh, or None if radiation data is missing
    """
    if radiation_w_m2 is None or capacity_kw <= 0:
        return None

    irradiance_kw_m2 = radiation_w_m2 / 1000.0
    pv_kwh = irradiance_kw_m2 * capacity_kw * efficiency * slot_hours
    return round(pv_kwh, 4)


def calculate_per_array_pv(
    radiation_w_m2: float | None,
    solar_arrays: list[dict[str, Any]],
    efficiency: float = 0.85,
    slot_hours: float = 0.25,
) -> tuple[float | None, list[dict[str, float]]]:
    """
    Calculate PV estimates for each solar array and the sum.

    Args:
        radiation_w_m2: Shortwave radiation in W/m² (from Open-Meteo)
        solar_arrays: List of array configs with 'name' and 'kwp' keys
        efficiency: System efficiency factor (default 0.85)
        slot_hours: Duration of the time slot in hours (default 0.25)

    Returns:
        Tuple of (sum_kwh, per_array_list) where per_array_list contains
        dicts with 'name' and 'kwh' keys. Returns (None, []) if no data.
    """
    if radiation_w_m2 is None or not solar_arrays:
        return None, []

    per_array: list[dict[str, float]] = []
    total_kwh = 0.0
    has_valid_data = False

    for arr in solar_arrays:
        name = arr.get("name", "Unknown")
        kwp = float(arr.get("kwp", 0) or 0)
        if kwp <= 0:
            continue

        arr_kwh = calculate_pv_from_radiation(radiation_w_m2, kwp, efficiency, slot_hours)
        if arr_kwh is not None:
            per_array.append({"name": name, "kwh": arr_kwh})
            total_kwh += arr_kwh
            has_valid_data = True

    if not has_valid_data:
        return None, []

    return round(total_kwh, 4), per_array
