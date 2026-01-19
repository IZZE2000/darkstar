import asyncio
import sys
from pathlib import Path

from sqlalchemy import func, select

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.learning import get_learning_engine
from backend.learning.models import SlotObservation


async def main():
    print("--- Investigating Cost Reality Data ---")
    try:
        engine = get_learning_engine()
        print(f"DB Path: {engine.db_path}")

        # 1. Check raw observation counts
        async with engine.store.AsyncSession() as session:
            count = await session.scalar(select(func.count(SlotObservation.slot_start)))
            print(f"Total SlotObservations: {count}")

            # Check recent observations with non-zero import/export
            recent = await session.execute(
                select(
                    SlotObservation.slot_start,
                    SlotObservation.import_kwh,
                    SlotObservation.import_price_sek_kwh,
                )
                .where(SlotObservation.import_kwh > 0)
                .order_by(SlotObservation.slot_start.desc())
                .limit(5)
            )
            print("\nRecent Active Observations:")
            for row in recent:
                print(row)

        # 2. Call the API method directly
        print("\n--- API Response (Cost Series) ---")
        data = await engine.get_performance_series(days_back=7)
        cost_series = data.get("cost_series", [])
        for item in cost_series:
            print(item)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
