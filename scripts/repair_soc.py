import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytz
import yaml
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.learning.models import SlotObservation

logger = logging.getLogger("repair_soc")
logging.basicConfig(level=logging.INFO)


def load_config():
    try:
        with Path("config.yaml").open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def parse_args():
    parser = argparse.ArgumentParser(description="Repair missing SoC data.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate repairs without committing to DB"
    )
    return parser.parse_args()


async def repair():
    args = parse_args()
    config = load_config()
    db_path = config.get("learning", {}).get("sqlite_path", "data/planner_learning.db")
    tz_name = config.get("timezone", "Europe/Stockholm")
    tz = pytz.timezone(tz_name)

    # Repair window: Last 24 hours up to NOW
    now_local = datetime.now(tz)
    start_time = now_local - timedelta(hours=24)
    start_iso = start_time.isoformat()
    now_iso = now_local.isoformat()

    print(f"Repairing database: {db_path}")
    print(f"Scanning window: {start_iso} to {now_iso}")
    if args.dry_run:
        print("!!! DRY RUN MODE - NO CHANGES WILL BE SAVED !!!")

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    # We need to manually manage session context to ensure commit/rollback control
    async with engine.begin() as conn:
        # Fetch observations
        stmt = (
            select(SlotObservation)
            .where(SlotObservation.slot_start >= start_iso, SlotObservation.slot_start <= now_iso)
            .order_by(SlotObservation.slot_start.asc())
        )
        result = await conn.execute(stmt)
        # We need to fetch all columns to reconstruct objects or just fetch specific cols
        # For update, we specificially need slot_start and current soc
        # Easier to fetch fully as dicts
        rows = result.all()

        if not rows:
            print("No observations found.")
            return

        # Load into DataFrame
        df_data = []
        for r in rows:
            df_data.append({"slot_start": r.slot_start, "soc": r.soc_end_percent})

        df = pd.DataFrame(df_data)

        # Ensure datetime index for time-based operations if needed, but linear on rows is usually fine for slots
        # Let's stick to simple linear interpolation on the values.

        # 1. Identify missing values (None or 0.0 if treated as missing)
        # User scan showed 'None', but we should be careful with 0.0
        # Let's assume 0.0 is valid ONLY if it was 0.0 before or adjacent.
        # But safest is to treat real None as None.

        # Store original for comparison
        df["soc_original"] = df["soc"]

        # 2. Interpolate
        # method='linear' fills gaps between valid numbers.
        # limit_direction='both' handles the start (07:30) by backfilling from first valid.
        # It also handles the end? No, 'both' usually fills NaNs at beginning and end.
        df["soc_filled"] = df["soc"].interpolate(method="linear", limit_direction="both")

        # 3. Handling trailing NaNs if interpolate didn't catch them (e.g. if we have a big gap at the end)
        # Forward fill the rest
        df["soc_filled"] = df["soc_filled"].ffill()

        # Prepare updates
        updates_to_run = []
        print(f"\n{'Time':<25} {'Old':<10} {'New':<10} {'Method'}")
        print("-" * 65)

        for _idx, row in df.iterrows():
            original = row["soc_original"]
            filled = row["soc_filled"]
            slot_start = row["slot_start"]

            # Check if we actually changed anything
            # Use pd.isna to handle None/NaN checks correctly
            if pd.isna(original) and not pd.isna(filled):
                method = "Interpolate"
                print(f"{slot_start:<25} {'None':<10} {filled:<10.2f} {method}")
                updates_to_run.append({"slot_start": slot_start, "soc_end_percent": float(filled)})

        print("-" * 65)
        print(f"Total repairs identified: {len(updates_to_run)}")

        if not updates_to_run:
            print("No repairs needed.")
            return

        if args.dry_run:
            print("Dry run complete. No changes applied.")
            return

        # Apply updates
        print("Applying updates...")
        for update_data in updates_to_run:
            stmt = (
                update(SlotObservation)
                .where(SlotObservation.slot_start == update_data["slot_start"])
                .values(soc_end_percent=update_data["soc_end_percent"])
            )
            await conn.execute(stmt)

        # Commit is handled by the context manager 'async with engine.begin()' automatically on exit if no error
        print("Database updated successfully.")


if __name__ == "__main__":
    asyncio.run(repair())
