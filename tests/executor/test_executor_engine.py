"""
Tests for Executor Engine Integration

Integration tests for the full ExecutorEngine with mocked HA client and schedule.json.
"""

import contextlib
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytz
from sqlalchemy import create_engine

from backend.learning.models import Base
from executor.actions import HAClient
from executor.config import (
    ControllerConfig,
    EVChargerDeviceConfig,
    ExecutorConfig,
    InverterConfig,
    NotificationConfig,
    WaterHeaterConfig,
)
from executor.engine import EVChargerState, ExecutorEngine, ExecutorStatus
from executor.override import SlotPlan


@pytest.fixture
def temp_schedule():
    """Create a temporary schedule.json file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        schedule_path = f.name

    yield schedule_path

    with contextlib.suppress(OSError):
        Path(schedule_path).unlink()


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Create schema
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    yield db_path

    with contextlib.suppress(OSError):
        Path(db_path).unlink()


def make_schedule(slots: list, timezone: str = "Europe/Stockholm") -> dict:
    """Create a schedule payload with given slots."""
    return {
        "schedule": slots,
        "meta": {
            "generated_at": datetime.now(pytz.timezone(timezone)).isoformat(),
        },
    }


def make_slot(
    start: datetime,
    charge_kw: float = 0,
    export_kwh: float = 0,
    water_kw: float = 0,
    soc_target: int = 50,
) -> dict:
    """Create a slot entry."""
    end = start + timedelta(minutes=15)
    return {
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "end_time_kepler": end.isoformat(),
        "battery_charge_kw": charge_kw,
        "battery_discharge_kw": 0,
        "export_kwh": export_kwh,
        "water_heating_kw": water_kw,
        "soc_target_percent": soc_target,
        "projected_soc_percent": soc_target - 5,
    }


class TestExecutorStatus:
    """Test ExecutorStatus dataclass."""

    def test_default_values(self):
        """ExecutorStatus has sensible defaults."""
        status = ExecutorStatus()
        assert status.enabled is False
        assert status.shadow_mode is False
        assert status.last_run_status == "pending"

    def test_custom_values(self):
        """ExecutorStatus accepts custom values."""
        status = ExecutorStatus(enabled=True, shadow_mode=True)
        assert status.enabled is True
        assert status.shadow_mode is True


class TestExecutorEngineInit:
    """Test ExecutorEngine initialization."""

    def test_creates_history_manager(self, temp_db):
        """Engine creates ExecutionHistory on init."""
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path="schedule.json",
                timezone="Europe/Stockholm",
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    engine = ExecutorEngine("config.yaml")

                    assert engine.history is not None


class TestLoadCurrentSlot:
    """Test ExecutorEngine._load_current_slot."""

    @pytest.fixture
    def engine(self, temp_schedule, temp_db):
        """Create an engine with temp files."""
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    engine = ExecutorEngine("config.yaml")
                    engine.config.schedule_path = temp_schedule
                    yield engine

    def test_no_schedule_file_returns_none(self, engine):
        """Missing schedule file returns None."""
        engine.config.schedule_path = "/nonexistent/schedule.json"
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)

        slot, slot_start = engine._load_current_slot(now)

        assert slot is None
        assert slot_start is None

    def test_empty_schedule_returns_none(self, engine, temp_schedule):
        """Empty schedule returns None."""
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump({"schedule": []}, f)

        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)

        slot, _slot_start = engine._load_current_slot(now)

        assert slot is None

    def test_finds_current_slot(self, engine, temp_schedule):
        """Finds slot containing current time."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        # Create a slot that spans now
        slot_start = now - timedelta(minutes=5)

        schedule = make_schedule(
            [
                make_slot(slot_start, charge_kw=5.0, soc_target=80),
            ]
        )
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        slot, start_iso = engine._load_current_slot(now)

        assert slot is not None
        assert slot.charge_kw == 5.0
        assert slot.soc_target == 80
        assert start_iso is not None

    def test_no_matching_slot_returns_none(self, engine, temp_schedule):
        """Returns None when no slot matches current time."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        # Create slots in the past
        old_slot = now - timedelta(hours=2)

        schedule = make_schedule(
            [
                make_slot(old_slot, charge_kw=5.0),
            ]
        )
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        slot, _ = engine._load_current_slot(now)

        assert slot is None


class TestParseSlotPlan:
    """Test ExecutorEngine._parse_slot_plan."""

    @pytest.fixture
    def engine(self, temp_schedule, temp_db):
        """Create an engine."""
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    yield ExecutorEngine("config.yaml")

    def test_parses_charge_slot(self, engine):
        """Parses a charging slot correctly."""
        slot_data = {
            "battery_charge_kw": 5.0,
            "battery_discharge_kw": 0.0,
            "export_kwh": 0.0,
            "water_heating_kw": 0.0,
            "soc_target_percent": 80,
            "projected_soc_percent": 75,
        }

        slot = engine._parse_slot_plan(slot_data)

        assert slot.charge_kw == 5.0
        assert slot.discharge_kw == 0.0
        assert slot.soc_target == 80

    def test_parses_export_slot(self, engine):
        """Parses an export slot correctly (kWh to kW conversion)."""
        slot_data = {
            "battery_charge_kw": 0.0,
            "export_kwh": 2.0,  # 2 kWh per 15-min slot = 8 kW
            "soc_target_percent": 50,
        }

        slot = engine._parse_slot_plan(slot_data)

        assert slot.export_kw == 8.0  # 2 kWh * 4 = 8 kW

    def test_handles_missing_fields(self, engine):
        """Handles missing/null fields gracefully."""
        slot_data = {
            "soc_target_percent": 60,
        }

        slot = engine._parse_slot_plan(slot_data)

        assert slot.charge_kw == 0.0
        assert slot.export_kw == 0.0
        assert slot.soc_target == 60


class TestQuickActions:
    """Test ExecutorEngine quick action system."""

    @pytest.fixture
    def engine(self, temp_schedule, temp_db):
        """Create an engine."""
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    yield ExecutorEngine("config.yaml")

    def test_set_quick_action(self, engine):
        """Can set a quick action."""
        result = engine.set_quick_action("force_charge", 30)

        assert result["success"] is True
        assert result["type"] == "force_charge"
        assert result["duration_minutes"] == 30
        assert "expires_at" in result

    def test_invalid_action_type_raises(self, engine):
        """Invalid action type raises ValueError."""
        with pytest.raises(ValueError):
            engine.set_quick_action("invalid_action", 30)

    def test_invalid_duration_raises(self, engine):
        """Invalid duration raises ValueError."""
        with pytest.raises(ValueError):
            engine.set_quick_action("force_charge", 45)  # Must be 15, 30, or 60

    def test_get_active_quick_action(self, engine):
        """Can retrieve active quick action."""
        engine.set_quick_action("force_export", 60)

        action = engine.get_active_quick_action()

        assert action is not None
        assert action["type"] == "force_export"
        assert action["remaining_minutes"] > 0

    def test_clear_quick_action(self, engine):
        """Can clear a quick action."""
        engine.set_quick_action("force_charge", 30)

        result = engine.clear_quick_action()

        assert result["success"] is True
        assert result["was_active"] is True

        # Should now be None
        assert engine.get_active_quick_action() is None


class TestGetStatus:
    """Test ExecutorEngine.get_status."""

    @pytest.fixture
    def engine(self, temp_schedule, temp_db):
        """Create an engine."""
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                enabled=True,
                shadow_mode=False,
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    yield ExecutorEngine("config.yaml")

    def test_get_status_returns_dict(self, engine):
        """get_status returns a dictionary with expected keys."""
        status = engine.get_status()

        assert isinstance(status, dict)
        assert "enabled" in status
        assert "shadow_mode" in status
        assert "version" in status
        assert "quick_action" in status

    def test_get_status_reflects_config(self, engine):
        """Status reflects config values."""
        engine.status.enabled = True
        engine.status.shadow_mode = False

        status = engine.get_status()

        assert status["enabled"] is True
        assert status["shadow_mode"] is False


@pytest.mark.asyncio
class TestRunOnce:
    """Test ExecutorEngine.run_once (single tick)."""

    @pytest.fixture
    def engine(self, temp_schedule, temp_db):
        """Create an engine with mocked HA client."""
        with patch("executor.engine.load_executor_config") as mock_config:
            config = ExecutorConfig(
                enabled=True,
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
                automation_toggle_entity="input_boolean.automation",
                inverter=InverterConfig(),
                water_heater=WaterHeaterConfig(),
                notifications=NotificationConfig(),
                controller=ControllerConfig(),
            )
            mock_config.return_value = config

            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {"input_sensors": {}}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    engine = ExecutorEngine("config.yaml")

                    # Mock HA client
                    mock_ha = MagicMock(spec=HAClient)

                    # Default mock behavior: return "on" for booleans, "50" for numbers
                    def side_effect_get_state(entity_id):
                        if "input_boolean" in entity_id or "automation" in entity_id:
                            return "on"
                        if "soc" in entity_id:
                            return "50"
                        if "temp" in entity_id or "target" in entity_id:
                            return "55"
                        return "0.0"

                    mock_ha.get_state_value.side_effect = side_effect_get_state
                    mock_ha.set_select_option.return_value = True
                    mock_ha.set_switch.return_value = True
                    mock_ha.set_number.return_value = True
                    mock_ha.set_input_number.return_value = True
                    engine.ha_client = mock_ha

                    # Create dispatcher
                    from executor.actions import ActionDispatcher

                    engine.dispatcher = ActionDispatcher(mock_ha, config, shadow_mode=False)

                    yield engine

    async def test_run_once_returns_result(self, engine, temp_schedule):
        """run_once returns a result dict."""
        # Create empty schedule
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump({"schedule": []}, f)

        result = await engine.run_once()

        assert isinstance(result, dict)
        assert "success" in result
        assert "executed_at" in result
        assert "actions" in result

    async def test_run_once_skips_when_automation_off(self, engine, temp_schedule):
        """run_once skips when automation toggle is off."""
        engine.ha_client.get_state_value.side_effect = None
        engine.ha_client.get_state_value.return_value = "off"

        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump({"schedule": []}, f)

        result = await engine.run_once()

        assert result["success"] is True
        # Check that it was skipped
        assert any(a.get("reason") == "automation_disabled" for a in result["actions"])

    async def test_run_once_executes_with_schedule(self, engine, temp_schedule):
        """run_once executes actions when schedule exists."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        slot_start = now - timedelta(minutes=5)

        schedule = make_schedule(
            [
                make_slot(slot_start, charge_kw=5.0, soc_target=80),
            ]
        )
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        result = await engine.run_once()

        assert result["success"] is True
        assert len(result["actions"]) > 0

    async def test_run_once_logs_to_history(self, engine, temp_schedule):
        """run_once logs execution to history."""
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump({"schedule": []}, f)

        await engine.run_once()

        # Check history has the record
        records = engine.history.get_history()
        assert len(records) >= 1

    async def test_tick_calls_set_water_temp_when_enabled(self, engine, temp_schedule):
        """_tick calls set_water_temp when water heater is enabled."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        slot_start = now - timedelta(minutes=5)

        # Enable water heater and set target entity
        engine._has_water_heater = True
        engine.config.water_heater.target_entity = "input_number.water_heater_target"

        schedule = make_schedule(
            [
                make_slot(slot_start, water_kw=3.0, soc_target=50),
            ]
        )
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        # Mock the dispatcher's set_water_temp method (it's async)
        from unittest.mock import AsyncMock

        from executor.actions import ActionResult

        mock_result = ActionResult(
            action_type="water_temp",
            success=True,
            message="Set water temp to 50°C",
            previous_value=40,
            new_value=50,
            entity_id="input_number.water_heater_target",
            skipped=False,
        )
        engine.dispatcher.set_water_temp = AsyncMock(return_value=mock_result)

        result = await engine.run_once()

        # Assert set_water_temp was called
        engine.dispatcher.set_water_temp.assert_called_once()
        # Assert the result is in the actions
        assert any(a.get("type") == "water_temp" for a in result["actions"])

    async def test_ev_charging_kw_logged_in_execution_record(self, engine, temp_schedule):
        """ev_charging_kw from slot plan is included in the execution record (task 6.2)."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        slot_start = now - timedelta(minutes=5)

        # Write a schedule with ev_charging_kw
        end = slot_start + timedelta(minutes=15)
        slot = {
            "start_time": slot_start.isoformat(),
            "end_time": end.isoformat(),
            "end_time_kepler": end.isoformat(),
            "battery_charge_kw": 0,
            "battery_discharge_kw": 0,
            "export_kwh": 0,
            "water_heating_kw": 0,
            "soc_target_percent": 50,
            "projected_soc_percent": 45,
            "ev_charging_kw": 7.4,
        }
        schedule = make_schedule([slot])
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        result = await engine.run_once()

        assert result is not None
        records = engine.history.get_recent(limit=1)
        assert records
        assert records[0]["ev_charging_kw"] == pytest.approx(7.4)

    async def test_non_ev_slot_logs_zero_ev_charging_kw(self, engine, temp_schedule):
        """Non-EV slot logs ev_charging_kw = 0.0 in execution record."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        slot_start = now - timedelta(minutes=5)

        schedule = make_schedule([make_slot(slot_start, charge_kw=3.0, soc_target=80)])
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        result = await engine.run_once()

        assert result is not None
        records = engine.history.get_recent(limit=1)
        assert records
        assert records[0]["ev_charging_kw"] == pytest.approx(0.0)

    async def test_tick_skips_water_temp_when_disabled(self, engine, temp_schedule):
        """_tick skips set_water_temp when water heater is disabled."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        slot_start = now - timedelta(minutes=5)

        # Disable water heater
        engine._has_water_heater = False
        engine.config.water_heater.target_entity = "input_number.water_heater_target"

        schedule = make_schedule(
            [
                make_slot(slot_start, water_kw=3.0, soc_target=50),
            ]
        )
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        # Mock the dispatcher's set_water_temp method (it's async)
        from unittest.mock import AsyncMock

        engine.dispatcher.set_water_temp = AsyncMock()

        result = await engine.run_once()

        # Assert set_water_temp was NOT called
        engine.dispatcher.set_water_temp.assert_not_called()
        # Assert no water_temp action in results
        assert not any(a.get("type") == "water_temp" for a in result["actions"])


class TestGetStatusModeIntent:
    """Tests for mode_intent in get_status() (tasks 6.1 and 6.3)."""

    @pytest.fixture
    def engine(self, temp_schedule, temp_db):
        """Create an engine with temp files."""
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    engine = ExecutorEngine("config.yaml")
                    engine.config.schedule_path = temp_schedule
                    yield engine

    @pytest.mark.parametrize(
        "charge_kw,export_kw,discharge_kw,soc_target,ev_kw,soc_pct,expected_mode",
        [
            (5.0, 0.0, 0.0, 80, 0.0, 50.0, "charge"),
            (0.0, 3.0, 3.0, 10, 0.0, 80.0, "export"),
            (0.0, 0.0, 0.0, 10, 0.0, 80.0, "self_consumption"),
            (0.0, 0.0, 0.0, 80, 0.0, 50.0, "idle"),
        ],
    )
    def test_get_status_returns_mode_intent_for_modes(
        self,
        engine,
        temp_schedule,
        charge_kw,
        export_kw,
        discharge_kw,
        soc_target,
        ev_kw,
        soc_pct,
        expected_mode,
    ):
        """get_status() returns correct mode_intent in current_slot_plan (task 6.1)."""
        from executor.override import SystemState

        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        slot_start = now - timedelta(minutes=5)
        end = slot_start + timedelta(minutes=15)

        slot = {
            "start_time": slot_start.isoformat(),
            "end_time": end.isoformat(),
            "end_time_kepler": end.isoformat(),
            "battery_charge_kw": charge_kw,
            "battery_discharge_kw": discharge_kw,
            "export_kwh": export_kw * 0.25,  # kWh for 15-min slot
            "water_heating_kw": 0.0,
            "soc_target_percent": soc_target,
            "projected_soc_percent": soc_target - 5,
            "ev_charging_kw": ev_kw,
        }
        schedule = make_schedule([slot])
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        # Provide a cached system state with the test SoC
        engine._last_system_state = SystemState(current_soc_percent=soc_pct)

        status = engine.get_status()

        assert status["current_slot_plan"] is not None
        assert status["current_slot_plan"]["mode_intent"] == expected_mode

    def test_get_status_mode_intent_null_when_no_cached_state(self, engine, temp_schedule):
        """get_status() sets mode_intent to null when no system state is cached (task 6.3)."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        slot_start = now - timedelta(minutes=5)
        end = slot_start + timedelta(minutes=15)

        slot = {
            "start_time": slot_start.isoformat(),
            "end_time": end.isoformat(),
            "end_time_kepler": end.isoformat(),
            "battery_charge_kw": 5.0,
            "battery_discharge_kw": 0.0,
            "export_kwh": 0.0,
            "water_heating_kw": 0.0,
            "soc_target_percent": 80,
            "projected_soc_percent": 75,
        }
        schedule = make_schedule([slot])
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        # No cached system state
        engine._last_system_state = None

        status = engine.get_status()

        assert status["current_slot_plan"] is not None
        assert status["current_slot_plan"]["mode_intent"] is None
        # Other fields should still be populated
        assert status["current_slot_plan"]["charge_kw"] == pytest.approx(5.0)

    def test_get_status_mode_intent_null_when_no_profile(self, engine, temp_schedule):
        """get_status() sets mode_intent to null when profile is not loaded (task 6.3)."""
        from executor.override import SystemState

        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        slot_start = now - timedelta(minutes=5)
        end = slot_start + timedelta(minutes=15)

        slot = {
            "start_time": slot_start.isoformat(),
            "end_time": end.isoformat(),
            "end_time_kepler": end.isoformat(),
            "battery_charge_kw": 5.0,
            "battery_discharge_kw": 0.0,
            "export_kwh": 0.0,
            "water_heating_kw": 0.0,
            "soc_target_percent": 80,
            "projected_soc_percent": 75,
        }
        schedule = make_schedule([slot])
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        # Profile is None (not loaded)
        engine._last_system_state = SystemState(current_soc_percent=50.0)
        engine.inverter_profile = None

        status = engine.get_status()

        assert status["current_slot_plan"] is not None
        assert status["current_slot_plan"]["mode_intent"] is None
        # Other fields should still be populated
        assert status["current_slot_plan"]["charge_kw"] == pytest.approx(5.0)


class TestParseSlotPlanPerDevice:
    """Task 6.10: _parse_slot_plan correctly extracts per-device EV plans."""

    @pytest.fixture
    def engine(self, temp_schedule, temp_db):
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    yield ExecutorEngine("config.yaml")

    def test_parses_per_device_ev_plans(self, engine):
        """ev_chargers dict in slot data is parsed into ev_charger_plans."""
        slot_data = {
            "soc_target_percent": 50,
            "ev_chargers": {"ev1": 7.4, "ev2": 11.0},
        }
        slot = engine._parse_slot_plan(slot_data)

        assert slot.ev_charger_plans == {"ev1": 7.4, "ev2": 11.0}

    def test_empty_ev_chargers_dict(self, engine):
        """Empty dict produces empty ev_charger_plans."""
        slot_data = {
            "soc_target_percent": 50,
            "ev_chargers": {},
        }
        slot = engine._parse_slot_plan(slot_data)

        assert slot.ev_charger_plans == {}

    def test_missing_ev_chargers_field(self, engine):
        """Missing ev_chargers field produces empty ev_charger_plans."""
        slot_data = {"soc_target_percent": 50}
        slot = engine._parse_slot_plan(slot_data)

        assert slot.ev_charger_plans == {}

    def test_old_format_ev_charging_kw_still_parsed(self, engine):
        """Backward compat: old ev_charging_kw scalar is still parsed as aggregate."""
        slot_data = {
            "soc_target_percent": 50,
            "ev_charging_kw": 7.4,
        }
        slot = engine._parse_slot_plan(slot_data)

        assert slot.ev_charging_kw == pytest.approx(7.4)
        # No chargers configured in this fixture, so no per-device plans
        assert slot.ev_charger_plans == {}

    def test_old_format_fallback_maps_to_first_charger(self, temp_schedule, temp_db):
        """Old-format schedule maps aggregate ev_charging_kw to first configured charger."""
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
                ev_chargers=[EVChargerDeviceConfig(id="ev1", switch_entity="switch.ev1")],
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    eng = ExecutorEngine("config.yaml")

        slot_data = {"soc_target_percent": 50, "ev_charging_kw": 7.4}
        slot = eng._parse_slot_plan(slot_data)

        assert slot.ev_charging_kw == pytest.approx(7.4)
        assert slot.ev_charger_plans == {"ev1": pytest.approx(7.4)}


class TestControlEvChargerPerDevice:
    """Task 6.10: _control_ev_charger loops over configured chargers independently."""

    @pytest.fixture
    def engine(self, temp_schedule, temp_db):
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
                ev_chargers=[
                    EVChargerDeviceConfig(id="ev1", switch_entity="switch.ev1"),
                    EVChargerDeviceConfig(id="ev2", switch_entity="switch.ev2"),
                ],
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    eng = ExecutorEngine("config.yaml")
                    eng._has_ev_charger = True
                    yield eng

    @pytest.mark.asyncio
    async def test_per_device_state_initialized_independently(self, engine):
        """Each charger gets its own EVChargerState entry after control loop."""
        from unittest.mock import AsyncMock, MagicMock

        engine.ha_client = AsyncMock()
        engine.ha_client.get_state_value = AsyncMock(return_value="off")

        mock_result = MagicMock(
            success=True,
            skipped=False,
            duration_ms=5,
            action_type="switch",
            message="ok",
            entity_id="switch.ev1",
            previous_value=None,
            new_value="off",
            verified_value="off",
            verification_success=True,
            error_details=None,
        )
        engine.dispatcher = AsyncMock()
        engine.dispatcher.set_ev_charger_switch = AsyncMock(return_value=mock_result)

        slot = SlotPlan(
            charge_kw=0.0,
            discharge_kw=0.0,
            export_kw=0.0,
            load_kw=0.0,
            water_kw=0.0,
            ev_charging_kw=0.0,
            soc_target=50,
            soc_projected=50,
            ev_charger_plans={},
        )

        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        await engine._control_ev_charger(slot, now)

        # Both chargers should have state entries after control loop runs
        assert "ev1" in engine._ev_charger_states
        assert "ev2" in engine._ev_charger_states
        assert isinstance(engine._ev_charger_states["ev1"], EVChargerState)
        assert isinstance(engine._ev_charger_states["ev2"], EVChargerState)

    @pytest.mark.asyncio
    async def test_charger_without_switch_entity_skipped(self, temp_schedule, temp_db):
        """Charger with no switch_entity is skipped (no HA call)."""
        from unittest.mock import AsyncMock

        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
                ev_chargers=[
                    EVChargerDeviceConfig(id="ev_no_switch", switch_entity=None),
                ],
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    eng = ExecutorEngine("config.yaml")
                    eng._has_ev_charger = True

        eng.ha_client = AsyncMock()
        eng.dispatcher = AsyncMock()

        slot = SlotPlan(
            charge_kw=0.0,
            discharge_kw=0.0,
            export_kw=0.0,
            load_kw=0.0,
            water_kw=0.0,
            ev_charging_kw=0.0,
            soc_target=50,
            soc_projected=50,
            ev_charger_plans={"ev_no_switch": 7.4},
        )

        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        await eng._control_ev_charger(slot, now)

        # No switch calls should have been made
        eng.dispatcher.set_ev_charger_switch.assert_not_called()

    @pytest.mark.asyncio
    async def test_safety_timeout_stops_charger(self, engine):
        """Charger running without plan for >30 min triggers safety stop."""
        from datetime import timedelta
        from unittest.mock import AsyncMock, MagicMock

        engine.ha_client = AsyncMock()
        engine.ha_client.get_state_value = AsyncMock(return_value="on")

        mock_result = MagicMock(
            success=True,
            skipped=False,
            duration_ms=5,
            action_type="switch",
            message="ok",
            entity_id="switch.ev1",
            previous_value="on",
            new_value="off",
            verified_value="off",
            verification_success=True,
            error_details=None,
        )
        engine.dispatcher = AsyncMock()
        engine.dispatcher.set_ev_charger_switch = AsyncMock(return_value=mock_result)

        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)

        # Simulate charger has been running for 45 minutes without a plan
        engine._ev_charger_states["ev1"] = EVChargerState(
            charging_active=True,
            charging_started_at=now - timedelta(minutes=45),
            charging_slot_end=now - timedelta(minutes=30),
        )

        # No plan for ev1 (plan = 0.0)
        slot = SlotPlan(
            charge_kw=0.0,
            discharge_kw=0.0,
            export_kw=0.0,
            load_kw=0.0,
            water_kw=0.0,
            ev_charging_kw=0.0,
            soc_target=50,
            soc_projected=50,
            ev_charger_plans={"ev1": 0.0},
        )

        await engine._control_ev_charger(slot, now)

        # The charger should have been turned off due to safety timeout
        calls = engine.dispatcher.set_ev_charger_switch.call_args_list
        assert any(
            ("switch.ev1" in str(c) and "False" in str(c))
            or (c.args and c.args[0] == "switch.ev1" and c.kwargs.get("turn_on") is False)
            for c in calls
        ), "Expected safety-timeout stop call for switch.ev1"


class TestGetStatusEvChargerPlans:
    """Task 6.10: get_status() includes per-device EV plan."""

    @pytest.fixture
    def engine(self, temp_schedule, temp_db):
        with patch("executor.engine.load_executor_config") as mock_config:
            mock_config.return_value = ExecutorConfig(
                schedule_path=temp_schedule,
                timezone="Europe/Stockholm",
            )
            with patch("executor.engine.load_yaml") as mock_yaml:
                mock_yaml.return_value = {}
                with patch.object(ExecutorEngine, "_get_db_path", return_value=temp_db):
                    yield ExecutorEngine("config.yaml")

    def test_get_status_includes_ev_charger_plans(self, engine, temp_schedule):
        """get_status() returns ev_charger_plans in current_slot_plan."""
        from executor.override import SystemState

        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        slot_start = now - timedelta(minutes=5)
        end = slot_start + timedelta(minutes=15)

        slot = {
            "start_time": slot_start.isoformat(),
            "end_time": end.isoformat(),
            "end_time_kepler": end.isoformat(),
            "battery_charge_kw": 0.0,
            "battery_discharge_kw": 0.0,
            "export_kwh": 0.0,
            "water_heating_kw": 0.0,
            "soc_target_percent": 50,
            "projected_soc_percent": 45,
            "ev_charging_kw": 7.4,
            "ev_chargers": {"main_ev": 7.4},
        }
        schedule = make_schedule([slot])
        with Path(temp_schedule).open("w", encoding="utf-8") as f:
            json.dump(schedule, f)

        engine._last_system_state = SystemState(current_soc_percent=50.0)
        engine.inverter_profile = None

        status = engine.get_status()

        assert status["current_slot_plan"] is not None
        assert "ev_charger_plans" in status["current_slot_plan"]
        assert status["current_slot_plan"]["ev_charger_plans"] == {"main_ev": 7.4}
