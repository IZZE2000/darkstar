import contextlib
import json
import logging
from typing import Any, cast

import pytz

from backend.learning.store import LearningStore

logger = logging.getLogger("darkstar.planner.inputs.learning")


async def load_learning_overlays(learning_config: dict[str, Any]) -> dict[str, Any]:
    """
    Load latest learning adjustments asynchronously.

    Data is read from learning_daily_metrics via LearningStore.
    This method is intentionally tolerant: if anything fails or no data exists,
    it returns an empty dict.

    Args:
        learning_config: Learning configuration dictionary

    Returns:
        Dictionary with overlays
    """
    if not learning_config.get("enable", False):
        return {}

    path = learning_config.get("sqlite_path", "data/planner_learning.db")
    try:
        # We don't have timezone here easily, but we don't need it for just fetching metrics
        store = LearningStore(path, timezone=pytz.UTC)
        metric = await store.get_latest_metrics()

        if not metric:
            return {}

        def _parse_series(raw: Any) -> list[float] | None:
            if raw is None:
                return None
            try:
                data: Any = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(data, list):
                    data_list = cast("list[Any]", data)
                    return [float(v) for v in data_list]
            except (TypeError, ValueError, json.JSONDecodeError):
                return None
            return None

        overlays: dict[str, Any] = {}
        pv_adj = _parse_series(metric.get("pv_adjustment_by_hour_kwh"))
        load_adj = _parse_series(metric.get("load_adjustment_by_hour_kwh"))
        if pv_adj:
            overlays["pv_adjustment_by_hour_kwh"] = pv_adj
        if load_adj:
            overlays["load_adjustment_by_hour_kwh"] = load_adj

        s_index_base_factor = metric.get("s_index_base_factor")
        if s_index_base_factor is not None:
            with contextlib.suppress(TypeError, ValueError):
                overlays["s_index_base_factor"] = float(s_index_base_factor)

        return overlays
    except Exception as e:
        logger.debug("Failed to load learning overlays: %s", e)
        return {}
