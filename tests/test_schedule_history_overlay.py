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

        # 1. Planned Charge Slot at 13:00 (Future compared to mock 12:00)
        slot_13 = today_start.replace(hour=13).isoformat()
        await conn.execute(
            text("""
            INSERT INTO slot_plans (slot_start, planned_charge_kwh, planned_discharge_kwh, planned_soc_percent, planned_export_kwh, planned_water_heating_kwh)
            VALUES (:slot_start, 0.5, 0.0, 50.0, 0.0, 0.25)
            """),
            {"slot_start": slot_13},
        )

    # Mock config to point to temp DB
    mock_config = {"learning": {"sqlite_path": str(db_path)}, "timezone": "UTC"}

    # Mock now to be 12:00 today, so 13:00 is FUTURE
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
    assert len(slots) > 0

    found_charge = False
    for slot in slots:
        if "13:00:00" in slot["start_time"]:
            # Even though it's future, SoC target and Water should be preserved from DB
            # but per REV F36, battery_charge_kw should NOT be pulled for future.
            found_charge = True
            assert slot.get("battery_charge_kw") is None or slot.get("battery_charge_kw") == 0.0
            assert slot.get("soc_target_percent") == 50.0
            assert slot.get("water_heating_kw") == 1.0

    assert found_charge


@pytest.mark.anyio
async def test_today_with_history_excludes_past(tmp_path):
    """Verify that slots before 'now' are excluded after the filter implementation."""
    db_path = tmp_path / "planner_learning.db"

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        tz = pytz.UTC
        now = datetime.now(tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        past_start = today_start + timedelta(hours=1)
        future_start = today_start + timedelta(hours=22)

        # Past slot in DB
        await conn.execute(
            text(
                "INSERT INTO slot_observations (slot_start, slot_end, batt_charge_kwh) VALUES (:s, :e, 0.5)"
            ),
            {"s": past_start.isoformat(), "e": (past_start + timedelta(minutes=15)).isoformat()},
        )

        # Future slot in DB
        await conn.execute(
            text("INSERT INTO slot_plans (slot_start, planned_soc_percent) VALUES (:s, 80.0)"),
            {"s": future_start.isoformat()},
        )

    mock_config = {"learning": {"sqlite_path": str(db_path)}, "timezone": "UTC"}
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

        def side_effect(arg):
            m = MagicMock()
            m.exists.return_value = False
            return m

        MockPath.side_effect = side_effect

        store = LearningStore(str(db_path), tz)
        result = await schedule_today_with_history(store=store)

    slots = result["slots"]
    # 01:00 should be excluded (past), 22:00 should be included (future)
    assert not any("01:00:00" in s["start_time"] for s in slots)
    assert any("22:00:00" in s["start_time"] for s in slots)
