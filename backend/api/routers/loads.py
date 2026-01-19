import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.loads.service import LoadDisaggregator

from .config import get_config

router = APIRouter(prefix="/loads", tags=["loads"])
logger = logging.getLogger("darkstar.api.loads")

# Simple singleton pattern for the disaggregator within the API
_disaggregator: LoadDisaggregator | None = None


def get_disaggregator(config: dict = Depends(get_config)) -> LoadDisaggregator:
    global _disaggregator
    if _disaggregator is None:
        _disaggregator = LoadDisaggregator(config)
    return _disaggregator


@router.get("/debug")
async def get_loads_debug(
    disaggregator: LoadDisaggregator = Depends(get_disaggregator),
) -> dict[str, Any]:
    """
    Returns current disaggregation breakdown and sensor health.
    """
    try:
        # Note: In a real production scenario, the recorder or a background service
        # would be updating this. For the debug endpoint, we'll trigger a fresh fetch.
        controllable_kw = await disaggregator.update_current_power()

        # We don't have total_load_kw here easily without fetching it from HA.
        # However, the registry and metrics are already populated if the system is running.

        loads_breakdown = []
        for load in disaggregator.list_active_loads():
            loads_breakdown.append(
                {
                    "id": load.id,
                    "name": load.name,
                    "power_kw": load.current_power_kw,
                    "healthy": load.is_healthy,
                    "type": load.type.value,
                    "sensor": load.sensor_key,
                }
            )

        return {
            "controllable_total_kw": controllable_kw,
            "loads": loads_breakdown,
            "quality_metrics": disaggregator.get_quality_metrics(),
        }
    except Exception as e:
        logger.error(f"Failed to fetch loads debug data: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
