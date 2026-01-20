#!/usr/bin/env python3
"""
Migration Script: Enable WAL Mode for Existing Databases (ARC12)

This script ensures all existing planner_learning.db databases are
converted to WAL (Write-Ahead Logging) mode for concurrent access.

WAL mode persists across connections, so this only needs to run once.
"""

import sqlite3
import sys
from pathlib import Path


def enable_wal_mode(db_path: str) -> None:
    """Enable WAL mode for a SQLite database."""
    if not Path(db_path).exists():
        print(f"⚠️  Database not found: {db_path}")
        print("   (This is expected for new installations)")
        return

    try:
        conn = sqlite3.connect(db_path, timeout=30.0)
        cursor = conn.cursor()

        # Check current mode
        current_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
        print(f"Current journal mode: {current_mode}")

        if current_mode.lower() == "wal":
            print("✅ WAL mode already enabled")
            conn.close()
            return

        # Enable WAL mode
        cursor.execute("PRAGMA journal_mode=WAL")
        new_mode = cursor.fetchone()[0]

        if new_mode.lower() == "wal":
            print("✅ Successfully enabled WAL mode")
            print(f"   {current_mode} → WAL")
        else:
            print(f"⚠️  Failed to enable WAL mode (result: {new_mode})")
            sys.exit(1)

        conn.close()

    except Exception as e:
        print(f"❌ Error enabling WAL mode: {e}")
        sys.exit(1)


def main():
    """Enable WAL mode for planner_learning.db in standard locations."""

    # Standard locations to check
    db_paths = [
        "/data/planner_learning.db",  # Home Assistant Add-on
        "planner_learning.db",  # Local development
        "../planner_learning.db",  # From scripts/ directory
    ]

    print("=" * 60)
    print("SQLite WAL Mode Migration (REV ARC12)")
    print("=" * 60)
    print()

    found = False
    for db_path in db_paths:
        if Path(db_path).exists():
            found = True
            print(f"📁 Processing: {db_path}")
            enable_wal_mode(db_path)
            print()

    if not found:
        print("INFO: No existing databases found.")
        print("      WAL mode will be enabled automatically on first run.")

    print("Migration complete!")


if __name__ == "__main__":
    main()
