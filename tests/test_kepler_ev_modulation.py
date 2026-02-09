import sys
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path.cwd()))

from planner.solver.kepler import KeplerSolver
from planner.solver.types import IncentiveBucket, KeplerConfig, KeplerInput, KeplerInputSlot


def test_ev_modulation():
    print("\n--- Testing EV Modulation (Grid Limit) ---")
    solver = KeplerSolver()

    # Grid limit: 5kW
    # House load: 3kW
    # EV max power: 7.4kW
    # This should force EV to modulate at 2kW to fit in 5kW limit.

    config = KeplerConfig(
        capacity_kwh=0.0,
        min_soc_percent=10.0,
        max_soc_percent=90.0,
        max_charge_power_kw=0.0,
        max_discharge_power_kw=0.0,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
        wear_cost_sek_per_kwh=0.0,
        grid_import_limit_kw=5.0,
        ev_charging_enabled=True,
        ev_plugged_in=True,
        ev_max_power_kw=7.4,
        ev_battery_capacity_kwh=100.0,
        ev_current_soc_percent=50.0,
        ev_incentive_buckets=[
            IncentiveBucket(threshold_soc=100.0, value_sek=100.0)  # High incentive to force charge
        ],
    )

    slots = [
        KeplerInputSlot(
            start_time=datetime(2026, 1, 1, 0, 0),
            end_time=datetime(2026, 1, 1, 1, 0),
            load_kwh=3.0,
            pv_kwh=0.0,
            import_price_sek_kwh=1.0,
            export_price_sek_kwh=1.0,
        )
    ]
    input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

    result = solver.solve(input_data, config)

    print(f"Status: {result.status_msg}")
    print(f"EV Charge Power: {result.slots[0].ev_charge_kw} kW")
    print(f"Grid Import: {result.slots[0].grid_import_kwh} kWh (per 1h)")

    # Should be exactly 2.0 kW (5.0 limit - 3.0 load)
    assert abs(result.slots[0].ev_charge_kw - 2.0) < 0.1
    print("Modulation test SUCCESS")


def test_ev_economic_stop():
    print("\n--- Testing EV Economic Stop (Price Guard) ---")
    solver = KeplerSolver()

    # Incentive: 2.0 SEK/kWh
    # Price: 3.0 SEK/kWh
    # Should NOT charge.

    config = KeplerConfig(
        capacity_kwh=10.0,
        min_soc_percent=10.0,
        max_soc_percent=90.0,
        max_charge_power_kw=5.0,
        max_discharge_power_kw=5.0,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
        wear_cost_sek_per_kwh=0.0,
        ev_charging_enabled=True,
        ev_plugged_in=True,
        ev_max_power_kw=7.4,
        ev_battery_capacity_kwh=100.0,
        ev_current_soc_percent=50.0,
        ev_incentive_buckets=[IncentiveBucket(threshold_soc=100.0, value_sek=2.0)],
    )

    slots = [
        KeplerInputSlot(
            start_time=datetime(2026, 1, 1, 0, 0),
            end_time=datetime(2026, 1, 1, 1, 0),
            load_kwh=0.0,
            pv_kwh=0.0,
            import_price_sek_kwh=3.0,
            export_price_sek_kwh=0.5,
        )
    ]
    input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

    result = solver.solve(input_data, config)

    print(f"EV Charge Power: {result.slots[0].ev_charge_kw} kW")
    assert result.slots[0].ev_charge_kw < 0.01
    print("Economic stop test SUCCESS")


def test_multi_bucket_incentives():
    print("\n--- Testing Multi-Bucket Incentives ---")
    solver = KeplerSolver()

    # Buckets:
    # 0-40%: 10.0 SEK/kWh (Emergency)
    # 40-70%: 2.0 SEK/kWh (High)
    # 70-100%: 0.5 SEK/kWh (Normal)

    config = KeplerConfig(
        capacity_kwh=0.0,
        min_soc_percent=0.0,
        max_soc_percent=100.0,
        max_charge_power_kw=100.0,
        max_discharge_power_kw=100.0,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
        wear_cost_sek_per_kwh=0.0,
        ev_charging_enabled=True,
        ev_plugged_in=True,
        ev_max_power_kw=30.0,
        ev_battery_capacity_kwh=100.0,
        ev_current_soc_percent=30.0,
        ev_incentive_buckets=[
            IncentiveBucket(threshold_soc=40.0, value_sek=10.0),
            IncentiveBucket(threshold_soc=70.0, value_sek=2.0),
            IncentiveBucket(threshold_soc=100.0, value_sek=0.5),
        ],
    )

    # Slot 0: Price 5.0 (Should charge B1: 30->40% = 10kWh)
    # Slot 1: Price 1.0 (Should charge B2: 40->70% = 30kWh)
    # Slot 2: Price 0.1 (Should charge B3: 70->100% = 30kWh)

    slots = [
        KeplerInputSlot(
            start_time=datetime(2026, 1, 1, 0, 0),
            end_time=datetime(2026, 1, 1, 1, 0),
            load_kwh=0.0,
            pv_kwh=0.0,
            import_price_sek_kwh=5.0,
            export_price_sek_kwh=0.0,
        ),
        KeplerInputSlot(
            start_time=datetime(2026, 1, 1, 1, 0),
            end_time=datetime(2026, 1, 1, 2, 0),
            load_kwh=0.0,
            pv_kwh=0.0,
            import_price_sek_kwh=1.0,
            export_price_sek_kwh=0.0,
        ),
        KeplerInputSlot(
            start_time=datetime(2026, 1, 1, 2, 0),
            end_time=datetime(2026, 1, 1, 3, 0),
            load_kwh=0.0,
            pv_kwh=0.0,
            import_price_sek_kwh=0.1,
            export_price_sek_kwh=0.0,
        ),
    ]
    input_data = KeplerInput(slots=slots, initial_soc_kwh=0.0)

    result = solver.solve(input_data, config)

    print(f"Slot 0 (Price 5.0, Bucket 10.0): {result.slots[0].ev_charge_kw} kW")
    print(f"Slot 1 (Price 1.0, Bucket 2.0): {result.slots[1].ev_charge_kw} kW")
    print(f"Slot 2 (Price 0.1, Bucket 0.5): {result.slots[2].ev_charge_kw} kW")

    # Slot 2 (Cheapest @ 0.1) fills B1 (10kWh) and B2 (20/30kWh)
    assert abs(result.slots[2].ev_charge_kw - 30.0) < 0.1
    # Slot 1 (Price 1.0) fills remaining B2 (10kWh) because B2 incentive is 2.0 > 1.0
    assert abs(result.slots[1].ev_charge_kw - 10.0) < 0.1
    # Slot 0 (Price 5.0) is too expensive for any bucket
    assert abs(result.slots[0].ev_charge_kw - 0.0) < 0.1
    print("Multi-bucket test SUCCESS")


if __name__ == "__main__":
    try:
        test_ev_modulation()
        test_ev_economic_stop()
        test_multi_bucket_incentives()
        print("\nALL VERIFICATIONS PASSED")
    except Exception as e:
        print(f"\nVERIFICATION FAILED: {e}")
        import traceback

        traceback.print_exc()
