"""
Tests for REV K25 Phase 4: EV Deadline Constraint in Kepler Solver
"""

from datetime import datetime, timedelta

from pytz import timezone as pytz_timezone

from planner.solver.kepler import KeplerSolver
from planner.solver.types import IncentiveBucket, KeplerConfig, KeplerInput, KeplerInputSlot


class TestEVDeadlineConstraint:
    """Test that EV charging respects the deadline constraint."""

    def create_test_input(self, num_slots: int = 24) -> KeplerInput:
        """Create test input with slots spanning multiple hours."""
        slots = []
        tz = pytz_timezone("Europe/Stockholm")
        base_time = tz.localize(datetime(2024, 1, 15, 0, 0, 0))

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

    def test_ev_charging_before_deadline(self):
        """Test that EV charges before the deadline."""
        tz = pytz_timezone("Europe/Stockholm")
        input_data = self.create_test_input(24)

        # Deadline at 10:00 AM (slot 10)
        deadline = tz.localize(datetime(2024, 1, 15, 10, 0, 0))

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
            ev_incentive_buckets=[
                IncentiveBucket(threshold_soc=100.0, value_sek=2.0),
            ],
        )

        solver = KeplerSolver()
        result = solver.solve(input_data, config)

        # Check that there's EV charging before deadline
        pre_deadline_ev = sum(s.ev_charge_kw for s in result.slots[:10])

        # Should have charged before deadline
        assert pre_deadline_ev > 0, "Should charge EV before deadline"

    def test_ev_no_charging_after_deadline(self):
        """Test that EV does NOT charge after the deadline."""
        tz = pytz_timezone("Europe/Stockholm")
        input_data = self.create_test_input(24)

        # Deadline at 10:00 AM (slot 10)
        deadline = tz.localize(datetime(2024, 1, 15, 10, 0, 0))

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
            ev_incentive_buckets=[
                IncentiveBucket(threshold_soc=100.0, value_sek=2.0),
            ],
        )

        solver = KeplerSolver()
        result = solver.solve(input_data, config)

        # Check that there's NO EV charging after deadline
        post_deadline_ev = sum(s.ev_charge_kw for s in result.slots[10:])
        assert post_deadline_ev == 0, (
            f"Should NOT charge EV after deadline, but charged {post_deadline_ev} kW"
        )

    def test_ev_charges_without_deadline(self):
        """Test that EV charges normally when no deadline is set."""
        input_data = self.create_test_input(24)

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
            ev_deadline=None,
            ev_incentive_buckets=[
                IncentiveBucket(threshold_soc=100.0, value_sek=2.0),
            ],
        )

        solver = KeplerSolver()
        result = solver.solve(input_data, config)

        # Check that there's EV charging throughout
        total_ev = sum(s.ev_charge_kw for s in result.slots)

        # Should have charged
        assert total_ev > 0, "Should charge EV when no deadline"

    def test_ev_max_charging_with_urgent_deadline(self):
        """Test that EV maximizes charging when deadline is urgent (< 1 hour)."""
        tz = pytz_timezone("Europe/Stockholm")
        input_data = self.create_test_input(24)

        # Deadline at 02:00 (covers slots 0 and 1)
        deadline = tz.localize(datetime(2024, 1, 15, 2, 0, 0))

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
            ev_deadline_urgent=True,  # Urgent flag set
            ev_incentive_buckets=[
                IncentiveBucket(threshold_soc=100.0, value_sek=2.0),
            ],
        )

        solver = KeplerSolver()
        result = solver.solve(input_data, config)

        # Should charge maximally in slots before deadline (slots 0 and 1 end at 01:00 and 02:00)
        # With urgent flag, solver maximizes charging
        pre_deadline_ev = sum(s.ev_charge_kw for s in result.slots[:2])
        assert pre_deadline_ev > 0, (
            f"Should charge before deadline with urgent flag, got {pre_deadline_ev} kW"
        )

        # No charging after deadline (slot 2+ ends after 02:00)
        post_deadline_ev = sum(s.ev_charge_kw for s in result.slots[2:])
        assert post_deadline_ev == 0, (
            f"Should NOT charge after deadline, charged {post_deadline_ev} kW"
        )
