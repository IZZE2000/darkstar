from unittest.mock import AsyncMock, patch

import pytest

from backend.loads.base import DeferrableLoad, LoadType
from backend.loads.service import LoadDisaggregator


@pytest.fixture
def mock_config():
    return {
        "deferrable_loads": [
            {
                "id": "water_heater",
                "name": "Water Heater",
                "sensor_key": "water_power_sensor",
                "type": "binary",
                "nominal_power_kw": 3.0,
            },
            {
                "id": "ev_charger",
                "name": "EV Charger",
                "sensor_key": "sensor.ev_power",
                "type": "variable",
                "nominal_power_kw": 11.0,
            },
        ],
        "input_sensors": {"water_power_sensor": "sensor.water_heater_power"},
    }


@pytest.fixture
def disaggregator(mock_config):
    return LoadDisaggregator(mock_config)


def test_load_registration(disaggregator):
    """Test that loads are correctly registered from config."""
    loads = disaggregator.list_active_loads()
    assert len(loads) == 2

    wh = disaggregator.get_load_by_id("water_heater")
    assert wh is not None
    assert wh.name == "Water Heater"
    assert wh.sensor_key == "sensor.water_heater_power"
    assert wh.type == LoadType.BINARY

    ev = disaggregator.get_load_by_id("ev_charger")
    assert ev.sensor_key == "sensor.ev_power"
    assert ev.type == LoadType.VARIABLE


@pytest.mark.asyncio
async def test_update_current_power(disaggregator):
    """Test fetching power from HA sensors and unit conversion."""
    with patch("backend.loads.service.get_ha_sensor_float", new_callable=AsyncMock) as mock_get:
        # sensor.water_heater_power -> 3000W, sensor.ev_power -> 5500W
        mock_get.side_effect = lambda sensor: 3000.0 if "water" in sensor else 5500.0

        total_controllable = await disaggregator.update_current_power()

        assert total_controllable == 8.5  # (3000 + 5500) / 1000
        assert disaggregator.get_load_by_id("water_heater").current_power_kw == 3.0
        assert disaggregator.get_load_by_id("ev_charger").current_power_kw == 5.5
        assert disaggregator.get_load_by_id("water_heater").is_healthy is True


@pytest.mark.asyncio
async def test_update_current_power_failure(disaggregator):
    """Test handling of sensor failures."""
    with patch("backend.loads.service.get_ha_sensor_float", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = lambda sensor: None if "water" in sensor else 5500.0

        total_controllable = await disaggregator.update_current_power()

        assert total_controllable == 5.5
        assert disaggregator.get_load_by_id("water_heater").is_healthy is False
        assert disaggregator.get_load_by_id("water_heater").current_power_kw == 0.0
        assert disaggregator.metrics["sensor_failures"] == 1


def test_calculate_base_load(disaggregator):
    """Test base load subtraction and quality metrics."""
    # Normal case
    base = disaggregator.calculate_base_load(total_load_kw=10.0, controllable_kw=3.0)
    assert base == 7.0
    assert disaggregator.metrics["total_calculations"] == 1

    # Negative base load (small drift)
    base = disaggregator.calculate_base_load(total_load_kw=2.0, controllable_kw=2.05)
    assert base == 0.0
    assert (
        disaggregator.metrics["negative_base_load_count"] == 0
    )  # Small drift (<0.1) shouldn't count

    # Negative base load (significant drift)
    base = disaggregator.calculate_base_load(total_load_kw=2.0, controllable_kw=3.0)
    assert base == 0.0
    assert disaggregator.metrics["negative_base_load_count"] == 1

    metrics = disaggregator.get_quality_metrics()
    assert metrics["metrics"]["negative_base_load_count"] == 1
    assert metrics["drift_rate"] == 1 / 3


def test_manual_load_registration(disaggregator):
    """Test dynamic load registration at runtime."""
    new_load = DeferrableLoad(
        load_id="dynamic_load",
        name="Dynamic",
        sensor_key="sensor.dynamic",
        load_type=LoadType.VARIABLE,
        nominal_power_kw=1.0,
    )
    disaggregator.register_load(new_load)
    assert disaggregator.get_load_by_id("dynamic_load") == new_load
    assert len(disaggregator.list_active_loads()) == 3
