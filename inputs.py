import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import pytz
import yaml
from nordpool.elspot import Prices
from open_meteo_solar_forecast import OpenMeteoSolarForecast

from backend.core.cache import cache_sync
from backend.exceptions import PVForecastError
from backend.health import set_load_forecast_status
from ml.api import get_forecast_slots
from ml.weather import get_weather_volatility

logger = logging.getLogger("darkstar.inputs")


def load_home_assistant_config() -> dict[str, Any]:
    """Read Home Assistant configuration from secrets.yaml."""
    try:
        with Path("secrets.yaml").open() as file:
            raw_data: Any = yaml.safe_load(file)
            secrets: dict[str, Any] = (
                cast("dict[str, Any]", raw_data) if isinstance(raw_data, dict) else {}
            )
    except FileNotFoundError:
        return {}
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Warning: Could not load secrets.yaml: {exc}")
        return {}

    ha_config: Any = secrets.get("home_assistant")
    if not isinstance(ha_config, dict):
        return {}
    return cast("dict[str, Any]", ha_config)


def load_notifications_config() -> dict[str, Any]:
    """Read notification secrets (e.g., Discord webhook) from secrets.yaml."""
    try:
        with Path("secrets.yaml").open() as file:
            raw_data: Any = yaml.safe_load(file)
            secrets: dict[str, Any] = (
                cast("dict[str, Any]", raw_data) if isinstance(raw_data, dict) else {}
            )
    except FileNotFoundError:
        return {}
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Warning: Could not load secrets.yaml: {exc}")
        return {}

    notif_secrets: Any = secrets.get("notifications")
    if not isinstance(notif_secrets, dict):
        return {}
    return cast("dict[str, Any]", notif_secrets)


def make_ha_headers(token: str) -> dict[str, str]:
    """Return headers for Home Assistant REST calls."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def load_yaml(path: str) -> dict[str, Any]:
    try:
        with Path(path).open() as f:
            raw_data: Any = yaml.safe_load(f)
            return cast("dict[str, Any]", raw_data) if isinstance(raw_data, dict) else {}
    except FileNotFoundError:
        return {}


async def get_ha_entity_state(entity_id: str) -> dict[str, Any] | None:
    """Fetch a single entity state from Home Assistant asynchronously."""
    ha_config = load_home_assistant_config()
    url = ha_config.get("url")
    token = ha_config.get("token")

    if not url or not token or not entity_id:
        print(
            f"[get_ha_entity_state] Missing config: url={bool(url)}, token={bool(token)}, entity={entity_id}"
        )
        return None

    endpoint = f"{url.rstrip('/')}/api/states/{entity_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(endpoint, headers=make_ha_headers(token))
            response.raise_for_status()
            data = response.json()
            return data
    except Exception as exc:
        print(f"Warning: Could not fetch HA entity {entity_id}: {exc}")
        return None


async def get_ha_sensor_float(entity_id: str) -> float | None:
    """Return numeric state of HA sensor asynchronously."""
    state = await get_ha_entity_state(entity_id)
    if not state:
        return None

    raw_value = state.get("state")
    if raw_value in (None, "unknown", "unavailable"):
        return None

    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None


async def get_ha_sensor_kw_normalized(entity_id: str) -> float | None:
    """Return numeric state of HA sensor normalized to kW (scales W to kW)."""
    state_data = await get_ha_entity_state(entity_id)
    if not state_data:
        return None

    raw_value = state_data.get("state")
    if raw_value in (None, "unknown", "unavailable"):
        return None

    try:
        value = float(raw_value)
        # Check units
        attributes = state_data.get("attributes", {})
        unit = str(attributes.get("unit_of_measurement", "")).upper()
        if unit == "W":
            return value / 1000.0
        return value
    except (TypeError, ValueError):
        return None


def _normalize_energy_to_kwh(value: float, unit: str | None) -> float:
    """Normalize energy value to kWh based on Home Assistant unit_of_measurement.

    Handles common energy units: Wh, kWh, MWh with case-insensitive matching.
    Assumes kWh if no unit is specified (conservative fallback).

    Args:
        value: The raw numeric value from HA
        unit: The unit_of_measurement attribute from HA state

    Returns:
        Value normalized to kWh
    """
    if not unit:
        return value  # Assume kWh if no unit specified

    unit_clean = str(unit).upper().replace(" ", "_")

    if unit_clean in ("WH", "WATT_HOUR", "WATT_HOURS"):
        return value / 1000.0
    elif unit_clean in ("KWH", "KILOWATT_HOUR", "KILOWATT_HOURS"):
        return value
    elif unit_clean in ("MWH", "MEGAWATT_HOUR", "MEGAWATT_HOURS"):
        return value * 1000.0
    else:
        # Unknown unit - assume kWh (conservative)
        return value


async def get_ha_bool(entity_id: str) -> bool:
    """Return True if entity is 'on', 'true', 'armed', etc."""
    state = await get_ha_entity_state(entity_id)
    if not state:
        return False

    raw = str(state.get("state", "")).lower()
    # Common 'on' states in Home Assistant
    true_states = {"on", "true", "yes", "1", "armed_away", "armed_home", "armed_night"}
    is_true = raw in true_states
    if is_true and "vacation" in entity_id:
        print(f"DEBUG: Vacation mode detected TRUE. Raw state: '{raw}' from entity '{entity_id}'")
    return is_true


async def get_nordpool_data(config_path: str = "config.yaml") -> list[dict[str, Any]]:
    # --- Smart Cache Check ---
    cache_key = "nordpool_data"
    cached = cache_sync.get(cache_key)

    with Path(config_path).open() as f:
        config = yaml.safe_load(f)
    local_tz = pytz.timezone(config.get("timezone", "Europe/Stockholm"))
    now = datetime.now(local_tz)
    today = now.date()

    if cached and len(cached) > 0:
        first_slot = cached[0]["start_time"]
        first_slot_date = first_slot.date() if hasattr(first_slot, "date") else today
        has_tomorrow = any(
            s["start_time"].date() > today for s in cached if hasattr(s["start_time"], "date")
        )

        if first_slot_date < today:
            cached = None
        elif first_slot > now and now.hour < 23:
            current_slot_start = now.replace(
                minute=(now.minute // 15) * 15, second=0, microsecond=0
            )
            if first_slot > current_slot_start:
                cached = None

        if cached and now.hour >= 13 and not has_tomorrow:
            cached = None

        if cached:
            return cached

    nordpool_config = config.get("nordpool", {})
    price_area = nordpool_config.get("price_area", "SE4")
    currency = nordpool_config.get("currency", "SEK")
    resolution_minutes = nordpool_config.get("resolution_minutes", 60)

    import asyncio

    prices_client = Prices(currency=currency)

    try:
        # Fetch prices for today and tomorrow using to_thread
        raw_today = await asyncio.to_thread(
            prices_client.fetch, end_date=today, areas=[price_area], resolution=resolution_minutes
        )
        today_values = []
        if raw_today and "areas" in raw_today and price_area in raw_today["areas"]:
            today_raw = raw_today["areas"][price_area].get("values", [])
            today_values = [v for v in today_raw if v["start"].astimezone(local_tz).date() == today]

        tomorrow_values = []
        if now.hour >= 13:
            tomorrow = today + timedelta(days=1)
            raw_tomorrow = await asyncio.to_thread(
                prices_client.fetch,
                end_date=tomorrow,
                areas=[price_area],
                resolution=resolution_minutes,
            )
            if raw_tomorrow and "areas" in raw_tomorrow and price_area in raw_tomorrow["areas"]:
                all_raw = raw_tomorrow["areas"][price_area].get("values", [])
                tomorrow_values = [
                    v for v in all_raw if v["start"].astimezone(local_tz).date() == tomorrow
                ]

        all_entries = today_values + tomorrow_values

        if not all_entries:
            return []

        processed = _process_nordpool_data(all_entries, config)
        cache_sync.set(cache_key, processed, ttl_seconds=3600.0)
        return processed
    except Exception as exc:
        print(f"Warning: Failed to fetch Nordpool prices: {exc}")
        import traceback

        traceback.print_exc()
        return []


def calculate_import_export_prices(
    spot_price_mwh: float, config: dict[str, Any]
) -> tuple[float, float]:
    """
    Calculate import and export prices from spot price.

    Args:
        spot_price_mwh: Spot price in SEK/MWh
        config: Configuration dictionary

    Returns:
        tuple: (import_price_sek_kwh, export_price_sek_kwh)
    """
    pricing_config = config.get("pricing", {})
    vat_percent = pricing_config.get("vat_percent", 25.0)
    grid_transfer_fee_sek = pricing_config.get("grid_transfer_fee_sek", 0.2456)
    energy_tax_sek = pricing_config.get("energy_tax_sek", 0.439)

    spot_price_sek_kwh = spot_price_mwh / 1000.0
    export_price_sek_kwh = spot_price_sek_kwh

    import_price_sek_kwh = (spot_price_sek_kwh + grid_transfer_fee_sek + energy_tax_sek) * (
        1 + vat_percent / 100.0
    )

    return import_price_sek_kwh, export_price_sek_kwh


def _process_nordpool_data(
    all_entries: list[dict[str, Any]],
    config: dict[str, Any],
    today_values: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Process raw Nordpool API data into the required format.

    Args:
        all_entries: Combined list of raw price entries from today and tomorrow
        config: The full configuration dictionary, typed as dict[str, Any]

    Returns:
        list: Processed list of dictionaries with standardized format
    """
    result: list[dict[str, Any]] = []

    # Get local timezone
    local_tz = pytz.timezone(config.get("timezone", "Europe/Stockholm"))

    # Process the hourly data
    for i, entry in enumerate(all_entries):
        # Manual timezone conversion
        if today_values is not None and i < len(today_values):
            # Original entries - use their actual timestamps
            start_time = entry["start"].astimezone(local_tz)
            end_time = entry["end"].astimezone(local_tz)
        else:
            # Extended entries - calculate timestamps based on position
            if today_values is not None and len(today_values) > 0:
                base_start = today_values[0]["start"].astimezone(local_tz)
                slot_duration = today_values[0]["end"] - today_values[0]["start"]
                start_time = base_start + (slot_duration * i)
                end_time = start_time + slot_duration
            else:
                # Fallback if no today_values available
                start_time = entry["start"].astimezone(local_tz)
                end_time = entry["end"].astimezone(local_tz)

        import_price, export_price = calculate_import_export_prices(entry["value"], config)

        result.append(
            {
                "start_time": start_time,
                "end_time": end_time,
                "import_price_sek_kwh": import_price,
                "export_price_sek_kwh": export_price,
            }
        )

    # Sort by start time to ensure chronological order
    result.sort(key=lambda x: x["start_time"])

    return result


async def get_current_slot_prices(config: dict[str, Any]) -> dict[str, float] | None:
    """
    Fetch prices for the current 15-minute slot.
    """
    try:
        price_data = await get_nordpool_data()
        if not price_data:
            return None

        local_tz = pytz.timezone(config.get("timezone", "Europe/Stockholm"))
        now = datetime.now(local_tz)

        # Find the slot containing 'now'
        for slot in price_data:
            if slot["start_time"] <= now < slot["end_time"]:
                return {
                    "import_price_sek_kwh": slot["import_price_sek_kwh"],
                    "export_price_sek_kwh": slot["export_price_sek_kwh"],
                }
        return None
    except Exception as exc:
        print(f"Warning: Failed to get current slot prices: {exc}")
        return None


async def get_forecast_data(
    price_slots: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    """
    Generate PV and load forecasts based on price slots and configuration (Asynchronous).
    """
    forecasting_cfg = cast("dict[str, Any]", config.get("forecasting", {}) or {})
    active_version = str(forecasting_cfg.get("active_forecast_version", "baseline_7_day_avg"))

    if active_version == "aurora":
        return await _get_forecast_data_aurora(price_slots, config)
    else:
        return await _get_forecast_data_async(price_slots, config)


def _interpolate_small_gaps(
    db_slots: list[dict[str, Any]],
    max_gap_slots: int = 2,
) -> list[dict[str, Any]]:
    """
    Interpolate small gaps (1-2 slots) in forecast data.

    Only interpolates if gap is between valid (non-zero) data points.
    Never extrapolates - gaps at start or end are left as-is.
    """
    if not db_slots or len(db_slots) < 3:
        return db_slots

    result = list(db_slots)

    def is_valid_value(val: Any) -> bool:
        try:
            return float(val) > 0.001
        except (TypeError, ValueError):
            return False

    i = 0
    while i < len(result):
        slot = result[i]

        pv = slot.get("pv_forecast_kwh", 0.0)
        load = slot.get("load_forecast_kwh", slot.get("base_load_forecast_kwh", 0.0))

        if not is_valid_value(pv) or not is_valid_value(load):
            gap_start = i
            gap_end = i

            while gap_end < len(result) and (
                not is_valid_value(result[gap_end].get("pv_forecast_kwh", 0.0))
                or not is_valid_value(
                    result[gap_end].get(
                        "load_forecast_kwh",
                        result[gap_end].get("base_load_forecast_kwh", 0.0),
                    )
                )
            ):
                gap_end += 1

            gap_size = gap_end - gap_start

            if gap_size <= max_gap_slots and gap_start > 0 and gap_end < len(result):
                prev_pv = float(result[gap_start - 1].get("pv_forecast_kwh", 0.0))
                prev_load = float(
                    result[gap_start - 1].get("load_forecast_kwh")
                    or result[gap_start - 1].get("base_load_forecast_kwh", 0.0)
                )
                next_pv = float(result[gap_end].get("pv_forecast_kwh", 0.0))
                next_load = float(
                    result[gap_end].get("load_forecast_kwh")
                    or result[gap_end].get("base_load_forecast_kwh", 0.0)
                )

                for j in range(gap_start, gap_end):
                    fraction = (j - gap_start + 1) / (gap_size + 1)

                    result[j]["pv_forecast_kwh"] = prev_pv + fraction * (next_pv - prev_pv)
                    result[j]["load_forecast_kwh"] = prev_load + fraction * (next_load - prev_load)

                print(f"Info: Interpolated {gap_size} slot gap at index {gap_start}")

            i = gap_end
        else:
            i += 1

    return result


async def _get_forecast_data_aurora(
    price_slots: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    """Asynchronous logic for Aurora DB-backed forecasts."""
    timezone_name = str(config.get("timezone", "Europe/Stockholm"))
    local_tz = pytz.timezone(timezone_name)
    _fcfg: Any = config.get("forecasting", {})
    forecasting_cfg: dict[str, Any] = (
        cast("dict[str, Any]", _fcfg) if isinstance(_fcfg, dict) else {}
    )

    active_version = str(forecasting_cfg.get("active_forecast_version", "aurora"))

    # 1. Build slots strictly for the price horizon (0-48h)
    db_slots = await build_db_forecast_for_slots(price_slots, config)

    # 1b. Defensive interpolation for small gaps (1-2 slots / 15-30 min)
    # Belt-and-suspenders: handles race conditions where ML forecast
    # generation slightly misaligns with price slot boundaries. Larger gaps
    # (>2 slots) fall through to HA baseline fallback below.
    db_slots = _interpolate_small_gaps(db_slots)

    # 2. Fetch HA Load Baseline for fallback
    try:
        ha_profile = await get_load_profile_from_ha(config)
    except Exception:
        ha_profile = [0.0] * 96

    forecast_data: list[dict[str, Any]] = []
    if db_slots:
        print("Info: Using AURORA forecasts from learning DB (aurora).")
        for slot, db_slot in zip(price_slots, db_slots, strict=False):
            # Map slot time to 15-min index (0-95)
            # Localize to Stockholm/configured TZ to match profile
            ts = slot["start_time"].astimezone(local_tz)
            idx = int((ts.hour * 60 + ts.minute) // 15) % 96

            # Strictly prefer base_load_forecast_kwh (CLEAN) over load_forecast_kwh (DIRTY/TOTAL)
            val_load = float(
                db_slot.get("base_load_forecast_kwh") or db_slot.get("load_forecast_kwh", 0.0)
            )
            if val_load <= 0.001:
                val_load = ha_profile[idx]

            forecast_data.append(
                {
                    "start_time": slot["start_time"],
                    "pv_forecast_kwh": float(db_slot.get("pv_forecast_kwh", 0.0)),
                    "load_forecast_kwh": val_load,
                    "pv_p10": db_slot.get("pv_p10"),
                    "pv_p90": db_slot.get("pv_p90"),
                    "load_p10": db_slot.get("load_p10"),
                    "load_p90": db_slot.get("load_p90"),
                }
            )
    else:
        print("Warning: AURORA slots missing for price horizon. Returning empty slots.")

    # 2. Build DAILY totals for the extended horizon required by S-index
    daily_pv_forecast: dict[str, float] = {}
    daily_load_forecast: dict[str, float] = {}
    daily_pv_p10: dict[str, float] = {}
    daily_pv_p90: dict[str, float] = {}
    daily_load_p10: dict[str, float] = {}
    daily_load_p90: dict[str, float] = {}

    if price_slots:
        start_dt = price_slots[0]["start_time"].astimezone(local_tz)
        s_index_cfg = config.get("s_index", {})
        horizon_days_cfg = s_index_cfg.get("s_index_horizon_days", 4)
        try:
            max_days = int(horizon_days_cfg)
        except (TypeError, ValueError):
            max_days = 4

        horizon_days = max(4, max_days + 1)
        end_dt = start_dt + timedelta(days=horizon_days)

        # Fetch extended records from DB (base + corrections)
        extended_records = await get_forecast_slots(start_dt, end_dt, active_version)

        for rec in extended_records:
            ts = rec["slot_start"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            if ts.tzinfo is None:
                ts = pytz.UTC.localize(ts)
            date_key = ts.astimezone(local_tz).date().isoformat()

            # Use new nested structure from ml/api.py get_forecast_slots()
            base_pv = float(rec["final"]["pv_kwh"])
            base_load = float(rec["final"]["load_kwh"])

            pv_corr = float(rec.get("pv_correction_kwh", 0.0) or 0.0)
            load_corr = float(rec.get("load_correction_kwh", 0.0) or 0.0)

            pv_val = base_pv + pv_corr

            # Fallback for Load if 0.0
            if (base_load + load_corr) <= 0.001:
                # Calculate 15-min slot index (0-95)
                # ts is already localized or UTC, let's ensure local time for index match
                ts_local = ts.astimezone(local_tz)
                idx = int((ts_local.hour * 60 + ts_local.minute) // 15) % 96

                # Lazy load HA profile if needed (optimization)
                # But we likely already loaded it in _get_forecast_data_aurora if we are here?
                # Actually this is _get_forecast_data_aurora
                # We need to make sure ha_profile is available here.
                # It is not available in specific scope for "extended_records" loop below.
                # Let's fetch it if not existent (or pass it in).
                # Ideally use the one fetched above if possible.
                # To be safe and clean, we'll try fetch again or use a safe method.
                # Since this is "daily" aggregation, running fetching once is fine.
                try:
                    # We might want to cache this call if it's expensive, but for now it's okay.
                    # ha_profile from above scope is available here
                    # unless we are in the SAME function.
                    # We ARE in _get_forecast_data_aurora function scope.
                    # So 'ha_profile' defined at line 269 IS available!
                    load_val = ha_profile[idx]
                except (UnboundLocalError, NameError):
                    # Just in case code structure changed or valid ha_profile logic was conditioned
                    # We will re-fetch or use 0 default to avoid crash
                    try:
                        load_val = (await get_load_profile_from_ha(config))[idx]
                    except Exception:
                        load_val = 0.0
            else:
                load_val = base_load + load_corr

            daily_pv_forecast[date_key] = daily_pv_forecast.get(date_key, 0.0) + pv_val
            daily_load_forecast[date_key] = daily_load_forecast.get(date_key, 0.0) + load_val

            if rec.get("pv_p10") is not None:
                daily_pv_p10[date_key] = (
                    daily_pv_p10.get(date_key, 0.0) + float(rec["pv_p10"]) + pv_corr
                )
            if rec.get("pv_p90") is not None:
                daily_pv_p90[date_key] = (
                    daily_pv_p90.get(date_key, 0.0) + float(rec["pv_p90"]) + pv_corr
                )
            if rec.get("load_p10") is not None:
                daily_load_p10[date_key] = (
                    daily_load_p10.get(date_key, 0.0) + float(rec["load_p10"]) + load_corr
                )
            if rec.get("load_p90") is not None:
                daily_load_p90[date_key] = (
                    daily_load_p90.get(date_key, 0.0) + float(rec["load_p90"]) + load_corr
                )

    return {
        "slots": forecast_data,
        "daily_pv_forecast": daily_pv_forecast,
        "daily_load_forecast": daily_load_forecast,
    }


async def _get_forecast_data_async(
    price_slots: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    """
    Async logic for fallback Open-Meteo forecasts.
    """
    _sys_cfg: Any = config.get("system", {})
    if isinstance(_sys_cfg, dict):
        system_config: dict[str, Any] = cast("dict[str, Any]", _sys_cfg)
    else:
        system_config = {}

    _loc_cfg: Any = system_config.get("location", {})
    if isinstance(_loc_cfg, dict):
        location: dict[str, Any] = cast("dict[str, Any]", _loc_cfg)
    else:
        location = {}

    latitude = float(location.get("latitude", 59.3))
    longitude = float(location.get("longitude", 18.1))

    # Support for Multi-Array (REV ARC14 Phase 2)
    solar_arrays: list[Any] = system_config.get("solar_arrays", [])
    azimuth_list: list[float] = []
    tilt_list: list[float] = []
    kwp_list: list[float] = []
    if not solar_arrays or not isinstance(solar_arrays, list):  # type: ignore[unnecessary-isinstance-call]
        # Fallback to legacy single array or default
        _legacy_cfg: Any = system_config.get("solar_array", {})
        solar_array: dict[str, Any] = (
            cast("dict[str, Any]", _legacy_cfg) if isinstance(_legacy_cfg, dict) else {}
        )
        azimuth_list = [float(solar_array.get("azimuth", 180))]
        tilt_list = [float(solar_array.get("tilt", 30))]
        kwp_list = [float(solar_array.get("kwp", 5.0))]
        logger.debug("Falling back to legacy solar_array for forecast")
    else:
        for i, _array in enumerate(solar_arrays):
            a_idx = i + 1
            array: dict[str, Any] = (
                cast("dict[str, Any]", _array) if isinstance(_array, dict) else {}
            )
            name: str = str(array.get("name", f"Array {a_idx}"))
            az = float(array.get("azimuth", 180))
            ti = float(array.get("tilt", 30))
            kp = float(array.get("kwp", 0.0))
            azimuth_list.append(az)
            tilt_list.append(ti)
            kwp_list.append(kp)
            logger.debug(
                "Solar array %d (%s) configured: %.1fkWp, Azimuth: %.0f, Tilt: %.0f",
                a_idx,
                name,
                kp,
                az,
                ti,
            )

    timezone = str(config.get("timezone", "Europe/Stockholm"))
    local_tz = pytz.timezone(timezone)

    # --- FALLBACK: Open-Meteo (Live API) ---

    pv_kwh_forecast: list[float] = []
    daily_pv_forecast: dict[str, float] = {}
    resolution_hours = 0.25

    try:
        # REV F60 Phase 6: OpenMeteo requires ALL parameters to be lists when ANY array param is a list
        # Always wrap lat/long in lists when we have any solar arrays configured
        async def _fetch_forecast():
            # Filter out invalid arrays (kwp <= 0) - REV F62 fix
            valid_arrays = [
                (az, ti, kp)
                for az, ti, kp in zip(azimuth_list, tilt_list, kwp_list, strict=False)
                if kp > 0.0
            ]

            if not valid_arrays:
                logger.warning(
                    "No valid solar arrays with kwp > 0 found. Using default single array."
                )
                # Fallback to default single array
                azimuth_list_clean = [0.0]  # Open-Meteo South is 0
                tilt_list_clean = [30.0]
                kwp_list_clean = [5.0]
            else:
                # Open-Meteo expects -180 to 180 (0=South, 90=West)
                # Convert from HA (North=0, East=90, South=180, West=270)
                azimuth_list_clean = [(arr[0] % 360) - 180 for arr in valid_arrays]
                tilt_list_clean = [arr[1] for arr in valid_arrays]
                kwp_list_clean = [arr[2] for arr in valid_arrays]

                # Log which arrays were filtered out
                filtered_count = len(kwp_list) - len(valid_arrays)
                if filtered_count > 0:
                    logger.warning("Filtered out %d solar array(s) with kwp <= 0.0", filtered_count)

            async with OpenMeteoSolarForecast(
                latitude=[latitude] * len(kwp_list_clean) if kwp_list_clean else latitude,
                longitude=[longitude] * len(kwp_list_clean) if kwp_list_clean else longitude,
                declination=tilt_list_clean,
                azimuth=azimuth_list_clean,
                dc_kwp=kwp_list_clean,
            ) as forecast:
                estimate = await forecast.estimate()
                return estimate.watts

        solar_data_dict = await _fetch_forecast()
        if solar_data_dict:
            sorted_times = sorted(solar_data_dict.keys())
            if len(sorted_times) > 1:
                delta_seconds = abs((sorted_times[1] - sorted_times[0]).total_seconds())
                resolution_hours = max(delta_seconds / 3600.0, 0.0001)
            for dt in sorted_times:
                value = solar_data_dict[dt]
                dt_obj = dt
                if dt_obj.tzinfo is None:
                    dt_obj = pytz.UTC.localize(dt_obj)
                local_date = dt_obj.astimezone(local_tz).date().isoformat()
                energy_kwh = value * resolution_hours / 1000.0
                daily_pv_forecast[local_date] = daily_pv_forecast.get(local_date, 0.0) + energy_kwh

            # Map PV forecast to price slots (15 min resolution assumed)
            for slot in price_slots:
                slot_time = slot["start_time"]
                rounded_time = slot_time.replace(
                    minute=(slot_time.minute // 15) * 15, second=0, microsecond=0
                )
                power_watts = 0.0
                for solar_time, solar_power in solar_data_dict.items():
                    if solar_time == rounded_time:
                        power_watts = solar_power
                        break
                pv_kwh_forecast.append(power_watts * 0.25 / 1000.0)

        # REV F60 Phase 7: Clear forecast errors after successful forecast
        from backend.health import clear_forecast_errors

        clear_forecast_errors()

    except Exception as exc:
        # REV F60: Removed dangerous dummy fallback. PV forecast failure is critical.
        # Using fake solar data would cause the planner to make incorrect decisions.
        from backend.health import record_forecast_error

        error = PVForecastError(
            "Open-Meteo Solar Forecast failed - cannot generate valid PV forecast",
            original_exception=exc,
            solar_arrays=len(kwp_list),
            details={
                "latitude": latitude,
                "longitude": longitude,
                "arrays": len(kwp_list),
                "total_kwp": sum(kwp_list),
            },
        )
        record_forecast_error(error, context={"arrays": len(kwp_list)})
        raise error from exc
    if price_slots:
        first_date = price_slots[0]["start_time"].astimezone(local_tz).date()
        last_value = None
        for offset in range(4):
            target_date = (first_date + timedelta(days=offset)).isoformat()
            if target_date in daily_pv_forecast:
                last_value = daily_pv_forecast[target_date]
            elif last_value is not None:
                daily_pv_forecast[target_date] = last_value

    try:
        load_profile = await get_load_profile_from_ha(config)
    except Exception as exc:
        print(f"Warning: Failed to get HA load profile, using dummy: {exc}")
        load_profile = get_dummy_load_profile(config)

    daily_load_total = sum(load_profile)
    daily_load_forecast: dict[str, float] = {}

    load_kwh_forecast: list[float] = []
    for slot in price_slots:
        slot_time = slot["start_time"]
        slot_index = int((slot_time.hour * 60 + slot_time.minute) // 15)
        load_kwh = load_profile[slot_index]
        load_kwh_forecast.append(load_kwh)
        local_date = slot_time.astimezone(local_tz).date().isoformat()
        daily_load_forecast[local_date] = daily_load_total

    if price_slots:
        first_date = price_slots[0]["start_time"].astimezone(local_tz).date()
        for offset in range(4):
            target_date = (first_date + timedelta(days=offset)).isoformat()
            daily_load_forecast.setdefault(target_date, daily_load_total)

    forecast_data: list[dict[str, Any]] = []
    total_slots = len(price_slots)
    for idx in range(total_slots):
        pv_kwh = pv_kwh_forecast[idx] if idx < len(pv_kwh_forecast) else 0.0
        load_kwh = load_kwh_forecast[idx] if idx < len(load_kwh_forecast) else 0.0
        slot = price_slots[idx]
        forecast_data.append(
            {
                "start_time": slot["start_time"],
                "pv_forecast_kwh": pv_kwh,
                "load_forecast_kwh": load_kwh,
            }
        )

    return {
        "slots": forecast_data,
        "daily_pv_forecast": daily_pv_forecast,
        "daily_load_forecast": daily_load_forecast,
    }


async def get_initial_state(config_path: str = "config.yaml") -> dict[str, Any]:
    """
    Get the initial battery state (Asynchronous).
    """
    with Path(config_path).open() as f:
        config = yaml.safe_load(f)

    # Use system.battery if available, otherwise fall back to battery
    battery_config = config.get("system", {}).get("battery", config.get("battery", {}))
    capacity_kwh = battery_config.get("capacity_kwh", 10.0)
    battery_soc_percent = 50.0
    battery_cost_sek_per_kwh = config.get("battery_economics", {}).get(
        "battery_cycle_cost_kwh", 0.20
    )

    # HA Config
    ha_config = load_home_assistant_config()
    input_sensors = config.get("input_sensors", {})
    soc_entity_id = input_sensors.get("battery_soc", ha_config.get("soc_entity_id"))

    if soc_entity_id:
        ha_soc = await get_ha_sensor_float(soc_entity_id)
        if ha_soc is not None:
            battery_soc_percent = ha_soc
        else:
            # Critical safety check: Do not default to 50% if we expected a live reading.
            # This causes "phantom charging" when HA is down.
            raise RuntimeError(
                f"Critical: Failed to read battery SoC from {soc_entity_id}. "
                "Planning aborted to prevent unsafe assumptions."
            )

    battery_soc_percent = max(0.0, min(100.0, battery_soc_percent))
    battery_kwh = capacity_kwh * battery_soc_percent / 100.0

    # Water heater energy today
    system_config = config.get("system", {})
    has_water_heater = system_config.get("has_water_heater", False)
    water_heated_today_kwh = 0.0

    if has_water_heater:
        water_entity = input_sensors.get("water_heater_consumption", "sensor.vvb_energy_daily")
        if water_entity:
            ha_water = await get_ha_sensor_float(water_entity)
            if ha_water is not None:
                water_heated_today_kwh = ha_water

    # Rev K25: EV state (SoC and plug status)
    has_ev_charger = system_config.get("has_ev_charger", False)
    ev_soc_percent = 0.0
    ev_plugged_in = False

    if has_ev_charger:
        # Rev F63: EV sensors are now only in ev_chargers[] array
        ev_soc_entity = None
        ev_plug_entity = None

        ev_chargers = config.get("ev_chargers", [])
        for ev in ev_chargers:
            if ev.get("enabled", True):
                if ev.get("soc_sensor"):
                    ev_soc_entity = ev["soc_sensor"]
                if ev.get("plug_sensor"):
                    ev_plug_entity = ev["plug_sensor"]
                break  # Only use first enabled EV charger

        if ev_soc_entity:
            ha_ev_soc = await get_ha_sensor_float(ev_soc_entity)
            if ha_ev_soc is not None:
                ev_soc_percent = ha_ev_soc
            else:
                logger.warning("EV SoC sensor %s returned no data, defaulting to 0%", ev_soc_entity)
        else:
            logger.warning("has_ev_charger is true but ev_soc sensor is not configured")

        if ev_plug_entity:
            ev_plugged_in = await get_ha_bool(ev_plug_entity)
        else:
            logger.warning("has_ev_charger is true but ev_plug sensor is not configured")

    return {
        "battery_soc_percent": battery_soc_percent,
        "battery_kwh": battery_kwh,
        "battery_cost_sek_per_kwh": battery_cost_sek_per_kwh,
        "water_heated_today_kwh": water_heated_today_kwh,
        "ev_soc_percent": ev_soc_percent,
        "ev_plugged_in": ev_plugged_in,
    }


async def get_all_input_data(config_path: str = "config.yaml") -> dict[str, Any]:
    """
    Orchestrate all input data fetching.
    """
    # Load config
    with Path(config_path).open() as f:
        config = yaml.safe_load(f)

    # --- AUTO-RUN ML INFERENCE IF AURORA IS ACTIVE ---
    if config.get("forecasting", {}).get("active_forecast_version") == "aurora":
        try:
            print("🧠 Running AURORA ML Inference Pipeline (base + correction)...")
            from ml.pipeline import run_inference

            # Rev 2.4.13: Respect configured horizon (default 2 days / 48h)
            # Previously hardcoded to 168h (7 days), causing wasted CPU cycles.
            learning_cfg = config.get("learning", {})
            days = int(learning_cfg.get("horizon_days", 2))
            hours = days * 24

            await run_inference(horizon_hours=hours, forecast_version="aurora")
        except Exception as e:
            print(f"⚠️ AURORA Inference Pipeline Failed: {e}")

    # --- FETCH CONTEXT (New in Rev 19, extended in Rev 58) ---
    sensors = config.get("input_sensors", {})
    vacation_id = sensors.get("vacation_mode")
    alarm_id = sensors.get("alarm_state")

    timezone_name = config.get("timezone", "Europe/Stockholm")
    local_tz = pytz.timezone(timezone_name)
    now_local = datetime.now(local_tz)
    horizon_end = now_local + timedelta(hours=48)

    volatility_raw = get_weather_volatility(now_local, horizon_end, config)
    cloud_vol = float(volatility_raw.get("cloud_volatility", 0.0) or 0.0)
    temp_vol = float(volatility_raw.get("temp_volatility", 0.0) or 0.0)

    context = {
        "vacation_mode": await get_ha_bool(vacation_id) if vacation_id else False,
        "alarm_armed": await get_ha_bool(alarm_id) if alarm_id else False,
        "weather_volatility": {
            "cloud": max(0.0, min(1.0, cloud_vol)),
            "temp": max(0.0, min(1.0, temp_vol)),
        },
    }
    # -------------------------------------

    price_data = await get_nordpool_data(config_path)

    forecast_result = await get_forecast_data(price_data, config)
    forecast_data = forecast_result.get("slots", [])
    initial_state = await get_initial_state(config_path)

    return {
        "price_data": price_data,
        "forecast_data": forecast_data,
        "initial_state": initial_state,
        "daily_pv_forecast": forecast_result.get("daily_pv_forecast", {}),
        "daily_load_forecast": forecast_result.get("daily_load_forecast", {}),
        "daily_probabilistic": forecast_result.get("daily_probabilistic", {}),
        "context": context,
    }


async def get_db_forecast_slots(
    start: datetime, end: datetime, config: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Fetch forecast slots from the learning database via ml.api.

    This helper does not change planner behaviour by itself; it simply
    wraps get_forecast_slots using the configured active_forecast_version.
    """
    _fcfg: Any = config.get("forecasting", {})
    if isinstance(_fcfg, dict):
        forecasting_cfg: dict[str, Any] = cast("dict[str, Any]", _fcfg)
    else:
        forecasting_cfg = {}

    version = str(forecasting_cfg.get("active_forecast_version", "baseline_7_day_avg"))
    return await get_forecast_slots(start, end, version)


async def build_db_forecast_for_slots(
    price_slots: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Fetch DB forecast records matching the exact time range of price_slots.
    Returns a list of dicts aligned with price_slots (or empty list if no match).
    """
    if not price_slots:
        return []

    _fcfg: Any = config.get("forecasting", {})
    if isinstance(_fcfg, dict):
        forecasting_cfg: dict[str, Any] = cast("dict[str, Any]", _fcfg)
    else:
        forecasting_cfg = {}

    version = str(forecasting_cfg.get("active_forecast_version", "baseline_7_day_avg"))

    timezone = str(config.get("timezone", "Europe/Stockholm"))
    local_tz = pytz.timezone(timezone)

    # Determine horizon from price slots
    start_time = price_slots[0]["start_time"].astimezone(local_tz)
    end_time = price_slots[-1]["start_time"].astimezone(local_tz) + timedelta(
        minutes=15,
    )

    records = await get_forecast_slots(start_time, end_time, version)
    if not records:
        return []

    # Index forecasts by localised slot_start for quick lookup
    indexed: dict[datetime, dict[str, Any]] = {}
    for rec in records:
        ts = rec["slot_start"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = pytz.UTC.localize(ts)
        indexed[ts.astimezone(local_tz)] = rec

    result: list[dict[str, Any]] = []
    for slot in price_slots:
        ts = slot["start_time"].astimezone(local_tz)
        rec = indexed.get(ts)

        # Default values in case no forecast is found
        pv = 0.0
        load = 0.0
        pv_p10 = None
        pv_p90 = None
        load_p10 = None
        load_p90 = None

        if rec is None:
            # Defensive fallback: find closest forecast at or before requested slot
            fallback_ts = None
            for forecast_ts in sorted(indexed.keys()):
                if forecast_ts <= ts:
                    fallback_ts = forecast_ts
                else:
                    break

            if fallback_ts is not None:
                rec = indexed[fallback_ts]
                print(
                    f"Warning: No exact forecast match for {ts}, using fallback from {fallback_ts}"
                )

        if rec is not None:
            # Use new nested structure from ml/api.py get_forecast_slots()
            pv = float(rec["final"]["pv_kwh"])
            load = float(rec["final"]["load_kwh"])

            # Extract probabilistic data
            prob_data = rec.get("probabilistic", {})
            pv_p10 = prob_data.get("pv_p10")
            pv_p90 = prob_data.get("pv_p90")
            load_p10 = prob_data.get("load_p10")
            load_p90 = prob_data.get("load_p90")

        result.append(
            {
                "pv_forecast_kwh": pv,
                "load_forecast_kwh": load,
                "pv_p10": pv_p10,
                "pv_p90": pv_p90,
                "load_p10": load_p10,
                "load_p90": load_p90,
            }
        )

    return result


async def get_load_profile_from_ha(config: dict[str, Any]) -> list[float]:
    """Fetch actual load profile from Home Assistant historical data (Async)."""
    ha_config = load_home_assistant_config()
    url: str | None = cast("str | None", ha_config.get("url"))
    token = cast("str", ha_config.get("token", ""))

    _sensors_cfg: Any = config.get("input_sensors", {})
    if isinstance(_sensors_cfg, dict):
        input_sensors: dict[str, Any] = cast("dict[str, Any]", _sensors_cfg)
    else:
        input_sensors = {}

    entity_id: str | None = input_sensors.get(
        "total_load_consumption", ha_config.get("consumption_entity_id")
    )

    if not all([url, token, entity_id]):
        print("Warning: Missing Home Assistant configuration for load profile")
        return get_dummy_load_profile(config)

    headers = make_ha_headers(token)
    end_time = datetime.now(pytz.UTC)
    start_time = end_time - timedelta(days=7)

    url_str: str = cast("str", url)
    api_url = f"{url_str.rstrip('/')}/api/history/period/{start_time.isoformat()}"
    params = {
        "filter_entity_id": entity_id,
        "end_time": end_time.isoformat(),
        "significant_changes_only": False,
        "minimal_response": False,
    }

    try:
        print(f"Fetching {entity_id} data from Home Assistant...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
        if not data or not data[0]:
            print(f"Warning: No data received from Home Assistant for {entity_id}")
            return get_dummy_load_profile(config)

        states = data[0]
        if len(states) < 2:
            print(f"Warning: Insufficient data points from Home Assistant for {entity_id}")
            return get_dummy_load_profile(config)

        # Convert to local timezone for processing
        local_tz = pytz.timezone("Europe/Stockholm")

        # Calculate energy consumption between state changes
        time_buckets = [0.0] * (96 * 7)  # 7 days * 96 slots per day
        prev_state = None
        prev_time = None

        start_time_local = start_time.astimezone(local_tz)

        for state in states:
            try:
                # Skip unavailable/unknown/null states silently
                state_val = state.get("state", "")
                if state_val in ("unavailable", "unknown", "null", "", None):
                    continue

                current_time = datetime.fromisoformat(state["last_changed"])
                if current_time.tzinfo is None:
                    current_time = current_time.replace(tzinfo=pytz.UTC)
                current_time = current_time.astimezone(local_tz)
                current_value = float(state_val)

                # Normalize energy unit to kWh (handles Wh, kWh, MWh)
                attributes = state.get("attributes", {})
                unit = attributes.get("unit_of_measurement")
                current_value = _normalize_energy_to_kwh(current_value, unit)

                if prev_state is not None and prev_time is not None:
                    # Calculate energy delta (ensure positive)
                    energy_delta = max(0, current_value - prev_state)

                    # Distribute across time buckets
                    time_diff = current_time - prev_time
                    minutes_diff = time_diff.total_seconds() / 60

                    if minutes_diff > 0 and energy_delta > 0:
                        # Calculate which 15-minute buckets this spans
                        start_slot = int((prev_time.hour * 60 + prev_time.minute) // 15)
                        end_slot = int((current_time.hour * 60 + current_time.minute) // 15)
                        day_offset = int(
                            (prev_time - start_time_local).total_seconds() / (24 * 3600)
                        )

                        # Calculate start and end times for each slot
                        for slot_idx in range(max(0, start_slot), min(96, end_slot + 1)):
                            # Calculate slot start time relative to the day start
                            slot_start_minutes = slot_idx * 15
                            day_start = prev_time.replace(hour=0, minute=0, second=0, microsecond=0)
                            slot_start_time = day_start + timedelta(minutes=slot_start_minutes)
                            slot_end_time = slot_start_time + timedelta(minutes=15)

                            # Calculate overlap between this slot and the energy consumption period
                            overlap_start = max(prev_time, slot_start_time)
                            overlap_end = min(current_time, slot_end_time)
                            overlap_minutes = max(
                                0, (overlap_end - overlap_start).total_seconds() / 60
                            )

                            if overlap_minutes > 0:
                                # Distribute energy proportionally to time overlap
                                energy_fraction = overlap_minutes / minutes_diff
                                energy_for_slot = energy_delta * energy_fraction

                                bucket_idx = day_offset * 96 + slot_idx
                                if 0 <= bucket_idx < len(time_buckets):
                                    time_buckets[bucket_idx] += energy_for_slot

                prev_state = current_value
                prev_time = current_time

            except (ValueError, TypeError, KeyError) as e:
                print(f"Warning: Skipping invalid state data for {entity_id}: {e}")
                continue

        # Create average daily profile from the 7 days of data (divide by 7 days)
        daily_profile = [0.0] * 96
        for slot in range(96):
            slot_sum = 0.0
            for day in range(7):
                bucket_idx = day * 96 + slot
                if 0 <= bucket_idx < len(time_buckets):
                    slot_sum += time_buckets[bucket_idx]
            daily_profile[slot] = slot_sum / 7.0

        # Validate and clean the profile
        total_daily = sum(daily_profile)
        if total_daily <= 0:
            print(f"Warning: No valid energy consumption data found for {entity_id}")
            return get_dummy_load_profile(config)

        print(f"Successfully loaded HA data: {total_daily:.2f} kWh/day average")

        # Ensure all values are positive and reasonable
        for i in range(96):
            if daily_profile[i] < 0:
                daily_profile[i] = 0
            elif daily_profile[i] > 10:  # Cap at 10kW per 15min
                daily_profile[i] = 10

        return daily_profile

    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        print(f"Warning: Failed to fetch data from Home Assistant for {entity_id}: {e}")
        return get_dummy_load_profile(config)
    except Exception as e:
        print(f"Warning: Error processing Home Assistant data for {entity_id}: {e}")
        return get_dummy_load_profile(config)


def get_dummy_load_profile(config: dict[str, Any]) -> list[float]:
    """Create a dummy load profile or a synthetic scaled profile.

    If config.input_sensors.total_load_consumption is a number (estimated daily kWh),
    we generate a synthetic winter heat-pump curve scaled to that daily total.
    Otherwise, we fall back to a 0.5 kWh flat dummy profile.
    """
    import logging

    logger = logging.getLogger(__name__)

    # Check if the user provided an estimated daily kWh (from Startup Wizard)
    # The wizard stores this as a string, e.g. "20", in the total_load_consumption field
    # if they selected 'synthetic' mode.
    estimated_daily_kwh = None
    sensors = config.get("input_sensors", {})
    raw_val = sensors.get("total_load_consumption")

    if raw_val is not None:
        try:
            val = float(raw_val)
            if val > 0 and not str(raw_val).startswith(("sensor.", "input_")):
                estimated_daily_kwh = val
        except (ValueError, TypeError):
            pass

    if estimated_daily_kwh is not None:
        logger.info(
            f"Generating Synthetic Heat Pump profile scaled to {estimated_daily_kwh} kWh/day."
        )
        set_load_forecast_status("synthetic", "estimated")

        # Base normalized heat pump curve (higher in night/morning, lower in afternoon)
        # 96 slots representing a standard winter day shape. Sums to ~1.0.
        base_curve = [
            1.2,
            1.2,
            1.1,
            1.1,
            1.1,
            1.1,
            1.2,
            1.2,  # 00:00 - 02:00
            1.2,
            1.3,
            1.3,
            1.3,
            1.4,
            1.4,
            1.5,
            1.6,  # 02:00 - 04:00
            1.7,
            1.8,
            1.9,
            1.9,
            2.0,
            2.0,
            1.9,
            1.8,  # 04:00 - 06:00
            1.7,
            1.6,
            1.5,
            1.4,
            1.3,
            1.2,
            1.1,
            1.0,  # 06:00 - 08:00
            0.9,
            0.9,
            0.8,
            0.8,
            0.8,
            0.7,
            0.7,
            0.7,  # 08:00 - 10:00
            0.7,
            0.6,
            0.6,
            0.6,
            0.6,
            0.5,
            0.5,
            0.5,  # 10:00 - 12:00
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.5,
            0.6,  # 12:00 - 14:00
            0.6,
            0.6,
            0.7,
            0.7,
            0.8,
            0.8,
            0.9,
            1.0,  # 14:00 - 16:00
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.7,  # 16:00 - 18:00
            1.6,
            1.5,
            1.4,
            1.3,
            1.2,
            1.1,
            1.0,
            1.0,  # 18:00 - 20:00
            0.9,
            0.9,
            0.9,
            1.0,
            1.0,
            1.0,
            1.1,
            1.1,  # 20:00 - 22:00
            1.1,
            1.1,
            1.1,
            1.2,
            1.2,
            1.2,
            1.2,
            1.2,  # 22:00 - 00:00
        ]

        curve_sum = sum(base_curve)
        # Scale the curve so its integral (sum) equals the estimated daily kWh
        return [(val / curve_sum) * estimated_daily_kwh for val in base_curve]

    logger.warning(
        "⚠️ Using DEMO load profile (0.5 kWh flat) - no historical data available. Configure total_load_consumption sensor for accurate forecasts."
    )

    # REV F65 Phase 5b: Set degraded status when using demo data
    set_load_forecast_status("degraded", "demo")

    return [0.5] * 96


if __name__ == "__main__":
    # Test the combined input data fetching
    print("Testing get_all_input_data()...")

    async def test():
        try:
            data = await get_all_input_data(config_path="config.yaml")
            print(f"Price slots: {len(data['price_data'])}")
            print(f"Forecast slots: {len(data.get('forecast_data', []))}")
            print("Initial state:", data["initial_state"])
            print()

            # Show first 5 slots
            for i in range(min(5, len(data["price_data"]))):
                slot = data["price_data"][i]
                # forecast_data is the list matching price_slots
                forecast_slots = cast("list[dict[str, Any]]", data.get("forecast_data", []))
                forecast = forecast_slots[i] if i < len(forecast_slots) else {}
                slot_time = slot["start_time"]
                import_price = slot["import_price_sek_kwh"]
                pv_forecast = forecast.get("pv_forecast_kwh", 0.0)
                load_forecast = forecast.get("load_forecast_kwh", 0.0)
                summary = (
                    f"Slot {i + 1}: {slot_time} - Import: {import_price:.3f} SEK/kWh, "
                    f"PV: {pv_forecast:.3f} kWh, "
                    f"Load: {load_forecast:.3f} kWh"
                )
                print(summary)

            if len(data["price_data"]) > 5:
                print(f"... and {len(data['price_data']) - 5} more slots")

        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Error: {e}")

    import asyncio

    asyncio.run(test())
