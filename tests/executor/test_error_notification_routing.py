"""Errors and overrides can be routed to a separate notify service.

`notifications.error_service` (e.g. notify.persistent_notification) receives
error and override notifications; everything else keeps using `service`.
Unset falls back to `service`, preserving previous behaviour.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from executor.actions import ActionDispatcher
from executor.config import ExecutorConfig, NotificationConfig, load_executor_config

PHONE = "notify.mobile_app_phone"
PANEL = "notify.persistent_notification"


def _dispatcher(error_service: str | None) -> tuple[ActionDispatcher, MagicMock]:
    ha = MagicMock()
    ha.send_notification = AsyncMock(return_value=True)
    config = ExecutorConfig(
        notifications=NotificationConfig(service=PHONE, error_service=error_service)
    )
    return ActionDispatcher(ha_client=ha, config=config), ha


def _services(ha: MagicMock) -> list[str]:
    return [call.args[0] for call in ha.send_notification.await_args_list]


@pytest.mark.asyncio
async def test_error_and_override_go_to_error_service():
    dispatcher, ha = _dispatcher(PANEL)

    await dispatcher.notify_error("Schedule is stale (2.0h old, max 2h) — holding")
    await dispatcher.notify_override("slot_failure_fallback", "No valid slot plan found")
    await dispatcher._maybe_notify("error", "action failed")
    await dispatcher._maybe_notify("override", "override active")

    assert _services(ha) == [PANEL, PANEL, PANEL, PANEL]


@pytest.mark.asyncio
async def test_routine_notifications_stay_on_main_service():
    dispatcher, ha = _dispatcher(PANEL)

    await dispatcher._maybe_notify("charge_start", "Grid charging started")
    await dispatcher._send_notification("Executor paused", title="Darkstar Executor Paused")

    assert _services(ha) == [PHONE, PHONE]


@pytest.mark.asyncio
async def test_errors_fall_back_to_main_service_when_unset():
    dispatcher, ha = _dispatcher(None)

    await dispatcher.notify_error("boom")
    await dispatcher.notify_override("slot_failure_fallback", "No valid slot plan found")

    assert _services(ha) == [PHONE, PHONE]


def test_error_service_parsed_from_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        f"executor:\n  notifications:\n    service: {PHONE}\n    error_service: {PANEL}\n",
        encoding="utf-8",
    )
    cfg = load_executor_config(str(path))
    assert cfg.notifications.service == PHONE
    assert cfg.notifications.error_service == PANEL


def test_empty_error_service_parsed_as_none(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        'executor:\n  notifications:\n    service: x.y\n    error_service: ""\n',
        encoding="utf-8",
    )
    assert load_executor_config(str(path)).notifications.error_service is None
