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
            start=start_time, end=end_time, freq=f"{resolution_minutes}min", tz=self.timezone
        )

        slot_df = pd.DataFrame({"slot_start": slots[:-1], "slot_end": slots[1:]})
        [{} for _ in range(len(slot_df))]  # Simplified type hint

        for sensor_name, df in slot_records.items():
            canonical = self._canonical_sensor_name(sensor_name)
            base_series = df.set_index("timestamp")["cumulative_value"]
            aligned = base_series.reindex(slots)
            gaps = aligned.isna()
            reindexed = base_series.reindex(slots, method="ffill")
            reindexed = reindexed.ffill().fillna(0)
            raw_diff = reindexed.diff().fillna(0)

            gap_mask = gaps | gaps.shift(1, fill_value=False)
            mask_spike = (raw_diff > 5.0) & ~gap_mask
            raw_diff[mask_spike] = 0.0
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
