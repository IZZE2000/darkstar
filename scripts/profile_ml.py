"""Profiling script for ML inference components."""

import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.resolve()))

from datetime import datetime, timedelta

from ml.forward import _load_models, generate_forward_slots  # type: ignore[reportPrivateUsage]
from ml.weather import get_weather_series


def profile(
    name: str, func: Callable[..., Any], *args: Any, **kwargs: Any
) -> tuple[Any | None, float]:
    start = time.time()
    try:
        res = func(*args, **kwargs)
        dur = time.time() - start
        print(f"[{name}] Done in {dur:.4f}s")
        return res, dur
    except Exception as e:
        dur = time.time() - start
        print(f"[{name}] Failed in {dur:.4f}s: {e}")
        return None, dur


def main():
    print("Profiling ML Components\n")
    print("=" * 50)

    # Profile model loading
    print("\n1. Model Loading")
    print("-" * 30)
    load_result, load_dur = profile("load_models", _load_models)

    # Profile weather fetch
    print("\n2. Weather Fetch")
    print("-" * 30)
    now = datetime.now()
    future = now + timedelta(days=2)
    weather_result, weather_dur = profile("weather_fetch", get_weather_series, now, future)

    # Profile inference
    inference_dur: float | None = None
    print("\n3. Forward Inference")
    print("-" * 30)
    if load_result and weather_result:
        models, _ = load_result
        weather_df = weather_result
        _, inference_dur = profile(
            "generate_forward_slots",
            generate_forward_slots,
            models,
            weather_df,
            now,
        )

    # Summary
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"Model loading: {load_dur:.4f}s")
    print(f"Weather fetch: {weather_dur:.4f}s")
    if inference_dur is not None:
        print(f"Forward inference: {inference_dur:.4f}s")


if __name__ == "__main__":
    main()
