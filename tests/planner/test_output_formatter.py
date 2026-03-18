"""
Tests for planner output formatter - per-device EV charger data in schedule output.
"""

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from planner.output.formatter import dataframe_to_json_response


def _make_schedule_df(ev_chargers_col=None):
    """Build a minimal schedule DataFrame with optional ev_chargers column."""
    now = datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
    times = pd.date_range(now, periods=3, freq="1h", tz="UTC")
    df = pd.DataFrame(
        {
            "start_time": times,
            "end_time": times + pd.Timedelta(hours=1),
            "battery_charge_kw": [0.0, 1.0, 0.0],
            "battery_discharge_kw": [0.0, 0.0, 2.0],
            "ev_charge_kw": [3.0, 0.0, 0.0],
            "grid_import_kw": [0.0, 1.0, 0.0],
            "grid_export_kw": [0.0, 0.0, 0.0],
            "pv_kw": [5.0, 4.0, 3.0],
            "water_heater_kw": [0.0, 0.0, 0.0],
            "import_price_sek_kwh": [0.5, 0.5, 0.5],
            "export_price_sek_kwh": [0.1, 0.1, 0.1],
        }
    )
    if ev_chargers_col is not None:
        df["ev_chargers"] = ev_chargers_col
    return df


class TestEvChargersInOutput:
    def test_per_device_breakdown_present(self):
        """Each slot should include ev_chargers dict with per-device kW."""
        ev_data = [
            {"charger_a": 3.0, "charger_b": 0.0},
            {"charger_a": 0.0, "charger_b": 0.0},
            {"charger_a": 0.0, "charger_b": 0.0},
        ]
        df = _make_schedule_df(ev_chargers_col=ev_data)
        records = dataframe_to_json_response(
            df, now_override=datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        )

        assert len(records) == 3
        assert records[0]["ev_chargers"] == {"charger_a": 3.0, "charger_b": 0.0}
        assert records[1]["ev_chargers"] == {"charger_a": 0.0, "charger_b": 0.0}

    def test_nan_ev_chargers_normalised_to_empty_dict(self):
        """NaN in ev_chargers column (non-solver rows) must become {}."""
        df = _make_schedule_df(ev_chargers_col=[float("nan"), None, float("nan")])
        records = dataframe_to_json_response(
            df, now_override=datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        )

        for record in records:
            assert record["ev_chargers"] == {}

    def test_missing_ev_chargers_column_produces_empty_dict(self):
        """When ev_chargers column is absent, output should still include {} per slot."""
        df = _make_schedule_df()
        records = dataframe_to_json_response(
            df, now_override=datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        )

        for record in records:
            assert record["ev_chargers"] == {}

    def test_aggregate_ev_charge_kw_preserved(self):
        """ev_charge_kw aggregate should still be present alongside ev_chargers."""
        ev_data = [{"charger_a": 3.0}, {"charger_a": 0.0}, {"charger_a": 0.0}]
        df = _make_schedule_df(ev_chargers_col=ev_data)
        records = dataframe_to_json_response(
            df, now_override=datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        )

        assert records[0]["ev_charge_kw"] == 3.0
        assert "ev_chargers" in records[0]

    def test_numpy_nan_in_ev_chargers_normalised(self):
        """numpy.nan values in ev_chargers column are also normalised to {}."""
        df = _make_schedule_df(ev_chargers_col=[np.nan, np.nan, np.nan])
        records = dataframe_to_json_response(
            df, now_override=datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        )

        for record in records:
            assert record["ev_chargers"] == {}

    def test_mixed_ev_chargers_column(self):
        """Mixed dict/NaN column: dicts pass through, NaN becomes {}."""
        ev_data = [{"charger_a": 2.5}, float("nan"), {"charger_a": 0.0}]
        df = _make_schedule_df(ev_chargers_col=ev_data)
        records = dataframe_to_json_response(
            df, now_override=datetime(2024, 6, 1, 10, 0, tzinfo=UTC)
        )

        assert records[0]["ev_chargers"] == {"charger_a": 2.5}
        assert records[1]["ev_chargers"] == {}
        assert records[2]["ev_chargers"] == {"charger_a": 0.0}
