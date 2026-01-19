#!/usr/bin/env python3
"""
Quick CLI visualization of load disaggregation data.
Usage: python scripts/visualize_loads.py
"""

import asyncio

from backend.loads.service import LoadDisaggregator
from backend.recorder import _load_config


async def show_current_breakdown():
    """Show current power breakdown."""
    config = _load_config()
    disaggregator = LoadDisaggregator(config)

    print("🔌 CURRENT LOAD BREAKDOWN")
    print("=" * 40)

    controllable_kw = await disaggregator.update_current_power()

    for load in disaggregator.list_active_loads():
        status = "✅" if load.is_healthy else "❌"
        print(f"{status} {load.name}: {load.current_power_kw:.2f} kW ({load.type.value})")

    print(f"\n📊 Total Controllable: {controllable_kw:.2f} kW")

    # Show quality metrics
    metrics = disaggregator.get_quality_metrics()
    print(f"📈 Drift Rate: {metrics['drift_rate']:.1%}")


async def show_historical_comparison():
    """Show base load vs total load over last 24h."""

    # This would query the database for historical data
    print("\n📈 HISTORICAL COMPARISON (Last 24h)")
    print("=" * 40)
    print("Time        | Total | Base  | Water | Diff")
    print("-" * 40)
    # Implementation would show actual data...


if __name__ == "__main__":
    asyncio.run(show_current_breakdown())
