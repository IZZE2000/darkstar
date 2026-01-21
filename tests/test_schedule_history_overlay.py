import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path.cwd()))


import pytest
import pytz
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.api.routers.schedule import schedule_today_with_history
from backend.learning.models import Base
from backend.learning.store import LearningStore


@pytest.mark.anyio
async def test_today_with_history_includes_planned_actions(tmp_path):
    # Setup temp DB
    db_path = tmp_path / "planner_learning.db"

    # Create tables using Base metadata for correctness
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Insert test data for today (UTC to avoid timezone confusion in test)
        tz = pytz.UTC
        now = datetime.now(tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Planned Charge Slot at 01:00 (Early today)
        slot_01 = today_start.replace(hour=1).isoformat()
        await conn.execute(
            text("""
            INSERT INTO slot_plans (slot_start, planned_charge_kwh, planned_discharge_kwh, planned_soc_percent, planned_export_kwh, planned_water_heating_kwh)
            VALUES (:slot_start, 0.5, 0.0, 50.0, 0.0, 0.25)
            """),
            {"slot_start": slot_01},
        )

        # 2. Planned Discharge Slot at 02:00
        slot_02 = today_start.replace(hour=2).isoformat()
        await conn.execute(
            text("""
            INSERT INTO slot_plans (slot_start, planned_charge_kwh, planned_discharge_kwh, planned_soc_percent, planned_export_kwh, planned_water_heating_kwh)
            VALUES (:slot_start, 0.0, 0.25, 40.0, 0.1, 0.0)
            """),
            {"slot_start": slot_02},
        )

    # Mock config to point to temp DB
    mock_config = {"learning": {"sqlite_path": str(db_path)}, "timezone": "UTC"}

    # Mock now to be 12:00 today, so 01:00/02:00 are historical
    fixed_now = today_start.replace(hour=12)

    with (
        patch("backend.api.routers.schedule.load_yaml", return_value=mock_config),
        patch("backend.api.routers.schedule.Path") as MockPath,
        patch("backend.api.routers.schedule.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = fixed_now
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
        mock_datetime.combine.side_effect = datetime.combine
        mock_datetime.min = datetime.min

        # Patch Path to hide schedule.json so we rely on DB + Plans
        real_Path = Path

        def side_effect(arg):
            if str(arg) == "schedule.json":
                m = MagicMock()
                m.exists.return_value = False
                return m
            return real_Path(arg)

        MockPath.side_effect = side_effect

        store = LearningStore(str(db_path), tz)
        result = await schedule_today_with_history(store=store)

    # Assertions
    slots = result["slots"]
    print(f"DEBUG: Returned {len(slots)} slots")

    assert len(slots) > 0

    found_charge = False
    found_discharge = False

    for slot in slots:
        # Times in response are ISO strings
        if "01:00:00" in slot["start_time"] and (
            slot.get("battery_charge_kw") == 2.0
            and slot.get("soc_target_percent") == 50.0
            and slot.get("water_heating_kw") == 1.0
        ):
            found_charge = True

        if (
            "02:00:00" in slot["start_time"]
            and slot.get("battery_discharge_kw") == 1.0
            and slot.get("export_kwh") == 0.1
        ):
            found_discharge = True

    assert found_charge, (
        "Did not find planned charge/water slot from DB (expected 2.0 kW charge, 1.0 kW water)"
    )
    assert found_discharge, (
        "Did not find planned discharge slot from DB (expected 1.0 kW discharge)"
    )


@pytest.mark.anyio
async def test_today_with_history_sets_executed_flag(tmp_path):
    """Verify that historical slots from observations have is_executed=True."""
    db_path = tmp_path / "planner_learning.db"

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Insert historical execution for "today start + 1 hour"
        tz = pytz.UTC
        now = datetime.now(tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        past_start = today_start + timedelta(hours=1)
        past_end = past_start + timedelta(minutes=15)

        # Insert 15 entries (one per minute) to simulate a full slot
        for i in range(15):
            t = past_start + timedelta(minutes=i)
            await conn.execute(
                text(
                    """
                    INSERT INTO execution_log
                    (executed_at, slot_start, planned_charge_kw, planned_discharge_kw, planned_export_kw, planned_water_kw, planned_soc_projected, success, override_active, source, commanded_unit)
                    VALUES (:at, :slot, 2.0, 0.0, 0.0, 0.0, 50, 1, 0, 'test', 'A')
                    """
                ),
                {"at": t.isoformat(), "slot": past_start.isoformat()},
            )

        # ALSO insert into slot_observations because that's what schedule.py actually reads!
        await conn.execute(
            text(
                """
                INSERT INTO slot_observations
                (slot_start, slot_end, batt_charge_kwh, soc_end_percent)
                VALUES (:slot, :slot_end, 0.5, 50.0)
                """
            ),
            {"slot": past_start.isoformat(), "slot_end": past_end.isoformat()},
        )

    # Mock config
    mock_config = {"learning": {"sqlite_path": str(db_path)}, "timezone": "UTC"}

    from unittest.mock import MagicMock, patch

    with (
        patch("backend.api.routers.schedule.load_yaml", return_value=mock_config),
        patch("backend.api.routers.schedule.Path") as MockPath,
    ):
        # Hide schedule.json so we rely on DB
        def side_effect(arg):
            if str(arg) == "schedule.json":
                m = MagicMock()
                m.exists.return_value = False
                return m
            return Path(arg)  # Use real path for DB

        MockPath.side_effect = side_effect

        from backend.api.routers.schedule import schedule_today_with_history

        store = LearningStore(str(db_path), tz)
        result = await schedule_today_with_history(store=store)

    slots = result["slots"]
    found_executed = False

    target_time_str = past_start.isoformat()

    for slot in slots:
        if slot["start_time"] == target_time_str and slot.get("is_executed") is True:
            found_executed = True
            # Also verify mapping of actual_charge_kw (0.5 kWh / 0.25h = 2.0 kW)
            assert slot.get("actual_charge_kw") == 2.0

    assert found_executed, "Did not find is_executed=True for historical slot"


@pytest.mark.anyio
async def test_today_with_history_f36_ignores_future_db_actions(tmp_path):
    """[REV F36] Verify that future slots do NOT pull battery actions from database."""
    db_path = tmp_path / "planner_learning.db"

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Insert a FUTURE planned charge in DB
        tz = pytz.UTC
        now = datetime.now(tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # Ensure we are well into the future but still TODAY
        future_start = today_start + timedelta(hours=22)

        await conn.execute(
            text("""
            INSERT INTO slot_plans (slot_start, planned_charge_kwh, planned_soc_percent)
            VALUES (:slot_start, 0.5, 80.0)
            """),
            {"slot_start": future_start.isoformat()},
        )

    # Mock config
    mock_config = {"learning": {"sqlite_path": str(db_path)}, "timezone": "UTC"}

    # Mock now to be 12:00 today, so 22:00 is FUTURE
    fixed_now = today_start.replace(hour=12)

    with (
        patch("backend.api.routers.schedule.load_yaml", return_value=mock_config),
        patch("backend.api.routers.schedule.Path") as MockPath,
        patch("backend.api.routers.schedule.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = fixed_now
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
        mock_datetime.combine.side_effect = datetime.combine
        mock_datetime.min = datetime.min

        # Mock schedule.json to be missing
        def side_effect(arg):
            if str(arg) == "schedule.json":
                m = MagicMock()
                m.exists.return_value = False
                return m
            return Path(arg)

        MockPath.side_effect = side_effect

        store = LearningStore(str(db_path), tz)
        result = await schedule_today_with_history(store=store)

    slots = result["slots"]
    found_future = False
    future_iso = future_start.isoformat().split(".")[0]

    for slot in slots:
        if future_iso in slot["start_time"]:
            found_future = True

    assert not found_future, f"Future slot from DB unexpectedly found in response: {future_iso}"
