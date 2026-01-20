import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytz
import yaml

from backend.learning import get_learning_engine

# Configure logging
logger = logging.getLogger(__name__)


class BackfillEngine:
    """
    Handles backfilling of missing observations from Home Assistant history and MariaDB.
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.engine = get_learning_engine(config_path)
        self.store = self.engine.store
        self.ha_config = self._load_ha_config()
        self.timezone = pytz.timezone(self.config.get("timezone", "Europe/Stockholm"))
        self.learning_config = self.config.get("learning", {})

        # Load secrets for backfill fallback (HA)
        self.secrets = self._load_secrets()

    def _load_config(self, path: str) -> dict:
        try:
            with Path(path).open(encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    def _load_secrets(self) -> dict:
        try:
            with Path("secrets.yaml").open(encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    def _load_ha_config(self) -> dict:
        """Load HA config from secrets.yaml"""
        secrets = self._load_secrets()
        return secrets.get("home_assistant", {})

    def _make_ha_headers(self) -> dict[str, str]:
        token = self.ha_config.get("token")
        if not token:
            return {}
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _fetch_history(
        self, entity_id: str, start_time: datetime, end_time: datetime
    ) -> list[tuple[datetime, float]]:
        """Fetch history for a single entity from HA asynchronously."""
        url = self.ha_config.get("url")
        if not url or not entity_id:
            return []

        api_url = f"{url.rstrip('/')}/api/history/period/{start_time.isoformat()}"
        params = {
            "filter_entity_id": entity_id,
            "end_time": end_time.isoformat(),
            "significant_changes_only": False,
            "minimal_response": False,
        }

        try:
            logger.info(f"Fetching history for {entity_id} from {start_time} to {end_time}")

            # Add small delay to avoid overwhelming HA
            import asyncio

            await asyncio.sleep(0.5)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url, headers=self._make_ha_headers(), params=params)
                response.raise_for_status()
                data = response.json()

            if not data or not data[0]:
                logger.info(f"No history found for {entity_id}")
                return []

            history = []
            for state in data[0]:
                try:
                    ts = datetime.fromisoformat(state["last_changed"])
                    val = float(state["state"])
                    history.append((ts, val))
                except (ValueError, TypeError, KeyError):
                    continue
            logger.info(f"Retrieved {len(history)} points for {entity_id}")
            if history:
                logger.info(f"First point for {entity_id}: {history[0]}, Last point: {history[-1]}")
            return history

        except Exception as e:
            logger.error(f"Failed to fetch history for {entity_id}: {e}")
            return []

    async def detect_gaps(self, days: int = 10) -> list[dict[str, Any]]:
        """
        Detect missing observation slots in the last N days.
        Returns a list of gap ranges: [{"start_time": ISO, "end_time": ISO, "missing_slots": int}]
        """
        tz = self.timezone
        now = datetime.now(tz)
        start_time = now - timedelta(days=days)

        # Truncate to 15-minute boundaries
        start_time = start_time.replace(
            minute=start_time.minute - (start_time.minute % 15), second=0, microsecond=0
        )

        logger.info(f"Gap detection: now={now}, start_time={start_time}, days={days}")

        # Generate expected slots
        expected_slots = set()
        current = start_time
        while current < now:
            expected_slots.add(current.astimezone(tz).isoformat())
            current += timedelta(minutes=15)

        # Query existing slots
        from sqlalchemy import select

        from backend.learning.models import SlotObservation

        existing_slots = set()
        async with self.store.AsyncSession() as session:
            stmt = select(
                SlotObservation.slot_start,
                SlotObservation.soc_end_percent,
                SlotObservation.pv_kwh,
                SlotObservation.load_kwh,
                SlotObservation.batt_charge_kwh,
                SlotObservation.batt_discharge_kwh,
            ).where(
                SlotObservation.slot_start >= start_time.astimezone(tz).isoformat(),
                SlotObservation.slot_start < now.astimezone(tz).isoformat(),
            )
            result = await session.execute(stmt)

            for row in result:
                # Check for slots that exist but have missing actual sensor data
                is_valid = True

                # SoC Check
                if row.soc_end_percent is None or (
                    isinstance(row.soc_end_percent, float) and math.isnan(row.soc_end_percent)
                ):
                    is_valid = False

                # PV Check
                if row.pv_kwh is None or (isinstance(row.pv_kwh, float) and math.isnan(row.pv_kwh)):
                    is_valid = False

                # Load Check
                if row.load_kwh is None or (
                    isinstance(row.load_kwh, float) and math.isnan(row.load_kwh)
                ):
                    is_valid = False

                # Battery Power Check - if both charge and discharge are None/NaN/0, consider invalid
                if (
                    row.batt_charge_kwh is None
                    or (isinstance(row.batt_charge_kwh, float) and math.isnan(row.batt_charge_kwh))
                ) and (
                    row.batt_discharge_kwh is None
                    or (
                        isinstance(row.batt_discharge_kwh, float)
                        and math.isnan(row.batt_discharge_kwh)
                    )
                ):
                    is_valid = False

                if is_valid:
                    existing_slots.add(row.slot_start)

        # Find missing
        missing = sorted(expected_slots - existing_slots)
        if not missing:
            return []

        # Group into contiguous ranges
        gaps = []
        current_gap_start = missing[0]
        current_gap_end = missing[0]
        count = 1

        for i in range(1, len(missing)):
            curr_dt = datetime.fromisoformat(missing[i])
            prev_dt = datetime.fromisoformat(missing[i - 1])

            if (curr_dt - prev_dt) == timedelta(minutes=15):
                current_gap_end = missing[i]
                count += 1
            else:
                gaps.append(
                    {
                        "start_time": current_gap_start,
                        "end_time": current_gap_end,
                        "missing_slots": count,
                    }
                )
                current_gap_start = missing[i]
                current_gap_end = missing[i]
                count = 1

        # Append last gap
        gaps.append(
            {
                "start_time": current_gap_start,
                "end_time": current_gap_end,
                "missing_slots": count,
            }
        )
        return gaps

    async def run(self) -> None:
        """Run the backfill process asynchronously targeting detected gaps."""
        logger.info("Starting backfill process...")

        # 1. Detect gaps
        gaps = await self.detect_gaps(days=10)
        if not gaps:
            logger.info("Data is up to date. No gaps found.")
            return

        total_missing = sum(g["missing_slots"] for g in gaps)
        logger.info(f"Found {len(gaps)} gap ranges totaling {total_missing} missing slots.")

        # 2. Identify sensors to fetch
        raw_map = self.learning_config.get("sensor_map")
        logger.info(f"Initial raw_map from config: {raw_map}")

        if not raw_map:
            logger.info("sensor_map is empty. Auto-detecting from input_sensors...")
            input_sensors = self.config.get("input_sensors", {})
            raw_map = {}
            # We ONLY map power-based config keys to ensure etl_power_to_slots works correctly.
            # Cumulative sensors (total_*) should NOT be used here.
            mapping = {
                "pv_power": "pv",
                "load_power": "load",
                "battery_power": "battery",
                "grid_power": "grid",
                "grid_import_power": "import",
                "grid_export_power": "export",
                "water_power": "water",
                "battery_soc": "soc",
            }
            for config_key, canonical in mapping.items():
                entity_id = input_sensors.get(config_key)
                if entity_id:
                    # Guard: ensure we don't accidentally pick up total/energy sensors if user misconfigured
                    if "total" in entity_id or "energy" in entity_id:
                        logger.warning(
                            f"Config key '{config_key}' points to cumulative sensor '{entity_id}'. Backfill usually expects power (W)."
                        )
                    raw_map[entity_id] = canonical
            logger.info(f"Auto-detected raw_map: {raw_map}")

        if not raw_map:
            logger.warning(
                "No sensors identified for backfill (sensor_map and input_sensors empty)."
            )
            return

        logger.info(f"Final backfill raw_map: {raw_map}")

        # 3. Process each gap range (with chunking for large gaps)

        for gap in gaps:
            start_time = datetime.fromisoformat(gap["start_time"])
            end_time = datetime.fromisoformat(gap["end_time"]) + timedelta(minutes=15)

            # Chunk large gaps to avoid overwhelming HA
            gap_duration_hours = (end_time - start_time).total_seconds() / 3600
            if gap_duration_hours > 6:  # Chunk if larger than 6 hours
                logger.info(
                    f"Large gap detected ({gap_duration_hours:.1f}h), chunking into 6h pieces"
                )

                current_start = start_time
                while current_start < end_time:
                    current_end = min(current_start + timedelta(hours=6), end_time)
                    chunk_slots = int(
                        (current_end - current_start).total_seconds() / 900
                    )  # 15min slots

                    logger.info(
                        f"Processing chunk: {current_start} to {current_end} ({chunk_slots} slots)"
                    )
                    await self._process_gap_chunk(current_start, current_end, raw_map)

                    current_start = current_end
                continue

            logger.info(
                f"Processing gap range: {start_time} to {end_time} ({gap['missing_slots']} slots)"
            )
            await self._process_gap_chunk(start_time, end_time, raw_map)

        logger.info("Backfill complete.")

    async def _process_gap_chunk(
        self, start_time: datetime, end_time: datetime, raw_map: dict
    ) -> None:
        """Process a single gap chunk."""
        import asyncio

        cumulative_data: dict[str, list[tuple[datetime, float]]] = {}
        count = 0
        for entity_id, canonical in raw_map.items():
            logger.debug(f"Process mapping: {entity_id} -> {canonical}")
            history = await self._fetch_history(str(entity_id), start_time, end_time)
            if history:
                # Resample to 1-minute intervals to save memory
                resampled = self._resample_history(history)
                cumulative_data[str(entity_id)] = resampled
                count += len(resampled)
                logger.debug(f"Resampled {len(history)} -> {len(resampled)} points for {entity_id}")
            else:
                logger.warning(f"No history for {entity_id} ({canonical})")

        if not cumulative_data:
            logger.warning(f"No history data found for gap {start_time} to {end_time}")
            return

        # ETL to slots
        df = await asyncio.to_thread(self.engine.etl_power_to_slots, cumulative_data)
        if df.empty:
            logger.warning(f"ETL produced empty DataFrame for gap {start_time} to {end_time}")
            return

        # Store
        await self.engine.store_slot_observations(df)
        await self.store.store_execution_logs_from_df(df)
        logger.info(f"Gap range {start_time} to {end_time} backfilled.")

    def _resample_history(
        self, history: list[tuple[datetime, float]], interval: str = "1min"
    ) -> list[tuple[datetime, float]]:
        """Downsample raw HA data to 1-minute intervals to reduce memory usage."""
        if not history:
            return []

        import pandas as pd

        try:
            df = pd.DataFrame(history, columns=["ts", "val"])
            df = df.set_index("ts")
            # Resample: mean() works well for power.
            # We use dropna() because if there's no data in a minute, we don't want to invent it yet
            # (etl_power_to_slots handles filling)
            resampled = df.resample(interval).mean().dropna()

            # Convert back to list of tuples
            return list(zip(resampled.index.to_pydatetime(), resampled["val"], strict=True))
        except Exception as e:
            logger.error(f"Failed to resample history: {e}")
            return history  # Fallback to raw data
