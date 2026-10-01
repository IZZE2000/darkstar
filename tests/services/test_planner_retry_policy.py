"""Unit tests for PlannerService retry policy."""
from datetime import UTC, datetime, timedelta

import pytest

from backend.services.planner_service import PlannerService, _BACKOFF_STEPS
from planner.errors import PlannerErrorCode


def _fresh_service() -> PlannerService:
    return PlannerService()


def test_config_blocking_sets_suspended():
    svc = _fresh_service()
    svc._consecutive_failures = 1
    svc._apply_retry_policy(PlannerErrorCode.CONFIG_INVALID)
    assert svc._retry_suspended is True
    assert svc._next_retry_at is None


def test_clear_retry_suspension_resets_and_schedules_immediate():
    svc = _fresh_service()
    svc._retry_suspended = True
    svc._next_retry_at = None
    before = datetime.now(UTC)
    svc.clear_retry_suspension()
    assert svc._retry_suspended is False
    assert svc._next_retry_at is not None
    assert svc._next_retry_at >= before


def test_transient_backoff_three_failures():
    svc = _fresh_service()
    expected_delays = _BACKOFF_STEPS[:3]

    for i, expected_delay in enumerate(expected_delays, start=1):
        svc._consecutive_failures = i
        before = datetime.now(UTC)
        svc._apply_retry_policy(PlannerErrorCode.PRICES_UNAVAILABLE)
        after = datetime.now(UTC)

        assert svc._retry_suspended is False
        delay = (svc._next_retry_at - before).total_seconds()
        assert abs(delay - expected_delay) < 2.0, (
            f"Failure #{i}: expected ~{expected_delay}s delay, got {delay:.1f}s"
        )


def test_transient_backoff_caps_at_300():
    svc = _fresh_service()
    svc._consecutive_failures = 99  # Far past the cap
    before = datetime.now(UTC)
    svc._apply_retry_policy(PlannerErrorCode.FORECAST_UNAVAILABLE)
    delay = (svc._next_retry_at - before).total_seconds()
    assert abs(delay - 300) < 2.0, f"Expected cap at 300s, got {delay:.1f}s"


def test_invariant_failure_uses_60s_cadence():
    svc = _fresh_service()
    svc._consecutive_failures = 1
    before = datetime.now(UTC)
    svc._apply_retry_policy(PlannerErrorCode.SOLVER_INFEASIBLE)
    delay = (svc._next_retry_at - before).total_seconds()
    assert abs(delay - 60) < 2.0, f"Expected 60s for invariant, got {delay:.1f}s"


def test_warning_only_codes_do_not_set_last_error_code():
    svc = _fresh_service()
    svc._consecutive_failures = 1
    svc._apply_retry_policy(PlannerErrorCode.DATA_STALE)
    svc._apply_retry_policy(PlannerErrorCode.EV_DEADLINE_PAST)
    # warning_only codes don't modify retry state — _last_error_code is still None
    assert svc._retry_suspended is False
    assert svc._next_retry_at is None


def test_success_resets_all_state():
    svc = _fresh_service()
    svc._consecutive_failures = 5
    svc._retry_suspended = True
    svc._last_error_code = PlannerErrorCode.CONFIG_INVALID
    svc._last_error_at = datetime.now(UTC)
    svc._last_error_details = {"x": 1}
    svc._next_retry_at = datetime.now(UTC) + timedelta(minutes=5)

    svc._on_success()

    assert svc._consecutive_failures == 0
    assert svc._retry_suspended is False
    assert svc._last_error_code is None
    assert svc._last_error_at is None
    assert svc._last_error_details is None
    assert svc._next_retry_at is None


def test_retry_in_s_returns_none_when_suspended():
    svc = _fresh_service()
    svc._retry_suspended = True
    assert svc.retry_in_s is None


def test_retry_in_s_returns_seconds_remaining():
    svc = _fresh_service()
    svc._retry_suspended = False
    svc._next_retry_at = datetime.now(UTC) + timedelta(seconds=120)
    remaining = svc.retry_in_s
    assert remaining is not None
    assert 118 <= remaining <= 121


def test_transient_retry_is_due_in_scheduler_utc_terms(monkeypatch):
    """Regression: next_retry_at must be tz-aware UTC.

    SchedulerService compares it against datetime.now(UTC) and treats a naive
    value as UTC. A naive local timestamp therefore delayed the 60s retry by the
    local UTC offset (2h in CEST) — the planner sat idle 00:00→02:02 after a
    brief Nordpool outage and the executor declared the schedule stale.
    """
    import time

    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset not available on this platform")
    monkeypatch.setenv("TZ", "Europe/Stockholm")
    time.tzset()
    try:
        svc = _fresh_service()
        svc._consecutive_failures = 1
        svc._apply_retry_policy(PlannerErrorCode.PRICES_UNAVAILABLE)

        retry_at = svc.next_retry_at
        assert retry_at is not None
        assert retry_at.tzinfo is not None
        # Same normalisation SchedulerService applies before comparing
        retry_at_utc = retry_at if retry_at.tzinfo else retry_at.replace(tzinfo=UTC)
        delay = (retry_at_utc - datetime.now(UTC)).total_seconds()
        assert 55 <= delay <= 61, f"Retry should be due in ~60s, got {delay:.0f}s"
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()
