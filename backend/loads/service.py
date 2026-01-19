import logging
from typing import Any

from inputs import get_ha_sensor_float

from .base import DeferrableLoad, LoadType

logger = logging.getLogger("loads")


class LoadDisaggregator:
    """Service to manage controllable loads and separate them from base load."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.loads: list[DeferrableLoad] = []
        self._initialize_loads()

    def _initialize_loads(self):
        """Initialize loads from configuration."""
        load_configs = self.config.get("deferrable_loads", [])
        input_sensors = self.config.get("input_sensors", {})

        for lc in load_configs:
            load_id = lc.get("id")
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

            # Use entity ID from input_sensors if sensor_key is a key, else assume it's an entity ID?
            # Standard practice in this repo seems to be using keys into input_sensors.
            entity_id = input_sensors.get(sensor_key)
            if not entity_id:
                # Fallback: maybe sensor_key is the entity ID itself (e.g. sensor.xyz)
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
                sensor_key=entity_id,  # Store the actual entity ID
                load_type=l_type,
                nominal_power_kw=nominal_power,
            )
            self.loads.append(load)
            logger.info(f"Registered deferrable load: {load}")

    async def update_current_power(self) -> float:
        """Fetch current power for all loads and return the total controllable load (kW)."""
        total_controllable_kw = 0.0

        for load in self.loads:
            try:
                val = await get_ha_sensor_float(load.sensor_key)
                if val is None:
                    load.is_healthy = False
                    load.current_power_kw = 0.0
                    logger.debug(f"Sensor {load.sensor_key} unavailable for load {load.id}")
                else:
                    load.is_healthy = True
                    # Darkstar convention: sensors > 100 are likely Watts.
                    # We'll use a safer check or assuming Watts if it's from HA.
                    # Most power sensors in HA are W.
                    load.current_power_kw = val / 1000.0 if val > 1.0 or val < -1.0 else val
                    # Wait, if it's 0.5 kW it would be treated as kW.
                    # Let's check recorder.py logic again.
                    # recorder.py: return val / 1000.0 (unconditional / 1000.0 if not None)
                    # Actually recorder.py says:
                    # def get_kw(key, default=0.0):
                    #     ...
                    #     return val / 1000.0
                    # So it ALWAYS assumes Watts.
                    load.current_power_kw = val / 1000.0
                    total_controllable_kw += load.current_power_kw
            except Exception as e:
                load.is_healthy = False
                logger.error(f"Error updating power for load {load.id}: {e}")

        return total_controllable_kw

    def calculate_base_load(self, total_load_kw: float, controllable_kw: float) -> float:
        """
        Calculate base load by deducting controllable load from total load.
        Ensures base load is non-negative.
        """
        base_load_kw = total_load_kw - controllable_kw

        if base_load_kw < 0:
            if abs(base_load_kw) > 0.1:  # Allow small drift
                logger.warning(
                    f"Negative base load detected: Total={total_load_kw:.3f}kW, "
                    f"Controllable={controllable_kw:.3f}kW. Clamping to 0."
                )
            base_load_kw = 0.0

        return base_load_kw
