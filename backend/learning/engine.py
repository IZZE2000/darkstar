import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pytz
import yaml

from backend.learning.store import LearningStore


class LearningEngine:
    """
    Learning engine for auto-tuning and forecast calibration.
    Unified AsyncIO architecture (REV ARC11).
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.learning_config = self.config.get("learning", {})
        self.db_path = self.learning_config.get("sqlite_path", "data/planner_learning.db")
        self.timezone = pytz.timezone(self.config.get("timezone", "Europe/Stockholm"))

        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize Store
        self.store = LearningStore(self.db_path, self.timezone)

        raw_map = self.learning_config.get("sensor_map", {}) or {}
        # Corrected: {entity_id: canonical} -> {entity_id: canonical}
        self.sensor_map = {str(k).lower(): str(v).lower() for k, v in raw_map.items()}

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with Path(config_path).open(encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Fallback to default config
            with Path("config.default.yaml").open(encoding="utf-8") as f:
                return yaml.safe_load(f)

    # Delegate storage methods to store (Async)
    async def store_slot_prices(self, price_rows: Any) -> None:
        await self.store.store_slot_prices(price_rows)

    async def store_slot_observations(self, observations_df: pd.DataFrame) -> None:
        await self.store.store_slot_observations(observations_df)

    async def store_forecasts(self, forecasts: list[dict], forecast_version: str) -> None:
        await self.store.store_forecasts(forecasts, forecast_version)

    async def log_training_episode(
        self, input_data: dict, schedule_df: pd.DataFrame, config_overrides: dict | None = None
    ) -> None:
        """
        Log a training episode (inputs + outputs) for RL.
        Also logs the planned schedule to slot_plans for metric tracking.
        """
        # 1. Log to training_episodes (Legacy/Debug only)
        # Defaults to False to prevent DB bloat (2GB+).
        if self.config.get("debug", {}).get("enable_training_episodes", False):
            episode_id = str(uuid.uuid4())

            inputs_json = json.dumps(input_data, default=str)
            schedule_json = schedule_df.to_json(orient="records", date_format="iso")
            context_json = None  # TODO: Capture context if available
            config_overrides_json = json.dumps(config_overrides) if config_overrides else None

            await self.store.store_training_episode(
                episode_id=episode_id,
                inputs_json=inputs_json,
                schedule_json=schedule_json,
                context_json=context_json,
                config_overrides_json=config_overrides_json,
            )

        # 2. Log to slot_plans
        await self.store.store_plan(schedule_df)

    def _canonical_sensor_name(self, name: str) -> str:
        """Map incoming sensor names to canonical identifiers."""
        key = str(name).lower()
        if key in self.sensor_map:
            return self.sensor_map[key]

        stripped = key.replace("sensor.", "")
        # Remove common inverter/brand prefixes
        for brand in ("inverter_", "sungrow_", "goodwe_", "victron_", "fronius_"):
            stripped = stripped.replace(brand, "")

        for token in (
            "energy_",
            "power_",
            "total_",
            "cumulative_",
            "_kw",
            "_kwh",
            "_current",
            "_production",
            "_consumption",
        ):
            stripped = stripped.replace(token, "")
        stripped = stripped.strip("_")

        # Explicit handling for compound names often found in HA
        if stripped in ("load_consumption", "house_load"):
            return "load"
        if stripped in ("pv_production", "solar_yield", "solar"):
            return "pv"
        if stripped in ("grid_import", "energy_import", "from_grid"):
            return "import"
        if stripped in ("grid_export", "energy_export", "to_grid"):
            return "export"

        aliases = {
            "import": {"grid_import", "gridin", "import", "grid", "from_grid", "energy_import"},
            "export": {"grid_export", "gridout", "export", "to_grid", "energy_export"},
            "pv": {"pv", "solar", "pvproduction", "production", "yield", "solar_yield"},
            "load": {"load", "consumption", "house", "usage", "load_consumption", "house_load"},
            "water": {"water", "vvb", "waterheater", "heater"},
            "soc": {"soc", "battery_soc", "socpercent", "battery"},
        }
        for canonical, names in aliases.items():
            if stripped in names:
                return canonical
        return stripped or key

    def etl_cumulative_to_slots(
        self,
        cumulative_data: dict[str, list[tuple[datetime, float]]],
        resolution_minutes: int = 15,
    ) -> pd.DataFrame:
        """
        Convert cumulative sensor data to 15-minute slot deltas.
        This remains CPU-bound but is efficient enough for small batches.
        Large batches should be run in to_thread.
        """
        slot_records: dict[str, pd.DataFrame] = {}
        for sensor_name, data in cumulative_data.items():
            if data:
                df = pd.DataFrame(data, columns=["timestamp", "cumulative_value"])
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                if df["timestamp"].dt.tz is None:
                    df["timestamp"] = df["timestamp"].dt.tz_localize(self.timezone)
                else:
                    df["timestamp"] = df["timestamp"].dt.tz_convert(self.timezone)
                df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
                slot_records[sensor_name] = df

        if not slot_records:
            return pd.DataFrame()

        all_timestamps = []
        for df in slot_records.values():
            all_timestamps.extend(df["timestamp"].tolist())

        if not all_timestamps:
            return pd.DataFrame()

        min_ts = min(all_timestamps)
        max_ts = max(all_timestamps)

        if min_ts.tzinfo is None:
            min_ts = min_ts.replace(tzinfo=self.timezone)
        else:
            min_ts = min_ts.astimezone(self.timezone)

        floored_minute = (min_ts.minute // resolution_minutes) * resolution_minutes
        start_time = min_ts.replace(minute=floored_minute, second=0, microsecond=0)
        end_time = max_ts

        slots = pd.date_range(
            start=start_time,
            end=end_time,
            freq=f"{resolution_minutes}min",
            tz=self.timezone,
            inclusive="both",
        )

        slot_df = pd.DataFrame({"slot_start": slots[:-1], "slot_end": slots[1:]})

        for sensor_name, df in slot_records.items():
            canonical = self._canonical_sensor_name(sensor_name)
            if canonical == "soc":
                continue

            base_series = df.set_index("timestamp")["cumulative_value"]
            reindexed = base_series.reindex(slots, method="ffill")
            reindexed = reindexed.ffill().fillna(0)
            raw_diff = reindexed.diff().fillna(0)

            # Basic spike filtering
            deltas = raw_diff.clip(lower=0)
            slot_df[f"{canonical}_kwh"] = deltas.iloc[1:].values

        if any(self._canonical_sensor_name(name) == "soc" for name in slot_records):
            soc_name = next(
                name for name in slot_records if self._canonical_sensor_name(name) == "soc"
            )
            soc_series = (
                slot_records[soc_name]
                .set_index("timestamp")["cumulative_value"]
                .reindex(slots, method="ffill")
                .ffill()
            )
            slot_df["soc_start_percent"] = soc_series.iloc[:-1].values
            slot_df["soc_end_percent"] = soc_series.iloc[1:].values

        slot_df["duration_minutes"] = resolution_minutes
        # Ensure ISO strings for storage if needed, but LearningStore expects datetime objects usually?
        # Actually, store_slot_observations converts to dict, so strings are safer but LearningStore might handle it.
        # REV ARC11: We prefer keeping them as datetime objects if possible, but let's follow the previous pattern.
        slot_df["slot_start"] = slot_df["slot_start"].map(lambda x: x.isoformat())
        slot_df["slot_end"] = slot_df["slot_end"].map(lambda x: x.isoformat())
        return slot_df

    def etl_power_to_slots(
        self,
        power_data: dict[str, list[tuple[datetime, float]]],
        resolution_minutes: int = 15,
    ) -> pd.DataFrame:
        """
        Convert instantaneous power sensor data (W) to energy (kWh) per slot.
        Specifically optimized for backfill to populate bars in ChartCard.
        """

        slot_records: dict[str, pd.DataFrame] = {}
        for sensor_name, data in power_data.items():
            if data:
                df = pd.DataFrame(data, columns=["timestamp", "power_value"])
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                if df["timestamp"].dt.tz is None:
                    df["timestamp"] = df["timestamp"].dt.tz_localize(self.timezone)
                else:
                    df["timestamp"] = df["timestamp"].dt.tz_convert(self.timezone)
                df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
                slot_records[sensor_name] = df

        if not slot_records:
            return pd.DataFrame()

        all_timestamps = []
        for df in slot_records.values():
            all_timestamps.extend(df["timestamp"].tolist())

        if not all_timestamps:
            return pd.DataFrame()

        min_ts = min(all_timestamps)
        max_ts = max(all_timestamps)
        min_ts = min_ts.astimezone(self.timezone)

        floored_minute = (min_ts.minute // resolution_minutes) * resolution_minutes
        start_time = min_ts.replace(minute=floored_minute, second=0, microsecond=0)

        slots = pd.date_range(
            start=start_time,
            end=max_ts,
            freq=f"{resolution_minutes}min",
            tz=self.timezone,
            inclusive="both",
        )
        if len(slots) < 2:
            return pd.DataFrame()

        slot_df = pd.DataFrame({"slot_start": slots[:-1], "slot_end": slots[1:]})
        hours_per_slot = resolution_minutes / 60.0

        for sensor_name, df in slot_records.items():
            canonical = self._canonical_sensor_name(sensor_name)

            if canonical == "soc":
                # SoC is a level, handled at the end
                continue

            # Average power (W) over the slot
            # We use 'resample' to get the mean power in each 15min bucket
            resampled = (
                df.set_index("timestamp")["power_value"]
                .resample(f"{resolution_minutes}min")
                .mean()
                .reindex(slots[:-1])
                .fillna(0)
            )

            # Convert W to kWh: (W / 1000) * hours_per_slot
            energy_kwh = (resampled / 1000.0) * hours_per_slot

            if canonical == "battery":
                # Battery sign: + discharge, - charge
                slot_df["batt_discharge_kwh"] = energy_kwh.clip(lower=0).values
                slot_df["batt_charge_kwh"] = energy_kwh.clip(upper=0).abs().values
            elif canonical in ("grid", "import", "export"):
                if canonical == "grid":
                    # Grid sign: + import, - export
                    slot_df["import_kwh"] = energy_kwh.clip(lower=0).values
                    slot_df["export_kwh"] = energy_kwh.clip(upper=0).abs().values
                elif canonical == "import":
                    slot_df["import_kwh"] = energy_kwh.values
                elif canonical == "export":
                    slot_df["export_kwh"] = energy_kwh.values
            else:
                # Standard consumption/production (PV, Load, Water)
                slot_df[f"{canonical}_kwh"] = energy_kwh.values

        # Handle SoC (which is a level, not power)
        soc_name = next(
            (name for name in slot_records if self._canonical_sensor_name(name) == "soc"), None
        )
        if soc_name:
            soc_series = (
                slot_records[soc_name]
                .set_index("timestamp")["power_value"]
                .reindex(slots, method="ffill")
                .ffill()
            )
            slot_df["soc_start_percent"] = soc_series.iloc[:-1].values
            slot_df["soc_end_percent"] = soc_series.iloc[1:].values

        # Ensure all expected columns exist (even if 0) to avoid SQLAlchemy issues
        for col in ["pv_kwh", "load_kwh", "import_kwh", "export_kwh", "water_kwh"]:
            if col not in slot_df.columns:
                slot_df[col] = 0.0

        slot_df["duration_minutes"] = resolution_minutes
        slot_df["slot_start"] = slot_df["slot_start"].map(lambda x: x.isoformat())
        slot_df["slot_end"] = slot_df["slot_end"].map(lambda x: x.isoformat())

        return slot_df

    async def calculate_metrics(self, days_back: int = 7) -> dict[str, Any]:
        """Calculate learning metrics for the last N days using the store."""
        return await self.store.calculate_metrics(days_back)

    async def get_status(self) -> dict[str, Any]:
        """Get current status of the learning engine."""
        last_obs = await self.store.get_last_observation_time()
        episodes = await self.store.get_episodes_count()

        return {
            "status": "active",
            "last_observation": last_obs.isoformat() if last_obs else None,
            "training_episodes": episodes,
            "db_path": self.db_path,
            "timezone": str(self.timezone),
        }

    async def get_performance_series(self, days_back: int = 7) -> dict[str, list[dict]]:
        """
        Get time-series data for performance visualization using the store.
        """
        return await self.store.get_performance_series(days_back)
