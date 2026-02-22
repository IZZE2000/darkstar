#!/usr/bin/env python3
"""
Deep Planner Profiler - Traces internal steps.
Usage: docker exec darkstar python scripts/profile_deep.py
"""

import asyncio
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

sys.path.append(str(Path(__file__).parent.parent.resolve()))

from datetime import datetime, timedelta

import pytz
import yaml

# Patch time-tracking into critical functions
_timings = {}


def profile(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                _timings[name] = time.time() - start
                print(f"  [{name}] {_timings[name]:.2f}s")

        return wrapper

    return decorator


async def main() -> None:
    print("=" * 60)
    print("DEEP PLANNER PROFILER")
    print("=" * 60)

    overall_start = time.time()

    # Step 1: Load config
    start = time.time()
    with Path("config.yaml").open() as f:
        config = cast("dict[str, Any]", yaml.safe_load(f))
    _timings["1_load_config"] = time.time() - start
    print(f"[1_load_config] {_timings['1_load_config']:.2f}s")

    # Step 2: ML Inference
    start = time.time()
    from ml.pipeline import run_inference

    learning_cfg: dict[str, Any] = config.get("learning", {})
    days = int(learning_cfg.get("horizon_days", 2))
    hours = days * 24
    await run_inference(horizon_hours=hours, forecast_version="aurora")
    _timings["2_ml_inference"] = time.time() - start
    print(f"[2_ml_inference] {_timings['2_ml_inference']:.2f}s")

    # Step 3: Weather Volatility
    start = time.time()
    from ml.weather import get_weather_volatility

    tz = pytz.timezone(config.get("timezone", "Europe/Stockholm"))
    now = datetime.now(tz)

    end = now + timedelta(hours=48)
    get_weather_volatility(now, end, config)
    _timings["3_weather_volatility"] = time.time() - start
    print(f"[3_weather_volatility] {_timings['3_weather_volatility']:.2f}s")

    # Step 4: Nordpool Prices
    start = time.time()
    from inputs import get_nordpool_data

    price_data = await get_nordpool_data()
    _timings["4_nordpool"] = time.time() - start
    print(f"[4_nordpool] {_timings['4_nordpool']:.2f}s")

    # Step 5: Forecast Data
    start = time.time()
    from inputs import get_forecast_data

    forecast_result: dict[str, Any] = await get_forecast_data(price_data, config)
    _timings["5_forecast_data"] = time.time() - start
    print(f"[5_forecast_data] {_timings['5_forecast_data']:.2f}s")

    # Step 6: Initial State (HA Sensors)
    start = time.time()
    from inputs import get_initial_state

    initial_state: dict[str, Any] = await get_initial_state()
    _timings["6_initial_state"] = time.time() - start
    print(f"[6_initial_state] {_timings['6_initial_state']:.2f}s")

    # Step 7: Planner Pipeline
    start = time.time()
    from planner.pipeline import PlannerPipeline

    input_data: dict[str, Any] = {
        "price_data": price_data,
        "forecast_data": forecast_result.get("slots", []),
        "initial_state": initial_state,
        "daily_pv_forecast": forecast_result.get("daily_pv_forecast", {}),
        "daily_load_forecast": forecast_result.get("daily_load_forecast", {}),
    }
    pipeline = PlannerPipeline(config)
    await pipeline.generate_schedule(input_data, mode="full", save_to_file=True)
    _timings["7_planner"] = time.time() - start
    print(f"[7_planner] {_timings['7_planner']:.2f}s")

    _timings["total"] = time.time() - overall_start

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for k, v in sorted(_timings.items()):  # type: ignore[arg-type]
        print(f"  {k:.<40} {v:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
