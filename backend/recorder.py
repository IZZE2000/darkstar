import asyncio
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytz
import yaml

from backend.learning.backfill import BackfillEngine

# Local imports
from backend.learning.store import LearningStore
from backend.loads.service import LoadDisaggregator
from inputs import get_ha_sensor_float

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("recorder")


def _load_config():
    try:
        with Path("config.yaml").open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


async def record_observation_from_current_state(
    config: dict, disaggregator: LoadDisaggregator | None = None
):
    """Capture current system state and store as an observation."""
    if not config:
        config = _load_config()
    db_path = config.get("learning", {}).get("sqlite_path", "data/planner_learning.db")
    tz_name = config.get("timezone", "Europe/Stockholm")
    tz = pytz.timezone(tz_name)

    # Initialize store (in-place initialization is acceptable for the standalone script)
    store = LearningStore(db_path, tz)

    # Identify the just-finished slot (or current instant)
    now = datetime.now(tz)
    # Round down to nearest 15 min
    minute_block = (now.minute // 15) * 15
    slot_start = now.replace(minute=minute_block, second=0, microsecond=0)
    slot_end = slot_start + timedelta(minutes=15)

    # Gather Data
    input_sensors = config.get("input_sensors", {})

    # Helper to get sensor value and convert W to kW if needed
    async def get_kw(key, default=0.0):
        entity = input_sensors.get(key)
        if not entity:
            return default
        val = await get_ha_sensor_float(entity)
        if val is None:
            return default
        # Assume sensors are in Watts if > 100? Or just assume Watts?
        # Usually HA power sensors are W.
        return val / 1000.0

    # Current Power State (Snapshot)
    pv_kw = await get_kw("pv_power")
    total_load_kw = await get_kw("load_power")

    # Disaggregate loads if disaggregator is provided (REV // ML2)
    controllable_kw = 0.0
    if disaggregator:
        controllable_kw = await disaggregator.update_current_power()
        load_kw = disaggregator.calculate_base_load(total_load_kw, controllable_kw)
        logger.info(
            f"Disaggregation: Total={total_load_kw:.3f}kW, Controllable={controllable_kw:.3f}kW -> Base={load_kw:.3f}kW"
        )
    else:
        load_kw = total_load_kw

    # Grid Metering Logic (REV // UI5)
    meter_type = config.get("system", {}).get("grid_meter_type", "net")

    if meter_type == "dual":
        # Dual sensors (Import/Export separate)
        import_kw = await get_kw("grid_import_power")
        export_kw = await get_kw("grid_export_power")
    else:
        # Net Meter (Single sensor, positive = import, negative = export)
        grid_net_kw = await get_kw("grid_power")
        import_kw = max(0.0, grid_net_kw)
        export_kw = max(0.0, -grid_net_kw)

    battery_kw = await get_kw("battery_power")
    water_kw = await get_kw("water_power")

    # Estimate Energy for the 15m slot (kWh = avg_kW * 0.25h)
    # This is a Rough Approximation if we don't have cumulative counters
    # ideally we would diff cumulative counters.
    # For now, we store the snapshot rate converted to energy.
    pv_kwh = pv_kw * 0.25
    load_kwh = load_kw * 0.25
    import_kwh = import_kw * 0.25
    export_kwh = export_kw * 0.25
    water_kwh = water_kw * 0.25

    # Standard inverter convention: positive = discharge, negative = charge
    batt_discharge_kwh = (battery_kw * 0.25) if battery_kw > 0 else 0.0
    batt_charge_kwh = (abs(battery_kw) * 0.25) if battery_kw < 0 else 0.0

    # Battery
    soc_entity = input_sensors.get("battery_soc")
    soc_percent = (await get_ha_sensor_float(soc_entity)) or 0.0 if soc_entity else 0.0

    # Construct Record
    record = {
        "slot_start": slot_start,
        "slot_end": slot_end,
        "pv_kwh": pv_kwh,
        "load_kwh": load_kwh,
        "import_kwh": import_kwh,
        "export_kwh": export_kwh,
        "water_kwh": water_kwh,
        "batt_charge_kwh": batt_charge_kwh,
        "batt_discharge_kwh": batt_discharge_kwh,
        "soc_end_percent": soc_percent,
        "created_at": datetime.now(UTC).isoformat(),
    }

    logger.info(
        f"Recording observation for {slot_start}: SOC={soc_percent}% "
        f"PV={pv_kwh:.3f}kWh Load={load_kwh:.3f}kWh Water={water_kwh:.3f}kWh Bat={battery_kw:.3f}kW"
    )

    # Store
    df = pd.DataFrame([record])
    await store.store_slot_observations(df)
    await store.close()  # Clean up async engine connections


async def _sleep_until_next_quarter() -> None:
    """Sleep until the next 15-minute boundary (UTC-based)."""
    now = datetime.now(UTC)
    minute_block = (now.minute // 15) * 15
    current_slot = now.replace(minute=minute_block, second=0, microsecond=0)
    next_slot = current_slot + timedelta(minutes=15)
    sleep_seconds = max(5.0, (next_slot - now).total_seconds())
    await asyncio.sleep(sleep_seconds)


async def _run_analyst() -> None:
    """Run the Learning Analyst to update s_index_base_factor and bias adjustments."""
    try:
        from backend.learning.analyst import Analyst

        config = _load_config()
        print("[recorder] Running Analyst (Learning Loop)...")
        analyst = Analyst(config)
        await analyst.update_learning_overlays()
    except Exception as e:
        print(f"[recorder] Analyst failed: {e}")


async def main() -> int:
    """Background recorder loop: capture observations every 15 minutes."""
    print("[recorder] Starting live observation recorder (15m cadence)")

    config = _load_config()
    tz_name = config.get("timezone", "Europe/Stockholm")
    tz = pytz.timezone(tz_name)

    # Run backfill on startup
    try:
        # BackfillEngine.run is now async.
        backfill = BackfillEngine()
        await backfill.run()
    except Exception as e:
        print(f"[recorder] Backfill failed: {e}")

    # Run Analyst on startup
    await _run_analyst()

    # Track last analyst run date to run once daily at ~6 AM local
    last_analyst_date = datetime.now(tz).date()

    # Initialize disaggregator (REV // ML2)
    disaggregator = LoadDisaggregator(config)

    while True:
        try:
            await record_observation_from_current_state(config, disaggregator)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"[recorder] Error while recording observation: {exc}")

        # Run Analyst once per day around 6 AM local time
        now_local = datetime.now(tz)
        if now_local.date() > last_analyst_date and now_local.hour >= 6:
            print(f"[recorder] Daily Analyst run triggered ({now_local.date()})")
            await _run_analyst()
            last_analyst_date = now_local.date()

        await _sleep_until_next_quarter()


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
