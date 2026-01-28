from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.recorder import record_observation_from_current_state


@pytest.fixture
def mock_config():
    return {
        "timezone": "Europe/Stockholm",
        "input_sensors": {
            "battery_power": "sensor.battery_power",
            "battery_soc": "sensor.battery_soc",
        },
        "learning": {"sqlite_path": ":memory:"},
    }


@pytest.mark.asyncio
@patch("backend.recorder._load_config")
@patch("backend.recorder.LearningStore")
@patch("backend.recorder.get_ha_sensor_float", new_callable=AsyncMock)
async def test_recorder_sign_convention_discharge(
    mock_get_sensor, mock_store_cls, mock_load_config, mock_config
):
    """
    Test standard convention: Positive battery power = Discharge
    """
    mock_load_config.return_value = mock_config

    # Setup mock store instance
    mock_store = MagicMock()
    # Mock async method on the store instance
    mock_store.store_slot_observations = AsyncMock()
    mock_store.initialize = AsyncMock()
    mock_store.get_system_state = AsyncMock(return_value=None)
    mock_store.set_system_state = AsyncMock()
    mock_store.close = AsyncMock()
    # Support async context manager
    mock_store.__aenter__ = AsyncMock(return_value=mock_store)
    mock_store.__aexit__ = AsyncMock(return_value=None)
    mock_store_cls.return_value = mock_store

    # Setup sensor values
    # +2.0 kW (Positive) -> Should be DISCHARGE in new logic
    async def get_sensor_side_effect(entity_id):
        if entity_id == "sensor.battery_power":
            return 2000.0  # 2000 Watts = 2.0 kW
        return 0.0

    mock_get_sensor.side_effect = get_sensor_side_effect

    # Run recorder
    await record_observation_from_current_state()

    # Verify store called with correct dataframe
    args, _ = mock_store.store_slot_observations.call_args
    df = args[0]

    # 2.0 kW for 15 mins = 0.5 kWh
    assert df.iloc[0]["batt_discharge_kwh"] == 0.5
    assert df.iloc[0]["batt_charge_kwh"] == 0.0


@pytest.mark.asyncio
@patch("backend.recorder._load_config")
@patch("backend.recorder.LearningStore")
@patch("backend.recorder.get_ha_sensor_float", new_callable=AsyncMock)
async def test_recorder_sign_convention_charge(
    mock_get_sensor, mock_store_cls, mock_load_config, mock_config
):
    """
    Test standard convention: Negative battery power = Charge
    """
    mock_load_config.return_value = mock_config
    mock_store = MagicMock()
    # Mock async method on the store instance
    mock_store.store_slot_observations = AsyncMock()
    mock_store.initialize = AsyncMock()
    mock_store.get_system_state = AsyncMock(return_value=None)
    mock_store.set_system_state = AsyncMock()
    mock_store.close = AsyncMock()
    # Support async context manager
    mock_store.__aenter__ = AsyncMock(return_value=mock_store)
    mock_store.__aexit__ = AsyncMock(return_value=None)
    mock_store_cls.return_value = mock_store

    # -2.0 kW (Negative) -> Should be CHARGE in new logic
    async def get_sensor_side_effect(entity_id):
        if entity_id == "sensor.battery_power":
            return -2000.0
        return 0.0

    mock_get_sensor.side_effect = get_sensor_side_effect

    await record_observation_from_current_state()

    args, _ = mock_store.store_slot_observations.call_args
    df = args[0]

    # 2.0 kW for 15 mins = 0.5 kWh
    assert df.iloc[0]["batt_charge_kwh"] == 0.5
    assert df.iloc[0]["batt_discharge_kwh"] == 0.0
