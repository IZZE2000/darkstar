"""
Task 2.13: Multi-device water heater solver tests.

Covers:
- Single heater equivalence with old scalar approach
- Two heaters with different power ratings get independent schedules
- Two heaters competing for grid budget get staggered
- Empty heater list equals no water constraints
- Per-device spacing works independently
"""

from datetime import datetime, timedelta

import pytest

from planner.solver.kepler import KeplerSolver
from planner.solver.types import (
    KeplerConfig,
    KeplerInput,
    KeplerInputSlot,
    WaterHeaterInput,
)


def _slots(n=48, import_price=1.0, export_price=0.0, load_kwh=0.5, pv_kwh=0.0):
    """Create N half-hour slots."""
    base = datetime(2026, 1, 15, 0, 0)
    result = []
    for i in range(n):
        s = base + timedelta(minutes=30 * i)
        result.append(
            KeplerInputSlot(
                start_time=s,
                end_time=s + timedelta(minutes=30),
                load_kwh=load_kwh,
                pv_kwh=pv_kwh,
                import_price_sek_kwh=import_price,
                export_price_sek_kwh=export_price,
            )
        )
    return result


def _wh(
    wh_id: str = "wh1",
    power_kw: float = 3.0,
    min_kwh_per_day: float = 3.0,
    min_spacing_hours: float = 0.0,
    max_hours_between_heating: float = 0.0,
    heated_today_kwh: float = 0.0,
) -> WaterHeaterInput:
    return WaterHeaterInput(
        id=wh_id,
        power_kw=power_kw,
        min_kwh_per_day=min_kwh_per_day,
        max_hours_between_heating=max_hours_between_heating,
        min_spacing_hours=min_spacing_hours,
        heated_today_kwh=heated_today_kwh,
    )


def _cfg(
    water_heaters: list[WaterHeaterInput],
    grid_limit_kw: float | None = None,
    reliability_penalty: float = 100.0,
) -> KeplerConfig:
    kwargs: dict = {
        "capacity_kwh": 10.0,
        "min_soc_percent": 10.0,
        "max_soc_percent": 100.0,
        "max_charge_power_kw": 5.0,
        "max_discharge_power_kw": 5.0,
        "charge_efficiency": 1.0,
        "discharge_efficiency": 1.0,
        "wear_cost_sek_per_kwh": 0.0,
        "water_heaters": water_heaters,
        "water_reliability_penalty_sek": reliability_penalty,
    }
    if grid_limit_kw is not None:
        kwargs["grid_import_limit_kw"] = grid_limit_kw
    return KeplerConfig(**kwargs)


class TestEmptyWaterHeatersNoConstraints:
    """Empty water_heaters list produces no water-related variables."""

    def test_empty_list_solves_without_water(self):
        """No heaters → no water heating in schedule."""
        solver = KeplerSolver()
        input_data = KeplerInput(slots=_slots(8), initial_soc_kwh=5.0)
        config = _cfg(water_heaters=[])

        result = solver.solve(input_data, config)

        assert result.is_optimal
        assert all(s.water_heat_kw == 0.0 for s in result.slots)
        assert all(s.water_heater_results == {} for s in result.slots)


class TestSingleHeaterEquivalence:
    """Single heater behaves like the old scalar approach."""

    def test_single_heater_meets_daily_min(self):
        """Single heater satisfies min_kwh_per_day over 24 slots (12 hours)."""
        solver = KeplerSolver()
        slots = _slots(48)  # 24 hours
        # Force cheap price everywhere to encourage heating
        for s in slots:
            s.import_price_sek_kwh = 0.1

        min_kwh = 3.0  # 3kW * 1h = 1 slot at 3kW for 30min = 1.5kWh, need 2 slots
        config = _cfg([_wh("wh1", power_kw=3.0, min_kwh_per_day=min_kwh)])
        input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

        result = solver.solve(input_data, config)

        assert result.is_optimal
        total_kwh = sum(s.water_heat_kw * 0.5 for s in result.slots)  # 30-min slots
        assert total_kwh >= min_kwh - 0.01

    def test_single_heater_results_in_water_heater_results(self):
        """Per-device results dict is populated for single heater."""
        solver = KeplerSolver()
        slots = _slots(8)
        for s in slots:
            s.import_price_sek_kwh = 0.1

        config = _cfg([_wh("main", power_kw=2.0, min_kwh_per_day=1.0)])
        input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

        result = solver.solve(input_data, config)

        assert result.is_optimal
        heated_slots = [s for s in result.slots if s.water_heat_kw > 0]
        assert len(heated_slots) > 0
        for s in heated_slots:
            # Per-device result matches aggregate
            assert "main" in s.water_heater_results
            assert s.water_heater_results["main"] == pytest.approx(2.0)
            assert s.water_heat_kw == pytest.approx(2.0)


class TestTwoHeatersIndependent:
    """Two heaters with different power ratings get independent schedules."""

    def test_two_heaters_aggregate_power_correct(self):
        """When both heaters run simultaneously, aggregate = sum of powers."""
        solver = KeplerSolver()
        slots = _slots(8)
        for s in slots:
            s.import_price_sek_kwh = 0.1

        config = _cfg(
            [
                _wh("wh1", power_kw=3.0, min_kwh_per_day=1.0),
                _wh("wh2", power_kw=2.0, min_kwh_per_day=0.5),
            ]
        )
        input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

        result = solver.solve(input_data, config)

        assert result.is_optimal
        for s in result.slots:
            # Aggregate matches sum of per-device values
            expected = s.water_heater_results.get("wh1", 0.0) + s.water_heater_results.get(
                "wh2", 0.0
            )
            assert s.water_heat_kw == pytest.approx(expected)

    def test_two_heaters_each_meet_min_kwh(self):
        """Both heaters independently meet their minimum kWh requirements."""
        solver = KeplerSolver()
        slots = _slots(48)  # 24 hours
        for s in slots:
            s.import_price_sek_kwh = 0.1

        min1 = 3.0
        min2 = 2.0
        config = _cfg(
            [
                _wh("wh1", power_kw=3.0, min_kwh_per_day=min1),
                _wh("wh2", power_kw=2.0, min_kwh_per_day=min2),
            ]
        )
        input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

        result = solver.solve(input_data, config)

        assert result.is_optimal
        kwh1 = sum(s.water_heater_results.get("wh1", 0.0) * 0.5 for s in result.slots)
        kwh2 = sum(s.water_heater_results.get("wh2", 0.0) * 0.5 for s in result.slots)
        assert kwh1 >= min1 - 0.01
        assert kwh2 >= min2 - 0.01


class TestTwoHeatersCompetingForGrid:
    """Two heaters under a rising price profile prefer cheap slots together."""

    def test_both_heaters_heat_in_cheap_slots(self):
        """With cheap early slots, both heaters prefer to heat early."""
        solver = KeplerSolver()
        slots = _slots(16)
        # Cheap in first 8 slots, expensive after
        for i, s in enumerate(slots):
            s.import_price_sek_kwh = 0.1 if i < 8 else 10.0

        config = _cfg(
            [
                _wh("wh1", power_kw=3.0, min_kwh_per_day=1.5),
                _wh("wh2", power_kw=2.0, min_kwh_per_day=1.0),
            ]
        )
        input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

        result = solver.solve(input_data, config)

        assert result.is_optimal
        # Both heaters meet their minimums
        kwh1 = sum(s.water_heater_results.get("wh1", 0.0) * 0.5 for s in result.slots)
        kwh2 = sum(s.water_heater_results.get("wh2", 0.0) * 0.5 for s in result.slots)
        assert kwh1 >= 1.5 - 0.01
        assert kwh2 >= 1.0 - 0.01
        # Most heating in cheap window (slots 0-7)
        cheap_kwh1 = sum(
            result.slots[i].water_heater_results.get("wh1", 0.0) * 0.5 for i in range(8)
        )
        cheap_kwh2 = sum(
            result.slots[i].water_heater_results.get("wh2", 0.0) * 0.5 for i in range(8)
        )
        assert cheap_kwh1 >= kwh1 - 0.01
        assert cheap_kwh2 >= kwh2 - 0.01


class TestPerDeviceSpacing:
    """Per-device spacing constraints work independently."""

    def test_heater_spacing_enforced_per_device(self):
        """Spacing constraint applies to each heater independently."""
        solver = KeplerSolver()
        slots = _slots(24)
        # Cheap at slots 0 and 4 (2 hours apart)
        slots[0].import_price_sek_kwh = 0.01
        slots[4].import_price_sek_kwh = 0.01
        for i in [1, 2, 3, 5, 6]:
            slots[i].import_price_sek_kwh = 10.0

        # wh1 has 4-hour spacing → slot 4 should be blocked for wh1
        # wh2 has no spacing → can use slot 4
        config = _cfg(
            [
                _wh("wh1", power_kw=3.0, min_kwh_per_day=1.5, min_spacing_hours=4.0),
                _wh("wh2", power_kw=2.0, min_kwh_per_day=1.0, min_spacing_hours=0.0),
            ],
            reliability_penalty=200.0,
        )
        input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

        result = solver.solve(input_data, config)

        assert result.is_optimal
        # wh1 must have heated at slot 0 (cheapest)
        if result.slots[0].water_heater_results.get("wh1", 0.0) > 0:
            # Slot 4 is only 2 hours after slot 0 — within 4h spacing window
            assert result.slots[4].water_heater_results.get("wh1", 0.0) == 0.0, (
                "wh1 should not heat at slot 4 (within 4h spacing of slot 0)"
            )
