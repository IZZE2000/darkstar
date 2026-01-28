import pandas as pd

from planner.strategy.s_index import calculate_deficit_ratio, calculate_safety_floor


def test_calculate_deficit_ratio():
    # Scenario 1: Load > PV (Deficit)
    # Load: 100, PV: 60 -> Deficit: 40 -> Ratio: 0.4
    assert calculate_deficit_ratio(100.0, 60.0) == 0.4

    # Scenario 2: PV > Load (Surplus)
    # Load: 100, PV: 120 -> Deficit: -20 -> Ratio: 0.0
    assert calculate_deficit_ratio(100.0, 120.0) == 0.0

    # Scenario 3: Zero Load
    assert calculate_deficit_ratio(0.0, 10.0) == 0.0

    # Scenario 4: Max Ratio (Zero PV)
    assert calculate_deficit_ratio(100.0, 0.0) == 1.0


def test_calculate_safety_floor_defaults():
    # Base Config
    battery_config = {"capacity_kwh": 10.0, "min_soc_percent": 10.0}  # Min 1.0 kWh
    s_index_cfg = {"risk_appetite": 3}  # Neutral (1.0x)

    # DataFrame with Deficit (0.4 ratio)
    # Load 100, PV 60
    df = pd.DataFrame(
        {
            "load_forecast_kwh": [50.0] * 2,  # Total 100
            "pv_forecast_kwh": [30.0] * 2,  # Total 60
        }
    )

    # Expected:
    # Deficit Ratio = 0.4
    # Base Reserve = 0.4 * 10.0 * 1.0 = 4.0 kWh
    # Weather Buffer = 0 (defaults)
    # Floor = 1.0 (Min) + 4.0 = 5.0 kWh

    floor, debug = calculate_safety_floor(df, battery_config, s_index_cfg, "UTC")

    assert floor == 5.0
    assert debug["deficit_ratio"] == 0.4
    assert debug["base_reserve_kwh"] == 4.0


def test_calculate_safety_floor_weather_adders():
    battery_config = {"capacity_kwh": 10.0, "min_soc_percent": 10.0}  # Min 1.0 kWh
    s_index_cfg = {"risk_appetite": 3}

    # DataFrame with Surplus (Ratio 0.0)
    df = pd.DataFrame(
        {
            "load_forecast_kwh": [50.0],
            "pv_forecast_kwh": [60.0],
            "temperature_c": [-5.0],  # Adder +1.0
            "snow_prob": [0.0],
            "cloud_cover": [80.0],  # Adder +0.5
        }
    )

    # Expected:
    # Base Reserve = 0.0
    # Weather Buffer = 1.0 (Temp) + 0.5 (Cloud) = 1.5 kWh
    # Floor = 1.0 + 0 + 1.5 = 2.5 kWh

    floor, debug = calculate_safety_floor(df, battery_config, s_index_cfg, "UTC")

    assert floor == 2.5
    assert debug["weather_buffer_kwh"] == 1.5


def test_calculate_safety_floor_risk_multipliers():
    battery_config = {"capacity_kwh": 10.0, "min_soc_percent": 0.0}
    df = pd.DataFrame(
        {
            "load_forecast_kwh": [100.0],
            "pv_forecast_kwh": [50.0],  # Ratio 0.5
        }
    )

    # Risk 1 (Safety): 1.3x -> Reserve = 0.5 * 10 * 1.3 = 6.5
    cfg_risk1 = {"risk_appetite": 1}
    floor1, _ = calculate_safety_floor(df, battery_config, cfg_risk1, "UTC")

    # Risk 5 (Gambler): 0.8x -> Reserve = 0.5 * 10 * 0.8 = 4.0
    cfg_risk5 = {"risk_appetite": 5}
    floor5, _ = calculate_safety_floor(df, battery_config, cfg_risk5, "UTC")

    assert floor1 == 6.5
    assert floor5 == 4.0
