import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path.cwd()))

# Configure logging
import logging

from sqlalchemy import select

from backend.learning.backfill import BackfillEngine
from backend.learning.models import SlotObservation

logging.basicConfig(level=logging.INFO)
logging.getLogger("backend.learning.backfill").setLevel(logging.INFO)

async def run_verification():
    print("Initializing BackfillEngine...")
    be = BackfillEngine()

    print("Running backfill...")
    await be.run()

    print("Backfill complete. Verifying DB for 03:00-03:30 charging data...")

    # Check last 10 days for any slot at 03:00 or 03:15 with charging data
    async with be.store.AsyncSession() as session:
        # Get all slots in last 10 days
        now = datetime.now(be.timezone)
        start_check = now - timedelta(days=10)

        stmt = select(SlotObservation).where(
            SlotObservation.slot_start >= start_check.isoformat()
        ).order_by(SlotObservation.slot_start)

        result = await session.execute(stmt)
        slots = result.scalars().all()

        found = False
        for s in slots:
            dt = datetime.fromisoformat(s.slot_start)
            # Check for 03:00-03:30 window
            if dt.hour == 3 and dt.minute in (0, 15, 30):
                charge = s.batt_charge_kwh or 0
                if charge > 0.1: # Threshold for "shows charging bars"
                    print(f"FOUND Charging Data at {dt}: {charge:.2f} kWh")
                    found = True
                    # ~3kW for 15 min = 0.75 kWh.
                    # If user expects 3kW power, the energy should be ~0.75 kWh per slot.
                    if charge > 0.5:
                        print(f"  -> Matches expected ~3kW power ({charge/0.25:.1f} kW)")

        if not found:
            print("WARNING: No significant charging data found in 03:00-03:30 windows in the last 10 days.")
        else:
            print("SUCCESS: Charging data verified.")

if __name__ == "__main__":
    asyncio.run(run_verification())
