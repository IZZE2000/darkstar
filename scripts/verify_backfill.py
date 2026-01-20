import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path.cwd()))

# Configure logging to see output
import logging

from backend.learning.backfill import BackfillEngine

logging.basicConfig(level=logging.INFO)

async def test_resample():
    print("Testing _resample_history...")
    try:
        be = BackfillEngine()
    except Exception as e:
        print(f"Could not init BackfillEngine (maybe config missing?): {e}")
        return

    # Generate 1 hour of 6-second data (600 points)
    # 12:00 to 13:00
    start = datetime(2023, 1, 1, 12, 0, 0)
    history = []
    # 60 mins * 10 points/min = 600 points
    for i in range(600):
        ts = start + timedelta(seconds=6*i)
        val = 1000.0 # Constant 1000W
        history.append((ts, float(val)))

    resampled = be._resample_history(history, interval="1min")
    print(f"Original: {len(history)}, Resampled: {len(resampled)}")

    # Expect 60 points (12:00 to 12:59)
    assert abs(len(resampled) - 60) <= 2, f"Expected ~60 points, got {len(resampled)}"
    print(f"First point: {resampled[0]}")
    print(f"Last point: {resampled[-1]}")
    print("Resample OK")

    # Test ETL
    print("Testing etl_power_to_slots with resampled data...")
    le = be.engine

    data = {"pv": resampled} # canonical 'pv' -> 'pv_kwh'
    df = le.etl_power_to_slots(data)
    print("ETL Result Head:")
    print(df.head())

    if not df.empty and "pv_kwh" in df.columns:
         # 1000W for 1h = 1.0 kWh
         # 4 slots of 15min. Each slot = 1000W * 0.25h = 0.25kWh.
         total_kwh = df["pv_kwh"].sum()
         print(f"Total kWh: {total_kwh}")
         assert abs(total_kwh - 1.0) < 0.1, f"Expected ~1.0 kWh, got {total_kwh}"
         print("ETL OK")
    else:
        print("ETL returned empty or missing column")

if __name__ == "__main__":
    asyncio.run(test_resample())
