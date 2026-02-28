import asyncio
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytz
import yaml

from backend.learning.backfill import BackfillEngine

# Local imports
from backend.learning.store import LearningStore
from backend.loads.service import LoadDisaggregator
from inputs import get_current_slot_prices, get_ha_sensor_float, get_ha_sensor_kw_normalized

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("recorder")


def _load_config() -> dict[str, Any]:
    try:
        with Path("config.yaml").open(encoding="utf-8") as f:
            result: Any = yaml.safe_load(f)
            if isinstance(result, dict):
                return result  # type: ignore[return-value]
            return {}
    except FileNotFoundError:
        return {}


async def record_observation_from_current_state(
    config: dict[str, Any] | None = None, disaggregator: LoadDisaggregator | None = None
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

    # Helper to get sensor value and convert W to kW if needed.
    # Uses get_ha_sensor_kw_normalized which reads unit_of_measurement from HA
    # and only divides by 1000 when the sensor reports in Watts.
    # This correctly handles both W-reporting (most inverters) and
    # kW-reporting (Fronius SolarNet) sensors automatically.
    async def get_kw(key: str, default: float = 0.0) -> float:
        entity = input_sensors.get(key)
        if not entity:
            return default
        val = await get_ha_sensor_kw_normalized(str(entity))
        if val is None:
            return default
        return val

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
    import_kw: float = 0.0
    export_kw: float = 0.0
    grid_net_kw: float = 0.0

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

    # Collect EV charging power from all configured EV chargers
    ev_charging_kw = 0.0
    ev_chargers = config.get("ev_chargers", [])
    for ev_charger in ev_chargers:
        if ev_charger.get("enabled", True):
            sensor = ev_charger.get("sensor")
            if sensor:
                try:
                    val = await get_ha_sensor_kw_normalized(str(sensor))
                    if val is not None:
                        ev_charging_kw += val
                except Exception:
                    pass  # Sensor not available, skip

    # Apply inversion flags if configured (REV F55)
    input_sensors = config.get("input_sensors", {})
    if input_sensors.get("battery_power_inverted", False):
        battery_kw = -battery_kw
        logger.debug(f"Applied battery_power_inverted: {battery_kw:.3f}kW")

    # Handle grid inversion for net meter type
    if meter_type == "net" and input_sensors.get("grid_power_inverted", False):
        grid_net_kw = -grid_net_kw
        import_kw = max(0.0, grid_net_kw)
        export_kw = max(0.0, -grid_net_kw)
        logger.debug(f"Applied grid_power_inverted: net={grid_net_kw:.3f}kW")

    # Estimate Energy for the 15m slot (kWh = avg_kW * 0.25h)
    # This is a Rough Approximation if we don't have cumulative counters
    # ideally we would diff cumulative counters.
    # For now, we store the snapshot rate converted to energy.
    pv_kwh = pv_kw * 0.25
    load_kwh = load_kw * 0.25
    import_kwh = import_kw * 0.25
    export_kwh = export_kw * 0.25
    water_kwh = water_kw * 0.25
    ev_charging_kwh = ev_charging_kw * 0.25

    # Standard inverter convention: positive = discharge, negative = charge
    batt_discharge_kwh = (battery_kw * 0.25) if battery_kw > 0 else 0.0
    batt_charge_kwh = (abs(battery_kw) * 0.25) if battery_kw < 0 else 0.0

    # Battery
    soc_entity = input_sensors.get("battery_soc")
    soc_percent = None
    if soc_entity:
        soc_percent = await get_ha_sensor_float(soc_entity)

    if soc_percent is None:
        # Fallback: Try to get last known SoC from DB
        cached_soc = await store.get_system_state("last_known_soc")
        if cached_soc and soc_entity:
            try:
                soc_percent = float(cached_soc)
                logger.warning(
                    f"Battery SoC sensor ({soc_entity}) unavailable. "
                    f"Using last known value: {soc_percent:.1f}%"
                )
            except ValueError:
                logger.error(
                    f"Cached SoC value is corrupted: '{cached_soc}'. "
                    "Cannot use fallback. Skipping observation."
                )
                soc_percent = None

        if soc_percent is None and soc_entity:
            logger.warning(
                f"Battery SoC sensor ({soc_entity}) unavailable and no valid cached value. "
                "Skipping observation record."
            )
            await store.close()
            return
    else:
        # Valid SoC obtained - update cache
        await store.set_system_state("last_known_soc", str(soc_percent))

    # Fetch Price Data (REV // Complete Cost Reality Fix)
    prices = await get_current_slot_prices(config)
    import_price = prices.get("import_price_sek_kwh") if prices else None
    export_price = prices.get("export_price_sek_kwh") if prices else None

    if prices:
        logger.info(f"Price data fetched: Import={import_price:.4f}, Export={export_price:.4f}")
    else:
        logger.warning("Failed to fetch price data for current observation")

    # Construct Record
    record = {
        "slot_start": slot_start,
        "slot_end": slot_end,
        "pv_kwh": pv_kwh,
        "load_kwh": load_kwh,
        "import_kwh": import_kwh,
        "export_kwh": export_kwh,
        "water_kwh": water_kwh,
        "ev_charging_kwh": ev_charging_kwh,
        "batt_charge_kwh": batt_charge_kwh,
        "batt_discharge_kwh": batt_discharge_kwh,
        "soc_end_percent": soc_percent,
        "import_price_sek_kwh": import_price,
        "export_price_sek_kwh": export_price,
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


async def run_analyst() -> None:
    """Run the Learning Analyst to update s_index_base_factor and bias adjustments."""
    try:
        from backend.learning.analyst import Analyst

        config = _load_config()
        print("[recorder] Running Analyst (Learning Loop)...")
        analyst = Analyst(config)
        await analyst.update_learning_overlays()
    except Exception as e:
        print(f"[recorder] Analyst failed: {e}")


async def backfill_missing_prices():
    """Backfill missing price data for historical observations."""
    try:
        from inputs import get_nordpool_data

        config = _load_config()
        db_path = config.get("learning", {}).get("sqlite_path", "data/planner_learning.db")
        tz_name = config.get("timezone", "Europe/Stockholm")
        tz = pytz.timezone(tz_name)

        store = LearningStore(db_path, tz)
        observations = await store.get_history_range(
            datetime.now(tz) - timedelta(days=30), datetime.now(tz)
        )

        missing_any = any(obs.get("import_price_sek_kwh") is None for obs in observations)
        if not missing_any:
            logger.info("[recorder] No missing prices to backfill.")
            await store.close()
            return

        logger.info("[recorder] Backfilling missing prices...")
        price_data = await get_nordpool_data()
        if not price_data:
            logger.error("[recorder] Failed to fetch price data for backfill.")
            await store.close()
            return

        indexed_prices = {p["start_time"]: p for p in price_data}
        updated_count = 0

        for obs in observations:
            if obs.get("import_price_sek_kwh") is None:
                slot_start_raw = obs["slot_start"]
                if isinstance(slot_start_raw, str):
                    slot_start = datetime.fromisoformat(slot_start_raw)
                else:
                    slot_start = slot_start_raw

                if slot_start.tzinfo is None:
                    slot_start = tz.localize(slot_start)
                else:
                    slot_start = slot_start.astimezone(tz)

                # Round to nearest 15/60 min boundary if needed, but get_nordpool_data handles it
                # We need exact match or closest previous
                price_slot = indexed_prices.get(slot_start)
                if price_slot:
                    obs["import_price_sek_kwh"] = price_slot["import_price_sek_kwh"]
                    obs["export_price_sek_kwh"] = price_slot["export_price_sek_kwh"]
                    updated_count += 1

        if updated_count > 0:
            # We need a way to update specific observations.
            # store.store_slot_prices handles upsert by slot_start.
            # Convert back to list of dicts with required fields
            rows_to_update = [
                {
                    "slot_start": obs["slot_start"],
                    "import_price_sek_kwh": obs["import_price_sek_kwh"],
                    "export_price_sek_kwh": obs["export_price_sek_kwh"],
                }
                for obs in observations
                if obs.get("import_price_sek_kwh") is not None
            ]
            await store.store_slot_prices(rows_to_update)
            logger.info(f"[recorder] Backfilled {updated_count} observation prices.")

        await store.close()
    except Exception as e:
        logger.error(f"[recorder] Price backfill failed: {e}")
        import traceback

        traceback.print_exc()


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
    await run_analyst()

    # Run Price Backfill on startup
    await backfill_missing_prices()

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
            await run_analyst()
            last_analyst_date = now_local.date()

        await _sleep_until_next_quarter()


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
