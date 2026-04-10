import contextlib
import logging
from typing import Any

import pytz

from backend.learning.store import LearningStore

logger = logging.getLogger("darkstar.planner.inputs.learning")


async def load_learning_overlays(learning_config: dict[str, Any]) -> dict[str, Any]:
    """
    Load latest learning adjustments asynchronously.

    Data is read from learning_daily_metrics via LearningStore.
    This method is intentionally tolerant: if anything fails or no data exists,
    it returns an empty dict.

    Note: Hourly adjustment overlays (pv_adjustment_by_hour_kwh, load_adjustment_by_hour_kwh)
    have been removed as part of removing the Analyst/Auto-Tuner. The base model now
    handles adaptation through recency-weighted training.

    Args:
        learning_config: Learning configuration dictionary

    Returns:
        Dictionary with overlays (s_index_base_factor only)
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

        overlays: dict[str, Any] = {}

        s_index_base_factor = metric.get("s_index_base_factor")
        if s_index_base_factor is not None:
            with contextlib.suppress(TypeError, ValueError):
                overlays["s_index_base_factor"] = float(s_index_base_factor)

        return overlays
    except Exception as e:
        logger.debug("Failed to load learning overlays: %s", e)
        return {}
