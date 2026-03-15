import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from sqlalchemy import func, select

# Add root to sys.path
sys.path.append(str(Path.cwd()))

from backend.core.secrets import load_yaml
from backend.learning.engine import LearningEngine
from backend.learning.models import (
    LearningRun,
    SlotForecast,
    SlotObservation,
    SlotPlan,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("darkstar.inspect")


async def inspect():
    print("--- Darkstar Database Inspection Tool ---")

    try:
        config = load_yaml("config.yaml")
        tz = pytz.timezone(config.get("timezone", "Europe/Stockholm"))
    except Exception:
        tz = pytz.timezone("Europe/Stockholm")

    engine = LearningEngine()
    print(f"Database Path: {engine.db_path}")

    async with engine.store.AsyncSession() as session:
        # 1. Learning Runs
        total_runs = await session.scalar(select(func.count(LearningRun.id)))
        print(f"Total Learning Runs: {total_runs}")

        # 2. Slot Observations
        obs_count = await session.scalar(select(func.count(SlotObservation.slot_start)))
        last_obs = await session.scalar(select(func.max(SlotObservation.slot_start)))
        print(f"Total Observations: {obs_count}")
        print(f"Last Observation: {last_obs}")

        # 3. Slot Forecasts (Aurora)
        aurora_count = await session.scalar(
            select(func.count(SlotForecast.id)).where(SlotForecast.forecast_version == "aurora")
        )
        print(f"Total Aurora Forecast Slots: {aurora_count}")

        # 4. Slot Plans
        plan_count = await session.scalar(select(func.count(SlotPlan.id)))
        last_plan = await session.scalar(select(func.max(SlotPlan.slot_start)))
        print(f"Total Plan Slots: {plan_count}")
        print(f"Last Plan Slot: {last_plan}")

        # 5. Recent Data Check (Last 24h)
        now = datetime.now(tz)
        yesterday = (now - timedelta(days=1)).isoformat()

        recent_obs = await session.scalar(
            select(func.count(SlotObservation.slot_start)).where(
                SlotObservation.slot_start >= yesterday
            )
        )
        print(f"Observations in last 24h: {recent_obs}")

        recent_forecasts = await session.scalar(
            select(func.count(SlotForecast.id)).where(
                SlotForecast.slot_start >= yesterday, SlotForecast.forecast_version == "aurora"
            )
        )
        print(f"Aurora Forecasts in last 24h: {recent_forecasts}")


if __name__ == "__main__":
    asyncio.run(inspect())
