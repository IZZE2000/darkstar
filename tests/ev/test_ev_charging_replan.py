"""
EV Charging Replan Tests (Rev EVFIX)

Production-grade test suite for EV plug-in replanning fixes.
Covers asyncio cross-thread dispatch, config path fixes, and executor gating.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from executor.config import EVChargerConfig
from executor.engine import ExecutorEngine


class TestEVReplanAsyncDispatch:
    """Test Task 1.1 & 1.2: asyncio cross-thread dispatch fixes."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create minimal config files for testing."""
        config = {
            "system": {
                "has_solar": True,
                "has_battery": True,
                "has_water_heater": False,
                "has_ev_charger": True,
                "grid_meter_type": "net",
            },
            "input_sensors": {
                "battery_soc": "sensor.test_battery",
                "pv_power": "sensor.test_pv",
                "load_power": "sensor.test_load",
            },
            "ev_chargers": [
                {
                    "enabled": True,
                    "name": "Test EV",
                    "replan_on_plugin": True,
                    "sensor": "sensor.test_ev_power",
                    "plug_sensor": "binary_sensor.test_ev_plug",
                }
            ],
            "battery": {"capacity_kwh": 10.0, "max_charge_kw": 5.0, "max_discharge_kw": 5.0},
            "executor": {
                "enabled": True,
                "shadow_mode": False,
                "interval_seconds": 300,
                "timezone": "Europe/Stockholm",
                "inverter": {},
                "ev_charger": {"switch_entity": "switch.test_ev"},
            },
        }

        secrets = {"home_assistant": {"url": "http://test", "token": "test_token"}}

        config_path = tmp_path / "config.yaml"
        secrets_path = tmp_path / "secrets.yaml"

        config_path.write_text(yaml.dump(config))
        secrets_path.write_text(yaml.dump(secrets))

        return str(config_path), str(secrets_path)

    @pytest.mark.asyncio
    async def test_trigger_ev_replan_uses_run_coroutine_threadsafe(self, mock_config, tmp_path):
        """Task 5.1: Verify run_coroutine_threadsafe is used (not create_task)."""
        _config_path, _secrets_path = mock_config

        # Change to temp directory so config files are found
        original_dir = Path.cwd()

        try:
            import os

            os.chdir(tmp_path)

            from backend.ha_socket import HAWebSocketClient

            client = HAWebSocketClient()

            # Set up the main event loop (simulating startup)
            loop = asyncio.get_event_loop()
            client.main_loop = loop

            # Mock run_coroutine_threadsafe to capture the call
            with patch("asyncio.run_coroutine_threadsafe") as mock_run_threadsafe:
                mock_future = MagicMock()
                mock_run_threadsafe.return_value = mock_future

                # Mock the scheduler service (imported inside the function)
                with patch(
                    "backend.services.scheduler_service.scheduler_service"
                ) as mock_scheduler:
                    mock_scheduler.trigger_now = AsyncMock(return_value=MagicMock(success=True))

                    # Call the trigger method
                    client._trigger_ev_replan()

                    # Assert run_coroutine_threadsafe was called (not create_task)
                    mock_run_threadsafe.assert_called_once()
                    # Verify the coroutine and loop were passed correctly
                    args = mock_run_threadsafe.call_args
                    assert args[0][1] == loop  # Second arg should be the main loop

                    # Verify add_done_callback was called
                    mock_future.add_done_callback.assert_called_once()
        finally:
            import os

            os.chdir(original_dir)


class TestEVReplanConfigPath:
    """Test Task 2.1 & 2.2: Config path reads from ev_chargers[]."""

    @pytest.fixture
    def mock_config_disabled_replan(self, tmp_path):
        """Create config with replan_on_plugin disabled."""
        config = {
            "system": {"has_ev_charger": True},
            "ev_chargers": [
                {
                    "enabled": True,
                    "name": "Test EV",
                    "replan_on_plugin": False,  # Disabled
                    "plug_sensor": "binary_sensor.test_plug",
                }
            ],
        }

        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(config))

        return str(config_path)

    @pytest.mark.asyncio
    async def test_trigger_ev_replan_reads_ev_chargers_array(self, tmp_path):
        """Task 5.2: Verify trigger respects replan_on_plugin=false in ev_chargers[]."""
        original_dir = Path.cwd()

        try:
            import os

            os.chdir(tmp_path)

            from backend.ha_socket import HAWebSocketClient

            client = HAWebSocketClient()
            client.main_loop = asyncio.get_event_loop()

            with patch("backend.services.scheduler_service.scheduler_service") as mock_scheduler:
                mock_scheduler.trigger_now = AsyncMock()

                with patch("asyncio.run_coroutine_threadsafe") as mock_run_threadsafe:
                    client._trigger_ev_replan()

                    # Should NOT trigger because replan_on_plugin=False
                    mock_run_threadsafe.assert_not_called()
                    mock_scheduler.trigger_now.assert_not_called()
        finally:
            import os

            os.chdir(original_dir)


class TestEVInitialStateOverride:
    """Test Task 3.1, 3.2 & 3.3: ev_plugged_in_override parameter."""

    @pytest.mark.asyncio
    async def test_get_initial_state_override_ev_plugged_in(self, tmp_path):
        """Task 5.3: Verify override skips HA REST fetch for ev_plugged_in."""
        config = {
            "system": {
                "has_ev_charger": True,
                "has_battery": False,
                "has_solar": False,
                "has_water_heater": False,
            },
            "ev_chargers": [
                {
                    "enabled": True,
                    "name": "Test EV",
                    "soc_sensor": "sensor.test_soc",
                    "plug_sensor": "binary_sensor.test_plug",
                }
            ],
            "input_sensors": {},
            "battery": {"capacity_kwh": 10.0},
        }

        secrets = {"home_assistant": {"url": "http://test", "token": "test"}}

        config_path = tmp_path / "config.yaml"
        secrets_path = tmp_path / "secrets.yaml"

        config_path.write_text(yaml.dump(config))
        secrets_path.write_text(yaml.dump(secrets))

        original_dir = Path.cwd()

        try:
            import os

            os.chdir(tmp_path)

            from inputs import get_initial_state

            # Mock HA sensor calls
            with patch("inputs.get_ha_sensor_float") as mock_float:
                mock_float.return_value = 50.0  # SoC value

                with patch("inputs.get_ha_bool") as mock_bool:
                    mock_bool.return_value = False  # Would normally return this

                    # Call with override=True
                    result = await get_initial_state(
                        config_path=str(config_path), ev_plugged_in_override=True
                    )

                    # Verify ev_plugged_in is True from override
                    assert result["ev_plugged_in"] is True

                    # Verify get_ha_bool was NOT called for plug sensor
                    # (it may be called for other things, but not for ev_plugged_in)
                    plug_calls = [
                        call for call in mock_bool.call_args_list if "test_plug" in str(call)
                    ]
                    assert len(plug_calls) == 0, (
                        "Should not fetch plug state from HA when override provided"
                    )
        finally:
            import os

            os.chdir(original_dir)


class TestExecutorEVSwitchGating:
    """Test Task 4.x: Executor switch gating hardening."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create minimal executor config."""
        config = {
            "system": {
                "has_solar": True,
                "has_battery": True,
                "has_water_heater": False,
                "has_ev_charger": True,
                "grid_meter_type": "net",
            },
            "input_sensors": {
                "battery_soc": "sensor.test_battery",
                "pv_power": "sensor.test_pv",
                "load_power": "sensor.test_load",
            },
            "battery": {"capacity_kwh": 10.0},
            "executor": {
                "enabled": True,
                "shadow_mode": True,  # Use shadow mode to avoid actual HA calls
                "interval_seconds": 300,
                "timezone": "Europe/Stockholm",
                "inverter": {"work_mode_entity": "sensor.work_mode"},
                "ev_charger": {
                    "switch_entity": "switch.test_ev",
                },
            },
            "ev_chargers": [
                {
                    "enabled": True,
                    "name": "Test EV",
                    "sensor": "sensor.test_ev_power",
                }
            ],
        }

        secrets = {"home_assistant": {"url": "http://test", "token": "test_token"}}

        config_path = tmp_path / "config.yaml"
        secrets_path = tmp_path / "secrets.yaml"

        config_path.write_text(yaml.dump(config))
        secrets_path.write_text(yaml.dump(secrets))

        return str(config_path)

    @pytest.mark.asyncio
    async def test_executor_ev_switch_not_opened_without_schedule(self, mock_config):
        """Task 5.4: Verify switch stays OFF when actual charging but no schedule."""
        from executor.override import SlotPlan, SystemState

        engine = ExecutorEngine(config_path=mock_config)

        # Mock the dependencies
        engine._has_ev_charger = True
        engine._has_battery = True
        engine.config.ev_charger = EVChargerConfig(switch_entity="switch.test_ev")

        # Create a slot with NO scheduled EV charging
        slot = SlotPlan(
            charge_kw=0.0,
            discharge_kw=3.0,
            export_kw=0.0,
            load_kw=1.0,
            water_kw=0.0,
            ev_charging_kw=0.0,  # No scheduled charging
            soc_target=50,
            soc_projected=50,
        )

        # Mock _control_ev_charger to capture what value is passed
        with patch.object(engine, "_control_ev_charger", new_callable=AsyncMock) as mock_control:
            # Mock the load disaggregator to return actual EV charging
            mock_disaggregator = MagicMock()
            mock_disaggregator.update_current_power = AsyncMock()
            mock_disaggregator.get_total_ev_power.return_value = 3.5  # Actual charging detected
            engine._load_disaggregator = mock_disaggregator

            # Mock other dependencies
            engine.ha_client = MagicMock()
            engine.dispatcher = MagicMock()

            # Mock _gather_system_state
            state = SystemState(current_soc_percent=50.0)
            with (
                patch.object(
                    engine, "_gather_system_state", new_callable=AsyncMock, return_value=state
                ),
                patch.object(
                    engine, "_load_current_slot", return_value=(slot, "2024-01-01T00:00:00")
                ),
                patch("executor.engine.make_decision") as mock_decision,
            ):
                mock_decision.return_value = MagicMock(
                    mode_intent="self_consumption",
                    reason="Test",
                    charge_value=0,
                    discharge_value=10,
                    soc_target=50,
                    water_temp=40,
                    source="test",
                )

                # Run the tick
                await engine._tick()

                # Verify _control_ev_charger was called with should_charge=False
                # (because no scheduled charging, even though actual charging detected)
                mock_control.assert_called_once()
                call_args = mock_control.call_args[0]
                should_charge = call_args[0]

                # Should be False because only scheduled_ev_charging should enable switch
                assert should_charge is False, "Switch should remain OFF without scheduled charging"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
