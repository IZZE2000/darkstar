#!/usr/bin/env python3
"""
Direct Database Query for Slot Observations
"""

import sqlite3
from datetime import datetime, timedelta


def check_database():
    """Check what's actually in the SlotObservation table."""
    print("🗄️  CHECKING DATABASE DIRECTLY...")

    try:
        conn = sqlite3.connect("data/planner_learning.db")
        cursor = conn.cursor()

        # Check table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='slot_observations'"
        )
        if not cursor.fetchone():
            print("❌ slot_observations table not found!")
            return

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM slot_observations")
        total = cursor.fetchone()[0]
        print(f"Total observations: {total}")

        # Get recent observations (last 24 hours)
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        cursor.execute(
            """
            SELECT slot_start, import_price_sek_kwh
            FROM slot_observations
            WHERE slot_start >= ?
            ORDER BY slot_start DESC
            LIMIT 20
        """,
            (yesterday.isoformat(),),
        )

        recent = cursor.fetchall()
        print(f"\nRecent observations (last 24h): {len(recent)}")

        if recent:
            print("Sample recent slots:")
            for slot_start, price in recent[:10]:
                print(f"  {slot_start} (price: {price})")
        else:
            print("❌ No recent observations found!")

        # Check for today's data specifically
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cursor.execute(
            """
            SELECT slot_start
            FROM slot_observations
            WHERE slot_start >= ?
            ORDER BY slot_start ASC
        """,
            (today.isoformat(),),
        )

        today_slots = cursor.fetchall()
        print(f"\nToday's slots: {len(today_slots)}")

        if today_slots:
            print("Today's slots:")
            for (slot_start,) in today_slots:
                print(f"  {slot_start}")
        else:
            print("❌ No data for today!")

        conn.close()

    except Exception as e:
        print(f"❌ Database error: {e}")


if __name__ == "__main__":
    check_database()
