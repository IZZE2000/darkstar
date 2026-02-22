import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import yaml

sys.path.append(str(Path(__file__).parent.parent))

import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Import models directly to avoid full app/store overhead if possible,
# but using LearningStore logic is safer for consistency.
# For a quick scan, I'll just use sqlalchemy directly with the models.
from backend.learning.models import SlotObservation

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("scanner")


def load_config() -> dict[str, Any]:
    try:
        with Path("config.yaml").open(encoding="utf-8") as f:
            return cast("dict[str, Any]", yaml.safe_load(f) or {})
    except FileNotFoundError:
        return {}


async def scan() -> None:
    config: dict[str, Any] = load_config()
    db_path: str = config.get("learning", {}).get("sqlite_path", "data/planner_learning.db")  # type: ignore[assignment]
    tz_name: str = config.get("timezone", "Europe/Stockholm")  # type: ignore[assignment]
    tz = pytz.timezone(tz_name)

    # Define "Today"
    now_local = datetime.now(tz)
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_iso = today_start.isoformat()

    print(f"Scanning database: {db_path}")
    print(f"Timezone: {tz_name}")
    print(f"Scanning from: {today_start_iso}")

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSession() as session:
        # Fetch all observations for today
        stmt = (
            select(SlotObservation)
            .where(SlotObservation.slot_start >= today_start_iso)
            .order_by(SlotObservation.slot_start.asc())
        )
        result = await session.execute(stmt)
        observations = result.scalars().all()

        if not observations:
            print("No observations found.")
            return

        print(f"Found {len(observations)} slots.")
        print(f"Range: {observations[0].slot_start} to {observations[-1].slot_start}")

        print(f"{'Time':<25} {'SoC (%)':<10} {'Battery (kW)':<15} {'Issue'}")
        print("-" * 65)

        prev_soc = None
        issues_found = 0

        for obs in observations:
            soc = obs.soc_end_percent

            # Formating
            soc_str = "None" if soc is None else f"{soc:.1f}"

            # Battery flow
            batt_kw = 0.0
            if obs.batt_charge_kwh:
                batt_kw -= obs.batt_charge_kwh * 4
            if obs.batt_discharge_kwh:
                batt_kw += obs.batt_discharge_kwh * 4

            issue = ""
            if soc is None:
                issue = "MISSING (None)"
            elif soc == 0.0:
                issue = "ZERO (0.0)"
            elif soc < 10.0:
                issue = f"LOW ({soc:.1f}%)"

            # Check drop
            if prev_soc is not None and soc is not None:
                diff = prev_soc - soc
                if diff > 5.0:  # stricter 5% drop
                    issue = f"{issue} DROP -{diff:.1f}%".strip()

            if issue or (soc is not None and soc < 10.0):
                print(f"{obs.slot_start:<25} {soc_str:<10} {batt_kw:<15.2f} {issue}")
                issues_found += 1

            if soc is not None:
                prev_soc = soc

        print("-" * 65)
        print(f"Scan complete. {issues_found} entries of interest found.")


if __name__ == "__main__":
    asyncio.run(scan())
