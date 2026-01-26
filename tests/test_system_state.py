import pytest
import pytz

from backend.learning.store import LearningStore


@pytest.mark.asyncio
async def test_system_state_persistence():
    # Use the same path as conftest.py
    store = LearningStore("data/test_planner.db", pytz.UTC)

    # Test 1: Get non-existent key
    val = await store.get_system_state("non_existent")
    assert val is None

    # Test 2: Set key and get it back
    await store.set_system_state("test_key", "test_value")
    val = await store.get_system_state("test_key")
    assert val == "test_value"

    # Test 3: Update key
    await store.set_system_state("test_key", "updated_value")
    val = await store.get_system_state("test_key")
    assert val == "updated_value"

    await store.close()
