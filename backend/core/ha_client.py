import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import pytz
import yaml

from backend.core import secrets
from backend.health import set_load_forecast_status

logger = logging.getLogger("darkstar.core.ha_client")


def make_ha_headers(token: str) -> dict[str, str]:
    """Return headers for Home Assistant REST calls."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def gather_sensor_reads(
    reads: list[tuple[str, Callable[[], Coroutine[Any, Any, Any]]]],
    context: str = "sensor_batch",
) -> dict[str, Any]:
    """Run multiple sensor reads concurrently using asyncio.gather().

    Args:
        reads: List of (name, coroutine_factory) pairs. Each factory is called
               to produce a coroutine (e.g., lambda: get_ha_sensor_float(entity_id)).
        context: Label included in log messages to identify the call site.

    Returns:
        Dict mapping each name to its result value, or None if that read failed.
    """
    names = [name for name, _ in reads]
    coros = [fn() for _, fn in reads]
    raw = await asyncio.gather(*coros, return_exceptions=True)

    out: dict[str, Any] = {}
    failures = 0
    for name, result in zip(names, raw, strict=True):
        if isinstance(result, Exception):
            logger.warning("[%s] Sensor read failed for '%s': %s", context, name, result)
            out[name] = None
            failures += 1
        else:
            out[name] = result

    if failures > 0 and failures == len(reads):
        logger.warning("[%s] All %d sensor reads failed", context, failures)

    return out


async def get_ha_entity_state(entity_id: str) -> dict[str, Any] | None:
    """Fetch a single entity state from Home Assistant asynchronously."""
    ha_config = secrets.load_home_assistant_config()
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


async def get_initial_state(
    config_path: str = "config.yaml",
    ev_plugged_in_override: bool | None = None,
) -> dict[str, Any]:
    """
    Get the initial battery state (Asynchronous).

    Args:
        config_path: Path to config.yaml
        ev_plugged_in_override: If provided, use this value instead of fetching from HA
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
    ha_config = secrets.load_home_assistant_config()
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

    # Rev K25: EV state (SoC and plug status)
    has_ev_charger = system_config.get("has_ev_charger", False)
    ev_soc_percent = 0.0
    ev_plugged_in = False

    ev_soc_entity: str | None = None
    ev_plug_entity: str | None = None
    water_entity: str | None = None

    if has_ev_charger:
        # Rev F63: EV sensors are now only in ev_chargers[] array
        ev_chargers = config.get("ev_chargers", [])
        for ev in ev_chargers:
            if ev.get("enabled", True):
                if ev.get("soc_sensor"):
                    ev_soc_entity = ev["soc_sensor"]
                if ev.get("plug_sensor"):
                    ev_plug_entity = ev["plug_sensor"]
                break  # Only use first enabled EV charger

        if not ev_soc_entity:
            logger.warning("has_ev_charger is true but ev_soc sensor is not configured")

    # ARC15: Read water heater energy sensors from water_heaters[] array, sum across enabled
    water_entities: list[str] = []
    if has_water_heater:
        water_heaters = config.get("water_heaters", [])
        for wh in water_heaters:
            if wh.get("enabled", True) and wh.get("energy_sensor"):
                water_entities.append(str(wh["energy_sensor"]))

    # Batch: water heater, EV SoC, and (optionally) EV plug reads in parallel
    optional_reads: list[tuple[str, Any]] = []
    for idx, water_entity in enumerate(water_entities):
        optional_reads.append((f"water_{idx}", lambda e=water_entity: get_ha_sensor_float(e)))
    if ev_soc_entity:
        optional_reads.append(("ev_soc", lambda e=ev_soc_entity: get_ha_sensor_float(e)))
    # Only fetch EV plug from HA if no override is provided
    if ev_plug_entity and ev_plugged_in_override is None:
        optional_reads.append(("ev_plug", lambda e=ev_plug_entity: get_ha_bool(e)))

    optional_results: dict[str, Any] = {}
    if optional_reads:
        optional_results = await gather_sensor_reads(optional_reads, context="initial_state")

    # Aggregate water heater energy across all enabled heaters
    total_water_kwh = 0.0
    for idx in range(len(water_entities)):
        ha_water = optional_results.get(f"water_{idx}")
        if ha_water is not None:
            total_water_kwh += ha_water
    water_heated_today_kwh = total_water_kwh

    ha_ev_soc = optional_results.get("ev_soc")
    if ev_soc_entity:
        if ha_ev_soc is not None:
            ev_soc_percent = ha_ev_soc
        else:
            logger.warning("EV SoC sensor %s returned no data, defaulting to 0%%", ev_soc_entity)

    # Rev EVFIX: Use override if provided (avoids WebSocket-vs-REST race)
    if ev_plugged_in_override is not None:
        ev_plugged_in = ev_plugged_in_override
        logger.debug(
            "Using ev_plugged_in_override=%s (skipping HA REST fetch)", ev_plugged_in_override
        )
    elif ev_plug_entity:
        ev_plugged_in = bool(optional_results.get("ev_plug"))
    elif has_ev_charger:
        logger.warning("has_ev_charger is true but ev_plug sensor is not configured")

    return {
        "battery_soc_percent": battery_soc_percent,
        "battery_kwh": battery_kwh,
        "battery_cost_sek_per_kwh": battery_cost_sek_per_kwh,
        "water_heated_today_kwh": water_heated_today_kwh,
        "ev_soc_percent": ev_soc_percent,
        "ev_plugged_in": ev_plugged_in,
    }


async def get_load_profile_from_ha(config: dict[str, Any]) -> list[float]:
    """Fetch actual load profile from Home Assistant historical data (Async)."""
    ha_config = secrets.load_home_assistant_config()
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
