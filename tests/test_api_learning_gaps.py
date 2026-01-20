import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
import pytz
from fastapi.testclient import TestClient

# Ensure backend module is found
sys.path.append(str(Path.cwd()))

from backend.learning.store import LearningStore
from inputs import load_yaml  # helper to load config


@pytest.fixture
def client():
    from backend.main import create_app

    app = create_app()
    fastapi_app = app.other_asgi_app if hasattr(app, "other_asgi_app") else app
    with TestClient(fastapi_app) as client:
        yield client


@pytest.mark.asyncio
async def test_get_gaps(client):
    # Setup: connect to same DB
    # Load config to get timezone
    try:
        config = load_yaml("config.yaml")
        tz_name = config.get("timezone", "Europe/Stockholm")
    except Exception:
        tz_name = "Europe/Stockholm"

    tz = pytz.timezone(tz_name)
    store = LearningStore("data/test_planner.db", tz)

    # Insert data with a gap
    # 2 days ago until now.
    now = datetime.now(tz)
    now = now.replace(minute=now.minute - (now.minute % 15), second=0, microsecond=0)

    start_time = now - timedelta(days=2)
    end_time = now

    # Create contiguous slots except for a gap
    # Gap will be 1 hour long (4 slots), 1 day ago
    slots = []
    current = start_time
    gap_start = now - timedelta(days=1)
    gap_end = gap_start + timedelta(hours=1)

    print(f"DEBUG: Generating slots from {start_time} to {end_time}")
    print(f"DEBUG: Gap from {gap_start} to {gap_end}")

    while current < end_time:
        # Check if current is in gap window
        # Use precise comparison
        if not (gap_start <= current < gap_end):
            slots.append(
                {
                    "slot_start": current,
                    "slot_end": current + timedelta(minutes=15),
                    "import_kwh": 0.1,
                    "export_kwh": 0.1,
                }
            )
        current += timedelta(minutes=15)

    if slots:
        df = pd.DataFrame(slots)
        await store.store_slot_observations(df)

    # Call API
    response = client.get("/api/learning/gaps?days=2")
    assert response.status_code == 200
    gaps = response.json()

    print(f"DEBUG: API returned gaps: {gaps}")

    # Verify gap
    found_gap = False
    for gap in gaps:
        g_start = datetime.fromisoformat(gap["start_time"])
        # Compare with gap_start
        # Allow slight offset if timezone conversion happens, but should be exact matches for 15 min slots
        diff = abs((g_start - gap_start).total_seconds())
        if diff < 300:  # 5 min tolerance
            found_gap = True
            # Expected 4 slots missing + maybe surrounding if boundaries slightly off?
            # 4 slots = 1 hour.
            print(f"DEBUG: Found candidate gap: {gap}")
            assert gap["missing_slots"] >= 4
            break

    assert found_gap, f"Created gap starting at {gap_start} not found in response: {gaps}"

    await store.close()
