import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import pytz

# Ensure backend module is found
sys.path.append(str(Path.cwd()))

from backend.learning.backfill import BackfillEngine
from backend.learning.store import LearningStore


@pytest.mark.asyncio
async def test_backfill_engine_targets_gaps():
    """
    Verify that BackfillEngine.run() identifies historical gaps and calls _fetch_history
    only for those specific ranges.
    """
    tz = pytz.timezone("Europe/Stockholm")

    # Mock LearningStore and LearningEngine
    mock_store = MagicMock(spec=LearningStore)
    mock_store.timezone = tz
    mock_store.AsyncSession = MagicMock()

    with (
        patch(
            "backend.learning.backfill.BackfillEngine._load_config",
            return_value={
                "timezone": "Europe/Stockholm",
                "learning": {"sensor_map": {"sensor.test": "test"}},
            },
        ),
        patch.object(
            BackfillEngine,
            "detect_gaps",
            return_value=[
                {
                    "start_time": (
                        datetime.now(tz).replace(minute=0, second=0, microsecond=0)
                        - timedelta(days=2)
                    ).isoformat(),
                    "end_time": (
                        datetime.now(tz).replace(minute=0, second=0, microsecond=0)
                        - timedelta(days=2)
                        + timedelta(minutes=45)
                    ).isoformat(),
                    "missing_slots": 4,
                }
            ],
        ),
        patch.object(
            BackfillEngine, "_fetch_history", return_value=[(datetime.now(tz), 10.0)]
        ) as mock_fetch,
        patch("backend.learning.backfill.get_learning_engine") as mock_get_le,
    ):
        engine = BackfillEngine()
        engine.store = mock_store

        le = MagicMock()
        mock_get_le.return_value = le
        le.etl_cumulative_to_slots.return_value = pd.DataFrame([{"slot_start": datetime.now(tz)}])

        await engine.run()

        # Verify _fetch_history was called for the gap range
        gap1_start = (
            datetime.now(tz).replace(minute=0, second=0, microsecond=0) - timedelta(days=2)
        ).isoformat()
        gap1_end = (
            datetime.now(tz).replace(minute=0, second=0, microsecond=0)
            - timedelta(days=2)
            + timedelta(minutes=45)
        ).isoformat()
        expected_start = datetime.fromisoformat(gap1_start)
        expected_end = datetime.fromisoformat(gap1_end) + timedelta(minutes=15)

        mock_fetch.assert_any_call("sensor.test", expected_start, expected_end)
        assert mock_fetch.call_count == 1


@pytest.mark.asyncio
async def test_detect_gaps_logic():
    """
    Verify detect_gaps correctly identifies gaps in the DB.
    """
    tz = pytz.timezone("Europe/Stockholm")
    db_path = "data/test_backfill_gaps.db"

    # Ensure data dir exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    if Path(db_path).exists():
        Path(db_path).unlink()

    store = LearningStore(db_path, tz)

    # Initialize tables
    from backend.learning.models import Base

    async with store.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with patch(
        "backend.learning.backfill.BackfillEngine._load_config",
        return_value={"timezone": "Europe/Stockholm"},
    ):
        engine = BackfillEngine()
        engine.store = store

        # Insert some data with a gap
        now = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
        t1 = now - timedelta(hours=5)
        t2 = t1 + timedelta(minutes=15)
        # Gap of 30 mins (2 slots)
        t3 = t2 + timedelta(minutes=45)

        slots = [
            {
                "slot_start": t1,
                "slot_end": t1 + timedelta(minutes=15),
                "soc_end_percent": 50.0,
                "pv_kwh": 1.0,
                "load_kwh": 1.0,
            },
            {
                "slot_start": t2,
                "slot_end": t2 + timedelta(minutes=15),
                "soc_end_percent": 51.0,
                "pv_kwh": 1.1,
                "load_kwh": 1.1,
            },
            # Gap here
            {
                "slot_start": t3,
                "slot_end": t3 + timedelta(minutes=15),
                "soc_end_percent": 53.0,
                "pv_kwh": 1.3,
                "load_kwh": 1.3,
            },
        ]
        await store.store_slot_observations(pd.DataFrame(slots))

        gaps = await engine.detect_gaps(days=1)

        # We expect gaps between t2 and t3
        # t2 is slot_start of last valid. Gap starts at t2 + 15min.
        expected_gap_start = (t2 + timedelta(minutes=15)).astimezone(tz).isoformat()

        found = False
        for g in gaps:
            if g["start_time"] == expected_gap_start:
                found = True
                assert g["missing_slots"] == 2

        assert found, f"Expected gap starting at {expected_gap_start} not found in {gaps}"

        await store.close()
        if Path(db_path).exists():
            Path(db_path).unlink()
