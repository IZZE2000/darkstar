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
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(api_url, headers=self._make_ha_headers(), params=params)
                response.raise_for_status()
                data = response.json()

            if not data or not data[0]:
                return []

            history = []
            for state in data[0]:
                try:
                    ts = datetime.fromisoformat(state["last_changed"])
                    val = float(state["state"])
                    history.append((ts, val))
                except (ValueError, TypeError, KeyError):
                    continue
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
        if not raw_map:
            logger.info("sensor_map is empty. Auto-detecting from input_sensors...")
            input_sensors = self.config.get("input_sensors", {})
            raw_map = {}
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
                    raw_map[entity_id] = canonical

        if not raw_map:
            logger.warning(
                "No sensors identified for backfill (sensor_map and input_sensors empty)."
            )
            return

        # 3. Process each gap range
        import asyncio

        for gap in gaps:
            start_time = datetime.fromisoformat(gap["start_time"])
            end_time = datetime.fromisoformat(gap["end_time"]) + timedelta(minutes=15)

            logger.info(
                f"Processing gap range: {start_time} to {end_time} ({gap['missing_slots']} slots)"
            )

            cumulative_data: dict[str, list[tuple[datetime, float]]] = {}
            count = 0
            for entity_id, _canonical in raw_map.items():
                history = await self._fetch_history(str(entity_id), start_time, end_time)
                if history:
                    cumulative_data[str(entity_id)] = history
                    count += len(history)

            if not cumulative_data:
                logger.warning(f"No history data found for gap {start_time} to {end_time}")
                continue

            # ETL to slots
            df = await asyncio.to_thread(self.engine.etl_power_to_slots, cumulative_data)
            if df.empty:
                logger.warning(f"ETL produced empty DataFrame for gap {start_time} to {end_time}")
                continue

            # Store
            await self.engine.store_slot_observations(df)
            await self.store.store_execution_logs_from_df(df)
            logger.info(f"Gap range {start_time} to {end_time} backfilled.")

        logger.info("Backfill complete.")
