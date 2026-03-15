import logging
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("darkstar.api.water")

router = APIRouter(prefix="/api/water", tags=["water"])


@router.get(
    "/boost",
    summary="Get Water Boost Status",
    description="Get current water boost status from executor.",
)
async def get_water_boost():
    """Get current water boost status from executor."""
    from backend.api.routers.executor import get_executor_instance

    executor = get_executor_instance()
    if not executor:
        return {"boost": False, "source": "no_executor"}

    if hasattr(executor, "get_water_boost_status"):
        status = executor.get_water_boost_status()
        if status:
            return {"boost": True, "expires_at": status.get("expires_at"), "source": "executor"}
    return {"boost": False, "source": "executor"}


class WaterBoostRequest(BaseModel):
    duration_minutes: int = 60


@router.post(
    "/boost",
    summary="Set Water Boost",
    description="Activate water heater boost via executor quick action.",
)
async def set_water_boost(req: WaterBoostRequest) -> dict[str, str]:
    """Activate water heater boost via executor quick action."""
    try:
        from backend.api.routers.executor import (
            get_executor_instance,
        )

        executor = get_executor_instance()
        if not executor:
            logger.error("Executor unavailable for water boost")
            raise HTTPException(503, "Executor not available")
        if hasattr(executor, "set_water_boost"):
            # The executor.set_water_boost isn't strictly typed in Pyright's eyes yet maybe?
            # We fixed it in executor/actions.py, but need to be sure engine calls match.
            # Assuming set_water_boost(duration_minutes=...) exists on the executor instance
            # which is actually engine.py's ExecutorEngine or similar.
            # Actually get_executor_instance returns the Engine instance.
            result = executor.set_water_boost(duration_minutes=req.duration_minutes)  # pyright: ignore [reportUnknownMemberType]
            if not result.get("success"):
                logger.error(f"Failed to set water boost: {result.get('error')}")
                raise HTTPException(500, f"Failed to set water boost: {result.get('error')}")

            logger.info(f"Water boost activated successfully for {req.duration_minutes} minutes")
            return {
                "status": "success",
                "message": f"Water boost activated for {req.duration_minutes} minutes",
            }

        logger.error("Executor missing set_water_boost method")
        raise HTTPException(501, "Water boost not supported by executor")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting water boost: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, f"Internal error setting water boost: {e}") from e


@router.delete(
    "/boost",
    summary="Cancel Water Boost",
    description="Cancel active water boost.",
)
async def cancel_water_boost() -> dict[str, str]:
    """Cancel active water boost."""
    try:
        from backend.api.routers.executor import (
            get_executor_instance,
        )

        executor = get_executor_instance()
        if executor and hasattr(executor, "clear_water_boost"):
            executor.clear_water_boost()
            logger.info("Water boost cancelled successfully")
        return {"status": "success", "message": "Water boost cancelled"}
    except Exception as e:
        logger.error(f"Error cancelling water boost: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, f"Internal error cancelling water boost: {e}") from e
