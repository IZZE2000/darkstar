"""
REV K25 Phase 6: Integration Tests for EV Departure Time Constraint

Tests the full pipeline integration from deadline calculation through solver execution.
"""

from datetime import datetime, timedelta

from pytz import timezone as pytz_timezone

from planner.pipeline import calculate_ev_deadline
from planner.solver.kepler import KeplerSolver
from planner.solver.types import IncentiveBucket, KeplerConfig, KeplerInput, KeplerInputSlot


class TestEVDepartureIntegration:
    """Integration tests for EV departure time feature."""

    def create_test_input(self, num_slots: int = 24, start_hour: int = 0) -> KeplerInput:
        """Create test input with slots spanning multiple hours."""
        slots = []
        tz = pytz_timezone("Europe/Stockholm")
        base_time = tz.localize(datetime(2024, 1, 15, start_hour, 0, 0))

        for i in range(num_slots):
            start = base_time + timedelta(hours=i)
            end = start + timedelta(hours=1)
            slots.append(
                KeplerInputSlot(
                    start_time=start,
                    end_time=end,
                    load_kwh=1.0,
                    pv_kwh=0.0,
                    import_price_sek_kwh=1.0,
                    export_price_sek_kwh=0.5,
                )
            )

        return KeplerInput(
            slots=slots,
            initial_soc_kwh=5.0,
        )

    def test_scenario1_plug_at_15_departure_07(self):
        """
        Test 1: Car plugged in at 15:00, departure 07:00 → charges overnight before 07:00.

        When plugging in at 15:00 with a 07:00 departure, the deadline should be
        tomorrow 07:00, giving ~16 hours to charge overnight.
        """
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 15, 0, 0))  # 15:00 today

        # Calculate deadline
        deadline = calculate_ev_deadline("07:00", now, "Europe/Stockholm")

        # Should be tomorrow 07:00
        assert deadline.day == 16
        assert deadline.hour == 7
        assert deadline.minute == 0

        # Create input starting from 15:00
        slots = []
        base_time = now
        for i in range(24):
            start = base_time + timedelta(hours=i)
            end = start + timedelta(hours=1)
            slots.append(
                KeplerInputSlot(
                    start_time=start,
                    end_time=end,
                    load_kwh=1.0,
                    pv_kwh=0.0,
                    import_price_sek_kwh=0.5 if i > 10 else 2.0,  # Cheaper at night
                    export_price_sek_kwh=0.3,
                )
            )

        input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

        config = KeplerConfig(
            capacity_kwh=10.0,
            min_soc_percent=10.0,
            max_soc_percent=100.0,
            max_charge_power_kw=5.0,
            max_discharge_power_kw=5.0,
            charge_efficiency=0.95,
            discharge_efficiency=0.95,
            wear_cost_sek_per_kwh=0.1,
            ev_charging_enabled=True,
            ev_max_power_kw=3.0,
            ev_battery_capacity_kwh=50.0,
            ev_current_soc_percent=50.0,
            ev_plugged_in=True,
            ev_deadline=deadline,
            ev_deadline_urgent=False,
            ev_incentive_buckets=[
                IncentiveBucket(
                    threshold_soc=100.0, value_sek=100.0
                ),  # High incentive to ensure charging
            ],
        )

        solver = KeplerSolver()
        result = solver.solve(input_data, config)

        # Find slots before deadline (tomorrow 07:00)
        deadline_slot = None
        for i, s in enumerate(result.slots):
            if s.end_time > deadline:
                deadline_slot = i
                break

        assert deadline_slot is not None, "Should find deadline slot"

        # All charging should happen before deadline
        pre_deadline_ev = sum(s.ev_charge_kw for s in result.slots[:deadline_slot])
        post_deadline_ev = sum(s.ev_charge_kw for s in result.slots[deadline_slot:])

        assert pre_deadline_ev > 0, "Should charge before deadline"
        assert post_deadline_ev == 0, f"Should NOT charge after deadline, got {post_deadline_ev} kW"

    def test_scenario2_plug_at_06_departure_07(self):
        """
        Test 2: Car plugged in at 06:00, departure 07:00 → charges immediately for 1 hour.

        When plugging in at 06:00 with a 07:00 departure, only 1 hour remains.
        Should charge maximally in that 1 hour window.
        """
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 6, 0, 0))  # 06:00 today

        # Calculate deadline
        deadline = calculate_ev_deadline("07:00", now, "Europe/Stockholm")

        # Should be today 07:00
        assert deadline.day == 15
        assert deadline.hour == 7
        assert deadline.minute == 0

        # Only 1 hour to deadline
        hours_to_deadline = (deadline - now).total_seconds() / 3600
        assert hours_to_deadline == 1.0

        # Create input starting from 06:00
        slots = []
        base_time = now
        for i in range(6):  # Just 6 hours
            start = base_time + timedelta(hours=i)
            end = start + timedelta(hours=1)
            slots.append(
                KeplerInputSlot(
                    start_time=start,
                    end_time=end,
                    load_kwh=1.0,
                    pv_kwh=0.0,
                    import_price_sek_kwh=1.0,
                    export_price_sek_kwh=0.5,
                )
            )

        input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

        # Should be urgent (< 1 hour)
        config = KeplerConfig(
            capacity_kwh=10.0,
            min_soc_percent=10.0,
            max_soc_percent=100.0,
            max_charge_power_kw=5.0,
            max_discharge_power_kw=5.0,
            charge_efficiency=0.95,
            discharge_efficiency=0.95,
            wear_cost_sek_per_kwh=0.1,
            ev_charging_enabled=True,
            ev_max_power_kw=3.0,
            ev_battery_capacity_kwh=50.0,
            ev_current_soc_percent=20.0,  # Low SoC - needs charging
            ev_plugged_in=True,
            ev_deadline=deadline,
            ev_deadline_urgent=hours_to_deadline < 1.0,  # Should be True
            ev_incentive_buckets=[
                IncentiveBucket(
                    threshold_soc=100.0, value_sek=100.0
                ),  # High incentive to ensure charging
            ],
        )

        solver = KeplerSolver()
        result = solver.solve(input_data, config)

        # First slot (06:00-07:00) should have maximum charging
        # Second slot (07:00-08:00) should have zero charging
        assert result.slots[0].ev_charge_kw > 0, "Should charge in first slot"
        assert result.slots[1].ev_charge_kw == 0, "Should NOT charge after deadline"

    def test_scenario3_plug_at_09_after_deadline(self):
        """
        Test 3: Car plugged in at 09:00 (after deadline) → charges for next day's deadline.

        When plugging in at 09:00 with a 07:00 departure, today's deadline has passed.
        Should schedule charging for tomorrow 07:00 instead.
        """
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 9, 0, 0))  # 09:00 today (after 07:00)

        # Calculate deadline
        deadline = calculate_ev_deadline("07:00", now, "Europe/Stockholm")

        # Should be tomorrow 07:00 (next occurrence)
        assert deadline.day == 16
        assert deadline.hour == 7
        assert deadline.minute == 0

        # Create input starting from 09:00
        slots = []
        base_time = now
        for i in range(48):  # 48 hours to cover deadline
            start = base_time + timedelta(hours=i)
            end = start + timedelta(hours=1)
            slots.append(
                KeplerInputSlot(
                    start_time=start,
                    end_time=end,
                    load_kwh=1.0,
                    pv_kwh=0.0,
                    import_price_sek_kwh=1.0,
                    export_price_sek_kwh=0.5,
                )
            )

        input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

        config = KeplerConfig(
            capacity_kwh=10.0,
            min_soc_percent=10.0,
            max_soc_percent=100.0,
            max_charge_power_kw=5.0,
            max_discharge_power_kw=5.0,
            charge_efficiency=0.95,
            discharge_efficiency=0.95,
            wear_cost_sek_per_kwh=0.1,
            ev_charging_enabled=True,
            ev_max_power_kw=3.0,
            ev_battery_capacity_kwh=50.0,
            ev_current_soc_percent=50.0,
            ev_plugged_in=True,
            ev_deadline=deadline,
            ev_deadline_urgent=False,  # Plenty of time
            ev_incentive_buckets=[
                IncentiveBucket(
                    threshold_soc=100.0, value_sek=100.0
                ),  # High incentive to ensure charging
            ],
        )

        solver = KeplerSolver()
        result = solver.solve(input_data, config)

        # Find deadline slot
        deadline_slot = None
        for i, s in enumerate(result.slots):
            if s.end_time > deadline:
                deadline_slot = i
                break

        assert deadline_slot is not None, "Should find deadline slot"

        # All charging should be before tomorrow 07:00
        pre_deadline_ev = sum(s.ev_charge_kw for s in result.slots[:deadline_slot])
        post_deadline_ev = sum(s.ev_charge_kw for s in result.slots[deadline_slot:])

        assert pre_deadline_ev > 0, "Should charge before next day's deadline"
        assert post_deadline_ev == 0, f"Should NOT charge after deadline, got {post_deadline_ev} kW"
