"""
Async Planner Service

Wraps the blocking PlannerPipeline in an async interface suitable
for running inside the FastAPI process without blocking the event loop.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.core.cache import cache
from backend.core.websockets import ws_manager

logger = logging.getLogger("darkstar.services.planner")


@dataclass
class PlannerResult:
    """Result of a planner execution."""

    success: bool
    planned_at: datetime
    slot_count: int = 0
    error: str | None = None
    duration_ms: float = 0


class PlannerService:
    """Async planner service for in-process execution."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current_phase: str | None = None
        self._phase_start_time: datetime | None = None

    async def _emit_progress(self, phase: str) -> None:
        """Emit progress event via WebSocket."""
        self._current_phase = phase
        self._phase_start_time = datetime.now()

        elapsed_ms = 0.0
        if self._phase_start_time:
            elapsed_ms = (datetime.now() - self._phase_start_time).total_seconds() * 1000

        try:
            await ws_manager.emit(
                "planner_progress",
                {
                    "phase": phase,
                    "elapsed_ms": elapsed_ms,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            logger.debug(f"Planner progress: {phase} ({elapsed_ms:.0f}ms)")
        except Exception as e:
            logger.warning(f"Failed to emit progress for phase '{phase}': {e}")

    def get_status(self) -> dict:
        """Get current planner status (for HTTP fallback)."""
        if not self._current_phase:
            return {"phase": "idle", "elapsed_ms": 0, "is_running": False}

        elapsed_ms = 0.0
        if self._phase_start_time:
            elapsed_ms = (datetime.now() - self._phase_start_time).total_seconds() * 1000

        return {
            "phase": self._current_phase,
            "elapsed_ms": elapsed_ms,
            "is_running": self._lock.locked(),
        }

    async def run_once(self) -> PlannerResult:
        """
        Run the planner asynchronously.
        Handles cache invalidation and WebSocket notification automatically.

        Uses a lock to prevent concurrent planner executions.
        """
        # Prevent concurrent runs
        if self._lock.locked():
            logger.warning("Planner already running, skipping concurrent request")
            return PlannerResult(
                success=False,
                planned_at=datetime.now(),
                error="Planner already running",
            )

        async with self._lock:
            start = datetime.now()
            planned_at = start
            self._phase_start_time = start

            try:
                await self._emit_progress("fetching_inputs")

                from bin.run_planner import main as run_planner_main

                exit_code = await run_planner_main(progress_callback=self._emit_progress)

                if exit_code == 0:
                    slot_count = self._count_schedule_slots()
                    result = PlannerResult(
                        success=True,
                        planned_at=planned_at,
                        slot_count=slot_count,
                    )
                else:
                    result = PlannerResult(
                        success=False,
                        planned_at=planned_at,
                        error=f"Planner exited with code {exit_code}",
                    )

                result.duration_ms = (datetime.now() - start).total_seconds() * 1000

                if result.success:
                    await self._emit_progress("complete")
                    # Invalidate cache and emit WebSocket event
                    await self._notify_success(result)
                else:
                    await self._notify_error(result)

                # Reset phase tracking
                self._current_phase = None
                self._phase_start_time = None

                return result

            except Exception as e:
                logger.exception("Planner execution failed")
                result = PlannerResult(
                    success=False,
                    planned_at=start,
                    error=str(e),
                    duration_ms=(datetime.now() - start).total_seconds() * 1000,
                )
                await self._notify_error(result)

                # Reset phase tracking
                self._current_phase = None
                self._phase_start_time = None

                return result

    def _count_schedule_slots(self) -> int:
        """Count slots in schedule.json for metadata."""
        import json

        try:
            with Path("data/schedule.json").open() as f:
                data = json.load(f)
                return len(data.get("schedule", []))
        except Exception:
            return 0

    async def _notify_success(self, result: PlannerResult) -> None:
        """Invalidate cache and emit WebSocket event on success."""
        try:
            await cache.invalidate("schedule:current")
            await ws_manager.emit(
                "schedule_updated",
                {
                    "planned_at": result.planned_at.isoformat(),
                    "slot_count": result.slot_count,
                    "duration_ms": result.duration_ms,
                    "status": "success",
                },
            )
            logger.info(
                "Planner completed: %d slots in %.0fms",
                result.slot_count,
                result.duration_ms,
            )
        except Exception as e:
            logger.warning(f"Failed to notify success: {e}")

    async def _notify_error(self, result: PlannerResult) -> None:
        """Emit WebSocket error event on failure."""
        try:
            await ws_manager.emit(
                "planner_error",
                {
                    "planned_at": result.planned_at.isoformat(),
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                },
            )
            logger.error("Planner failed: %s", result.error)
        except Exception as e:
            logger.warning(f"Failed to notify error: {e}")


# Global singleton
planner_service = PlannerService()
