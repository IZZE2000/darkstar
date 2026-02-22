"""
Async Recorder Service

Background task that captures system observations every 15 minutes.
Integrated into the backend lifecycle for production-grade reliability.
"""

import asyncio
import contextlib
import logging
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytz
import yaml

from backend.learning.backfill import BackfillEngine
from backend.loads.service import LoadDisaggregator
from backend.recorder import (
    backfill_missing_prices,
    record_observation_from_current_state,
    run_analyst,
)

logger = logging.getLogger("darkstar.services.recorder")


@dataclass
class RecorderStatus:
    """Current state of the recorder service."""

    running: bool = False
    last_record_at: datetime | None = None
    last_error: str | None = None
    error_count: int = 0
    recent_errors: deque[str] | None = None  # Bounded queue of error messages

    def __post_init__(self) -> None:
        if self.recent_errors is None:
            self.recent_errors = deque(maxlen=10)


class RecorderService:
    """Async recorder service running as FastAPI background task."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._status = RecorderStatus()
        self._config: dict[str, Any] = {}
        self._disaggregator: LoadDisaggregator | None = None

    @property
    def status(self) -> RecorderStatus:
        """Get current recorder status."""
        return self._status

    async def start(self) -> None:
        """Start the recorder background loop."""
        if self._running:
            logger.warning("Recorder already running")
            return

        self._running = True
        self._status.running = True
        self._task = asyncio.create_task(self._loop(), name="recorder_loop")
        logger.info("RecorderService started")

    async def stop(self) -> None:
        """Gracefully stop the recorder."""
        self._running = False
        self._status.running = False

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, TimeoutError):
                await asyncio.wait_for(self._task, timeout=5.0)
            self._task = None

        logger.info("RecorderService stopped")

    def _load_config(self) -> dict[str, Any]:
        try:
            with Path("config.yaml").open(encoding="utf-8") as f:
                result: dict[str, Any] = yaml.safe_load(f) or {}
                return result
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    async def _loop(self) -> None:
        """Main recorder loop."""
        logger.info("Recorder loop starting...")

        self._config = self._load_config()
        tz_name: str = self._config.get("timezone", "Europe/Stockholm")
        tz: pytz.BaseTzInfo = pytz.timezone(tz_name)

        # 1. Backfill energy on startup
        try:
            backfill = BackfillEngine()
            await backfill.run()
        except Exception as e:
            logger.error(f"Energy backfill failed: {e}")

        # 2. Backfill prices on startup
        await backfill_missing_prices()

        # 3. Run Analyst on startup
        await run_analyst()

        # 4. Initialize disaggregator
        self._disaggregator = LoadDisaggregator(self._config)

        last_analyst_date = datetime.now(tz).date()

        while self._running:
            try:
                # Record observation
                await record_observation_from_current_state(self._config, self._disaggregator)
                self._status.last_record_at = datetime.now(UTC)

                # Daily analyst run at ~6 AM
                now_local = datetime.now(tz)
                if now_local.date() > last_analyst_date and now_local.hour >= 6:
                    await run_analyst()
                    last_analyst_date = now_local.date()

                # Sleep until next 15m boundary
                await self._sleep_until_next_quarter()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Recorder loop error: {e}")
                self._status.last_error = str(e)
                self._status.error_count += 1
                self._status.recent_errors.append(f"{datetime.now(UTC).isoformat()}: {e}")  # type: ignore[union-attr]
                await asyncio.sleep(60)  # Back off on error

    async def _sleep_until_next_quarter(self) -> None:
        """Sleep until the next 15-minute boundary."""
        now = datetime.now(UTC)
        minute_block = (now.minute // 15) * 15
        current_slot = now.replace(minute=minute_block, second=0, microsecond=0)
        next_slot = current_slot + timedelta(minutes=15)
        sleep_seconds = max(5.0, (next_slot - now).total_seconds())
        await asyncio.sleep(sleep_seconds)


# Global singleton
recorder_service = RecorderService()
