"""
Test ARC15 Kepler Adapter Integration

Tests for the Kepler adapter's support of the new entity-centric config structure
with multiple water heaters and EV chargers.
"""

import pandas as pd
import pytz

from planner.solver.adapter import (
    _aggregate_ev_chargers,
    _aggregate_water_heaters,
    _get_config_version,
    config_to_kepler_config,
    planner_to_kepler_input,
)


class TestConfigVersionDetection:
    """Test config format version detection."""

    def test_detects_version_1_by_default(self):
        """Should default to version 1 when no config_version field."""
        config = {"battery": {"capacity_kwh": 13.5}}
        assert _get_config_version(config) == 1

    def test_detects_version_2_explicitly(self):
        """Should detect explicit version 2."""
        config = {"config_version": 2, "battery": {"capacity_kwh": 13.5}}
        assert _get_config_version(config) == 2

    def test_detects_version_as_int(self):
        """Should handle string version and convert to int."""
        config = {"config_version": "2"}
        assert _get_config_version(config) == 2


class TestWaterHeaterAggregation:
    """Test aggregation of multiple water heaters."""

    def test_empty_array_returns_disabled_config(self):
        """Empty water_heaters array should return zero-power config."""
        result = _aggregate_water_heaters([])
        assert result["power_kw"] == 0.0
        assert result["min_kwh_per_day"] == 0.0

    def test_single_water_heater_with_legacy_fallback(self):
        """Single water heater should use legacy section for comfort settings."""
        heaters = [
            {
                "id": "main",
                "enabled": True,
                "power_kw": 3.0,
                "min_kwh_per_day": 6.0,
                "max_hours_between_heating": 6.0,
                "water_min_spacing_hours": 4.0,
            }
        ]
        legacy_wh = {
            "comfort_level": 4,
            "enable_top_ups": True,
            "defer_up_to_hours": 2.0,
            "min_spacing_hours": 5.0,  # Should be overridden by water_min_spacing_hours
        }
        result = _aggregate_water_heaters(heaters, legacy_wh)
        assert result["power_kw"] == 3.0
        assert result["min_kwh_per_day"] == 6.0
        assert result["comfort_level"] == 4  # From legacy
        assert result["enable_top_ups"] is True  # From legacy
        assert result["max_hours_between_heating"] == 6.0  # From heater
        assert result["min_spacing_hours"] == 4.0  # From heater's water_min_spacing_hours
        assert result["defer_up_to_hours"] == 2.0  # From legacy

    def test_multiple_water_heaters_sums_power(self):
        """Multiple water heaters should have power summed."""
        heaters = [
            {"id": "main", "enabled": True, "power_kw": 3.0, "min_kwh_per_day": 6.0},
            {"id": "backup", "enabled": True, "power_kw": 2.0, "min_kwh_per_day": 4.0},
        ]
        legacy_wh = {"comfort_level": 3}
        result = _aggregate_water_heaters(heaters, legacy_wh)
        assert result["power_kw"] == 5.0
        assert result["min_kwh_per_day"] == 10.0

    def test_disabled_water_heaters_excluded(self):
        """Disabled water heaters should not be included in aggregation."""
        heaters = [
            {"id": "main", "enabled": True, "power_kw": 3.0, "min_kwh_per_day": 6.0},
            {"id": "backup", "enabled": False, "power_kw": 2.0, "min_kwh_per_day": 4.0},
        ]
        legacy_wh = {"comfort_level": 3}
        result = _aggregate_water_heaters(heaters, legacy_wh)
        assert result["power_kw"] == 3.0
        assert result["min_kwh_per_day"] == 6.0

    def test_all_disabled_returns_zero_config(self):
        """If all heaters disabled, return zero-power config."""
        heaters = [
            {"id": "main", "enabled": False, "power_kw": 3.0, "min_kwh_per_day": 6.0},
        ]
        legacy_wh = {"comfort_level": 3}
        result = _aggregate_water_heaters(heaters, legacy_wh)
        assert result["power_kw"] == 0.0
        assert result["min_kwh_per_day"] == 0.0

    def test_uses_legacy_spacing_when_heater_has_none(self):
        """Should fall back to legacy min_spacing_hours when heater lacks water_min_spacing_hours."""
        heaters = [
            {
                "id": "main",
                "enabled": True,
                "power_kw": 3.0,
                "min_kwh_per_day": 6.0,
                # No water_min_spacing_hours
            }
        ]
        legacy_wh = {"min_spacing_hours": 6.0}
        result = _aggregate_water_heaters(heaters, legacy_wh)
        assert result["min_spacing_hours"] == 6.0  # From legacy fallback

    def test_without_legacy_uses_heater_values(self):
        """Should use heater values when no legacy section provided."""
        heaters = [
            {
                "id": "main",
                "enabled": True,
                "power_kw": 3.0,
                "min_kwh_per_day": 6.0,
                "comfort_level": 5,
                "enable_top_ups": False,
                "defer_up_to_hours": 3.0,
                "water_min_spacing_hours": 4.0,
            }
        ]
        result = _aggregate_water_heaters(heaters, None)
        assert result["comfort_level"] == 5
        assert result["enable_top_ups"] is False
        assert result["defer_up_to_hours"] == 3.0
        assert result["min_spacing_hours"] == 4.0


class TestEVChargerAggregation:
    """Test aggregation of multiple EV chargers."""

    def test_empty_array_returns_disabled_config(self):
        """Empty ev_chargers array should return zero-power config."""
        result = _aggregate_ev_chargers([])
        assert result["max_power_kw"] == 0.0
        assert result["battery_capacity_kwh"] == 0.0
        assert result["penalty_levels"] == []

    def test_single_ev_charger_preserved(self):
        """Single EV charger should be returned as-is."""
        chargers = [
            {
                "id": "tesla",
                "enabled": True,
                "max_power_kw": 11.0,
                "battery_capacity_kwh": 82.0,
                "penalty_levels": [
                    {"max_soc": 50.0, "penalty_sek": 0.5},
                    {"max_soc": 80.0, "penalty_sek": 0.2},
                ],
            }
        ]
        result = _aggregate_ev_chargers(chargers)
        assert result["max_power_kw"] == 11.0
        assert result["battery_capacity_kwh"] == 82.0
        assert len(result["penalty_levels"]) == 2

    def test_multiple_ev_chargers_sums_power(self):
        """Multiple EV chargers should have max power summed."""
        chargers = [
            {"id": "tesla", "enabled": True, "max_power_kw": 11.0, "battery_capacity_kwh": 82.0},
            {"id": "fiat", "enabled": True, "max_power_kw": 7.4, "battery_capacity_kwh": 42.0},
        ]
        result = _aggregate_ev_chargers(chargers)
        assert result["max_power_kw"] == 18.4

    def test_multiple_ev_uses_largest_battery(self):
        """Multiple EVs should use largest battery capacity (conservative)."""
        chargers = [
            {"id": "tesla", "enabled": True, "max_power_kw": 11.0, "battery_capacity_kwh": 82.0},
            {"id": "fiat", "enabled": True, "max_power_kw": 7.4, "battery_capacity_kwh": 42.0},
        ]
        result = _aggregate_ev_chargers(chargers)
        assert result["battery_capacity_kwh"] == 82.0  # Largest

    def test_disabled_ev_chargers_excluded(self):
        """Disabled EV chargers should not be included."""
        chargers = [
            {"id": "tesla", "enabled": True, "max_power_kw": 11.0, "battery_capacity_kwh": 82.0},
            {"id": "fiat", "enabled": False, "max_power_kw": 7.4, "battery_capacity_kwh": 42.0},
        ]
        result = _aggregate_ev_chargers(chargers)
        assert result["max_power_kw"] == 11.0
        assert result["battery_capacity_kwh"] == 82.0

    def test_merges_penalty_buckets_by_threshold(self):
        """Multiple EVs should merge penalty buckets, taking max penalty at each threshold."""
        chargers = [
            {
                "id": "tesla",
                "enabled": True,
                "max_power_kw": 11.0,
                "battery_capacity_kwh": 82.0,
                "penalty_levels": [
                    {"max_soc": 50.0, "penalty_sek": 0.5},
                    {"max_soc": 80.0, "penalty_sek": 0.2},
                ],
            },
            {
                "id": "fiat",
                "enabled": True,
                "max_power_kw": 7.4,
                "battery_capacity_kwh": 42.0,
                "penalty_levels": [
                    {"max_soc": 50.0, "penalty_sek": 0.3},  # Lower penalty at 50%
                    {"max_soc": 90.0, "penalty_sek": 0.1},  # New threshold
                ],
            },
        ]
        result = _aggregate_ev_chargers(chargers)

        # Should have 3 unique thresholds: 50, 80, 90
        assert len(result["penalty_levels"]) == 3

        # At 50%, should use max penalty (0.5 from Tesla)
        soc_50 = next(p for p in result["penalty_levels"] if p["max_soc"] == 50.0)
        assert soc_50["penalty_sek"] == 0.5


class TestKeplerConfigWithARC15:
    """Test full config_to_kepler_config with ARC15 structure."""

    def test_uses_legacy_format_when_no_new_arrays(self):
        """Should use legacy water_heating and ev_charger when new arrays absent."""
        config = {
            "config_version": 1,
            "system": {"has_ev_charger": True},
            "battery": {"capacity_kwh": 13.5, "max_charge_a": 100, "max_discharge_a": 100},
            "water_heating": {
                "power_kw": 3.0,
                "min_kwh_per_day": 6.0,
                "comfort_level": 3,
            },
            "ev_charger": {
                "max_power_kw": 11.0,
                "battery_capacity_kwh": 82.0,
            },
        }

        kepler_cfg = config_to_kepler_config(config)

        assert kepler_cfg.water_heating_power_kw == 3.0
        assert kepler_cfg.water_heating_min_kwh == 6.0
        assert kepler_cfg.ev_max_power_kw == 11.0
        assert kepler_cfg.ev_battery_capacity_kwh == 82.0
        assert kepler_cfg.ev_charging_enabled is True

    def test_uses_new_format_when_config_version_2(self):
        """Should aggregate from new water_heaters/ev_chargers arrays when version 2."""
        config = {
            "config_version": 2,
            "system": {"has_ev_charger": True},
            "battery": {"capacity_kwh": 13.5, "max_charge_a": 100, "max_discharge_a": 100},
            "water_heaters": [
                {
                    "id": "main",
                    "enabled": True,
                    "power_kw": 3.0,
                    "min_kwh_per_day": 6.0,
                    "comfort_level": 4,
                    "enable_top_ups": True,
                    "max_hours_between_heating": 6.0,
                    "min_spacing_hours": 4.0,
                },
                {
                    "id": "backup",
                    "enabled": True,
                    "power_kw": 2.0,
                    "min_kwh_per_day": 4.0,
                },
            ],
            "ev_chargers": [
                {
                    "id": "tesla",
                    "enabled": True,
                    "max_power_kw": 11.0,
                    "battery_capacity_kwh": 82.0,
                },
            ],
        }

        kepler_cfg = config_to_kepler_config(config)

        # Water heaters should be summed: 3.0 + 2.0 = 5.0 kW, 6.0 + 4.0 = 10.0 kWh
        assert kepler_cfg.water_heating_power_kw == 5.0
        assert kepler_cfg.water_heating_min_kwh == 10.0

        # EV charger should use value from array
        assert kepler_cfg.ev_max_power_kw == 11.0
        assert kepler_cfg.ev_battery_capacity_kwh == 82.0
        assert kepler_cfg.ev_charging_enabled is True

    def test_disables_water_heating_when_all_disabled(self):
        """Should disable water heating when all heaters are disabled."""
        config = {
            "config_version": 2,
            "system": {},
            "battery": {"capacity_kwh": 13.5, "max_charge_a": 100, "max_discharge_a": 100},
            "water_heaters": [
                {"id": "main", "enabled": False, "power_kw": 3.0, "min_kwh_per_day": 6.0},
            ],
            "ev_chargers": [],
        }

        kepler_cfg = config_to_kepler_config(config)

        assert kepler_cfg.water_heating_power_kw == 0.0
        assert kepler_cfg.water_heating_min_kwh == 0.0

    def test_disables_ev_when_all_disabled(self):
        """Should disable EV charging when all chargers are disabled."""
        config = {
            "config_version": 2,
            "system": {"has_ev_charger": True},  # Legacy flag should be ignored
            "battery": {"capacity_kwh": 13.5, "max_charge_a": 100, "max_discharge_a": 100},
            "water_heaters": [],
            "ev_chargers": [
                {
                    "id": "tesla",
                    "enabled": False,
                    "max_power_kw": 11.0,
                    "battery_capacity_kwh": 82.0,
                },
            ],
        }

        kepler_cfg = config_to_kepler_config(config)

        assert kepler_cfg.ev_charging_enabled is False
        assert kepler_cfg.ev_max_power_kw == 0.0

    def test_backward_compatibility_with_legacy_config(self):
        """Should work with old config format without new arrays."""
        config = {
            # No config_version field
            "system": {"has_ev_charger": True},
            "battery": {"capacity_kwh": 13.5, "max_charge_a": 100, "max_discharge_a": 100},
            "water_heating": {
                "power_kw": 3.0,
                "min_kwh_per_day": 6.0,
                "comfort_level": 3,
                "enable_top_ups": True,
                "max_hours_between_heating": 8.0,
                "min_spacing_hours": 5.0,
            },
            "ev_charger": {
                "max_power_kw": 11.0,
                "battery_capacity_kwh": 82.0,
            },
        }

        kepler_cfg = config_to_kepler_config(config)

        # Should use legacy values
        assert kepler_cfg.water_heating_power_kw == 3.0
        assert kepler_cfg.ev_max_power_kw == 11.0
        assert kepler_cfg.ev_charging_enabled is True


class TestKeplerInputConversion:
    """Test planner_to_kepler_input function."""

    def test_converts_dataframe_to_kepler_input(self):
        """Should convert DataFrame with required columns to KeplerInput."""
        tz = pytz.UTC
        df = pd.DataFrame(
            {
                "load_forecast_kwh": [1.0, 2.0, 3.0],
                "pv_forecast_kwh": [0.5, 1.0, 1.5],
                "import_price_sek_kwh": [0.5, 0.6, 0.7],
                "export_price_sek_kwh": [0.4, 0.5, 0.6],
            },
            index=pd.date_range("2024-01-01 00:00", periods=3, freq="15min", tz=tz),
        )

        result = planner_to_kepler_input(df, initial_soc_kwh=5.0)

        assert len(result.slots) == 3
        assert result.initial_soc_kwh == 5.0
        assert result.slots[0].load_kwh == 1.0
        assert result.slots[0].pv_kwh == 0.5
        assert result.slots[0].import_price_sek_kwh == 0.5

    def test_handles_missing_export_price(self):
        """Should use import price when export price is missing."""
        tz = pytz.UTC
        df = pd.DataFrame(
            {
                "load_forecast_kwh": [1.0],
                "pv_forecast_kwh": [0.5],
                "import_price_sek_kwh": [0.5],
                # No export_price_sek_kwh
            },
            index=pd.date_range("2024-01-01 00:00", periods=1, freq="15min", tz=tz),
        )

        result = planner_to_kepler_input(df, initial_soc_kwh=5.0)

        assert result.slots[0].export_price_sek_kwh == 0.5  # Should equal import price

    def test_prefers_adjusted_forecasts(self):
        """Should prefer adjusted_load_kwh and adjusted_pv_kwh if available."""
        tz = pytz.UTC
        df = pd.DataFrame(
            {
                "load_forecast_kwh": [1.0],
                "pv_forecast_kwh": [0.5],
                "adjusted_load_kwh": [0.8],  # Should use this
                "adjusted_pv_kwh": [0.6],  # Should use this
                "import_price_sek_kwh": [0.5],
            },
            index=pd.date_range("2024-01-01 00:00", periods=1, freq="15min", tz=tz),
        )

        result = planner_to_kepler_input(df, initial_soc_kwh=5.0)

        assert result.slots[0].load_kwh == 0.8  # adjusted value
        assert result.slots[0].pv_kwh == 0.6  # adjusted value
