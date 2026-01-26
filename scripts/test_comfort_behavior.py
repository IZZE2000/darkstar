#!/usr/bin/env python3
"""Test script to demonstrate broken water comfort level behavior.

Shows that comfort levels 1 vs 5 produce identical heating patterns
due to hardcoded 2.0h windows and inadequate penalty scaling.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

from planner.solver.adapter import _comfort_level_to_penalty, config_to_kepler_config
from planner.solver.kepler import KeplerSolver


def create_test_config():
    """Create minimal config for testing."""
    from pathlib import Path

    with Path("config.yaml").open() as f:
        config = yaml.safe_load(f)

    # Override for consistent testing
    config["water_heating"]["daily_kwh"] = 8.0
    config["water_heating"]["comfort_level"] = 3  # Will be overridden

    return config


def test_comfort_level(level: int, scenario_name: str):
    """Test a specific comfort level and return heating pattern."""
    print(f"\n=== Testing Comfort Level {level} ({scenario_name}) ===")

    config = create_test_config()
    config["water_heating"]["comfort_level"] = level

    # Get penalty mapping
    penalties = _comfort_level_to_penalty(
        level,
        daily_kwh=config["water_heating"]["daily_kwh"],
        heater_power_kw=config["water_heating"]["power_kw"],
    )
    print(
        f"Penalties: reliability={penalties['water_reliability_penalty_sek']:.1f}, "
        f"block_start={penalties['water_block_start_penalty_sek']:.1f}, "
        f"block={penalties['water_block_penalty_sek']:.2f}"
    )
    print(f"Dynamic window: {penalties['max_block_hours']:.2f}h (vs 2.0h hardcoded)")

    # Convert to Kepler config
    kepler_config = config_to_kepler_config(config)

    # Create simple price scenario (cheap morning, expensive evening)
    prices = []
    for hour in range(48):
        if 2 <= hour % 24 <= 6:  # Cheap 02:00-06:00
            prices.extend([0.5, 0.5, 0.5, 0.5])  # 4 slots per hour
        else:  # Expensive rest of day
            prices.extend([2.0, 2.0, 2.0, 2.0])

    # Create input data
    from datetime import datetime, timedelta

    from planner.solver.types import KeplerInput, KeplerInputSlot

    slots = []
    start_time = datetime.now()
    for i, price in enumerate(prices):
        s = start_time + timedelta(minutes=15 * i)
        e = s + timedelta(minutes=15)
        slots.append(
            KeplerInputSlot(
                start_time=s,
                end_time=e,
                load_kwh=1.0,
                pv_kwh=0.0,
                import_price_sek_kwh=price,
                export_price_sek_kwh=0.0,
            )
        )

    input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)  # 50% of 10kWh

    # Solve
    solver = KeplerSolver()
    solve_start = time.time()
    result = solver.solve(input_data, kepler_config)
    solve_elapsed = time.time() - solve_start

    print(f"   🔧 Actual solve time: {solve_elapsed:.3f}s (reported: {result.solve_time_ms:.1f}ms)")

    if not result.is_optimal:
        print(f"❌ Solver failed: {result.status_msg}")
        return None

    # Analyze heating pattern
    water_slots = [i for i, slot in enumerate(result.slots) if slot.water_heat_kw > 0]
    if not water_slots:
        print("❌ No water heating scheduled")
        return None

    # Find heating blocks
    blocks = []
    current_block = [water_slots[0]]

    for slot in water_slots[1:]:
        if slot == current_block[-1] + 1:  # Consecutive
            current_block.append(slot)
        else:  # New block
            blocks.append(current_block)
            current_block = [slot]
    blocks.append(current_block)

    print(f"✅ Heating blocks: {len(blocks)} blocks")
    for i, block in enumerate(blocks):
        start_hour = block[0] // 4
        end_hour = block[-1] // 4
        duration = len(block) * 0.25
        print(
            f"  Block {i + 1}: Hours {start_hour:02d}-{end_hour:02d} ({duration:.2f}h, {len(block)} slots)"
        )

    return {
        "level": level,
        "blocks": len(blocks),
        "max_block_size": max(len(block) for block in blocks),
        "total_slots": len(water_slots),
        "solve_time": result.solve_time_ms / 1000.0,
    }


def main():
    """Test comfort levels and compare behavior."""
    import time

    script_start = time.time()

    print("🔍 Testing Water Comfort Level Behavior")
    print("=" * 50)

    results = []
    level_names = {1: "Economy", 2: "Balanced", 3: "Neutral", 4: "Priority", 5: "Maximum"}

    # Test all levels
    for level in [1, 2, 3, 4, 5]:
        level_start = time.time()
        results.append(test_comfort_level(level, level_names[level]))
        level_elapsed = time.time() - level_start
        print(f"   ⏱️  Level {level} total time: {level_elapsed:.2f}s\n")

    # Compare results
    print(f"\n{'=' * 50}")
    print("📊 COMPARISON RESULTS")
    print(f"{'=' * 50}")

    if all(r for r in results):
        for r in results:
            level_name = level_names[r["level"]]
            print(
                f"Level {r['level']} ({level_name:8s}): {r['blocks']} blocks, "
                f"max {r['max_block_size']} slots, solve: {r['solve_time'] * 1000:.1f}ms"
            )

        # Check for smooth progression
        block_counts = [r["blocks"] for r in results]
        if block_counts == sorted(block_counts):
            print("\n✅ Smooth progression detected (fewer → more blocks)")
        else:
            print("\n⚠️  WARNING: Progression may not be smooth!")
            print(f"   Block counts: {block_counts}")
    else:
        print("❌ Test failed - could not compare results")

    script_elapsed = time.time() - script_start
    print(f"\n⏱️  Total script time: {script_elapsed:.2f}s")


if __name__ == "__main__":
    main()
