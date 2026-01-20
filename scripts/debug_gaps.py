#!/usr/bin/env python3
"""
Gap Detection Diagnostic Script

Investigates why DataBackfillCard shows "System data up to date" when gaps exist.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select

from backend.learning import get_learning_engine
from backend.learning.models import SlotObservation


async def main():
    print("🔍 GAP DETECTION DIAGNOSTIC")
    print("=" * 50)
    
    try:
        engine = get_learning_engine()
        store = engine.store
        tz = store.timezone
        
        print(f"Database: {engine.db_path}")
        print(f"Timezone: {tz}")
        
        # Test parameters (same as API)
        days = 10
        now = datetime.now(tz)
        start_time = now - timedelta(days=days)
        
        # Truncate to 15-minute boundaries (same as API)
        start_time = start_time.replace(
            minute=start_time.minute - (start_time.minute % 15), 
            second=0, 
            microsecond=0
        )
        
        print(f"Now: {now}")
        print(f"Start time: {start_time}")
        print(f"Looking back: {days} days")
        print()
        
        # 1. Generate expected slots (same logic as API)
        print("📅 GENERATING EXPECTED SLOTS...")
        expected_slots = set()
        current = start_time
        slot_count = 0
        
        while current < now:
            expected_slots.add(current.isoformat())
            current += timedelta(minutes=15)
            slot_count += 1
            
        print(f"Expected slots: {slot_count}")
        print(f"Sample expected slots:")
        for i, slot in enumerate(sorted(expected_slots)):
            if i < 5 or i >= len(expected_slots) - 5:
                print(f"  {slot}")
            elif i == 5:
                print(f"  ... ({len(expected_slots) - 10} more) ...")
        print()
        
        # 2. Query existing slots (same logic as API)
        print("🗄️  QUERYING DATABASE...")
        existing_slots = set()
        
        async with store.AsyncSession() as session:
            stmt = select(SlotObservation.slot_start).where(
                SlotObservation.slot_start >= start_time.isoformat()
            )
            result = await session.execute(stmt)
            
            for row in result.scalars():
                existing_slots.add(row)
                
        print(f"Existing slots in DB: {len(existing_slots)}")
        print(f"Sample existing slots:")
        for i, slot in enumerate(sorted(existing_slots)):
            if i < 10:
                print(f"  {slot}")
            elif i == 10:
                print(f"  ... ({len(existing_slots) - 10} more) ...")
        print()
        
        # 3. Find missing slots
        print("🔍 FINDING GAPS...")
        missing = sorted(expected_slots - existing_slots)
        
        print(f"Missing slots: {len(missing)}")
        if missing:
            print("First 10 missing slots:")
            for i, slot in enumerate(missing[:10]):
                print(f"  {slot}")
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more")
        print()
        
        # 4. Check format differences
        print("🔧 FORMAT ANALYSIS...")
        if expected_slots and existing_slots:
            sample_expected = next(iter(expected_slots))
            sample_existing = next(iter(existing_slots))
            
            print(f"Expected format: '{sample_expected}' (len: {len(sample_expected)})")
            print(f"Existing format:  '{sample_existing}' (len: {len(sample_existing)})")
            print(f"Formats match: {sample_expected == sample_existing}")
        print()
        
        # 5. Test API logic simulation
        print("🧪 SIMULATING API LOGIC...")
        if not missing:
            print("✅ API would return: [] (empty gaps)")
        else:
            print(f"⚠️  API should return gaps for {len(missing)} missing slots")
            
            # Group into ranges (simplified)
            ranges = []
            if missing:
                current_start = missing[0]
                current_end = missing[0]
                count = 1
                
                for i in range(1, len(missing)):
                    curr_dt = datetime.fromisoformat(missing[i])
                    prev_dt = datetime.fromisoformat(missing[i-1])
                    
                    if (curr_dt - prev_dt) == timedelta(minutes=15):
                        current_end = missing[i]
                        count += 1
                    else:
                        ranges.append((current_start, current_end, count))
                        current_start = missing[i]
                        current_end = missing[i]
                        count = 1
                        
                ranges.append((current_start, current_end, count))
                
            print(f"Gap ranges: {len(ranges)}")
            for start, end, count in ranges:
                print(f"  {start} → {end} ({count} slots)")
        
        print()
        print("🎯 CONCLUSION:")
        if not missing:
            print("❌ No gaps detected - this explains why frontend shows 'up to date'")
            print("   But we know gaps should exist from log analysis!")
            print("   → Check timezone handling or boundary conditions")
        else:
            print(f"✅ {len(missing)} gaps detected - API should work correctly")
            print("   → Check if frontend is calling API or parsing response correctly")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
