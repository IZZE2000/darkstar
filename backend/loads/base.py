from enum import Enum


class LoadType(Enum):
    BINARY = "binary"  # On/Off (e.g. some water heaters)
    VARIABLE = "variable"  # Variable power (e.g. smart EV chargers)


class DeferrableLoad:
    """Base class for loads that can be deferred or controlled."""

    def __init__(
        self,
        load_id: str,
        name: str,
        sensor_key: str,
        load_type: LoadType = LoadType.VARIABLE,
        nominal_power_kw: float = 0.0,
    ):
        self.id = load_id
        self.name = name
        self.sensor_key = sensor_key
        self.type = load_type
        self.nominal_power_kw = nominal_power_kw
        self.current_power_kw = 0.0
        self.is_healthy = True

    def __repr__(self) -> str:
        return (
            f"<DeferrableLoad id={self.id} type={self.type.value} power={self.current_power_kw}kW>"
        )
