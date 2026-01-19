import logging
from typing import Any

from inputs import get_ha_sensor_float

from .base import DeferrableLoad, LoadType

logger = logging.getLogger("loads")


class LoadDisaggregator:
    """Service to manage controllable loads and separate them from base load."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.loads_registry: dict[str, DeferrableLoad] = {}
        self.metrics = {
            "negative_base_load_count": 0,
            "total_calculations": 0,
            "sensor_failures": 0,
        }
        self._initialize_loads()

    def _initialize_loads(self):
        """Initialize loads from configuration."""
        load_configs = self.config.get("deferrable_loads", [])
        input_sensors = self.config.get("input_sensors", {})

        for lc in load_configs:
            load_id = lc.get("id")
            if not load_id:
                logger.warning("Found deferrable load config without ID, skipping.")
                continue

            name = lc.get("name", load_id)
            sensor_key = lc.get("sensor_key")
            l_type_str = lc.get("type", "variable")
            nominal_power = lc.get("nominal_power_kw", 0.0)

            # Map type string to enum
            try:
                l_type = LoadType(l_type_str)
            except ValueError:
                logger.warning(
                    f"Invalid load type '{l_type_str}' for load '{load_id}', defaulting to variable"
                )
                l_type = LoadType.VARIABLE

            # Use entity ID from input_sensors if sensor_key is a key, else assume it's an entity ID
            entity_id = input_sensors.get(sensor_key)
            if not entity_id:
                if sensor_key and "." in sensor_key:
                    entity_id = sensor_key
                else:
                    logger.warning(
                        f"No entity ID found for load '{load_id}' with sensor_key '{sensor_key}'"
                    )
                    continue

            load = DeferrableLoad(
                load_id=load_id,
                name=name,
                sensor_key=entity_id,
                load_type=l_type,
                nominal_power_kw=nominal_power,
            )
            self.register_load(load)

    def register_load(self, load: DeferrableLoad):
        """Register a load in the disaggregator."""
        self.loads_registry[load.id] = load
        logger.info(f"Registered deferrable load: {load}")

    def get_load_by_id(self, load_id: str) -> DeferrableLoad | None:
        """Retrieve a registered load by its ID."""
        return self.loads_registry.get(load_id)

    def list_active_loads(self) -> list[DeferrableLoad]:
        """Return a list of all registered loads."""
        return list(self.loads_registry.values())

    async def update_current_power(self) -> float:
        """Fetch current power for all loads and return the total controllable load (kW)."""
        total_controllable_kw = 0.0

        for load in self.loads_registry.values():
            try:
                val = await get_ha_sensor_float(load.sensor_key)
                if val is None:
                    load.is_healthy = False
                    load.current_power_kw = 0.0
                    self.metrics["sensor_failures"] += 1
                    logger.debug(f"Sensor {load.sensor_key} unavailable for load {load.id}")
                else:
                    load.is_healthy = True
                    # Darkstar convention: sensors > 100 are likely Watts.
                    # Standard recorder practice (as seen in recorder.py) is to assume Watts.
                    load.current_power_kw = val / 1000.0
                    total_controllable_kw += load.current_power_kw
            except Exception as e:
                load.is_healthy = False
                self.metrics["sensor_failures"] += 1
                logger.error(f"Error updating power for load {load.id}: {e}")

        return total_controllable_kw

    def calculate_base_load(self, total_load_kw: float, controllable_kw: float) -> float:
        """
        Calculate base load by deducting controllable load from total load.
        Ensures base load is non-negative and tracks quality metrics.
        """
        self.metrics["total_calculations"] += 1
        base_load_kw = total_load_kw - controllable_kw

        if base_load_kw < -0.1:  # Significant negative drift
            self.metrics["negative_base_load_count"] += 1
            logger.warning(
                f"Negative base load detected: Total={total_load_kw:.3f}kW, "
                f"Controllable={controllable_kw:.3f}kW. Clamping to 0. "
                f"(Drift: {base_load_kw:.3f}kW)"
            )
            base_load_kw = 0.0
        elif base_load_kw < 0:
            base_load_kw = 0.0

        return base_load_kw

    def get_quality_metrics(self) -> dict[str, Any]:
        """Return current disaggregation quality metrics."""
        return {
            "metrics": self.metrics,
            "drift_rate": (
                self.metrics["negative_base_load_count"] / self.metrics["total_calculations"]
                if self.metrics["total_calculations"] > 0
                else 0
            ),
            "sensor_health": {lid: load.is_healthy for lid, load in self.loads_registry.items()},
        }
