"""Tests for ML corrector spike filtering."""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytz

from backend.learning import LearningEngine
from ml.corrector import (  # type: ignore[reportPrivateUsage]
    _compute_stats_bias,
    _load_training_frame,
)


def test_load_training_frame_filters_spikes():
    """Verify that _load_training_frame filters out spike values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        config = {
            "system": {"grid": {"max_power_kw": 10.0}},
            "timezone": "Europe/Stockholm",
        }

        engine = LearningEngine.__new__(LearningEngine)
        engine.db_path = str(db_path)
        engine.config = config
        engine.timezone = pytz.timezone("Europe/Stockholm")

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE slot_observations (
                    slot_start TEXT PRIMARY KEY,
                    load_kwh REAL,
                    pv_kwh REAL
                )
            """)
            conn.execute("""
                CREATE TABLE slot_forecasts (
                    slot_start TEXT,
                    forecast_version TEXT,
                    load_forecast_kwh REAL,
                    pv_forecast_kwh REAL,
                    PRIMARY KEY (slot_start, forecast_version)
                )
            """)

            tz = pytz.timezone("Europe/Stockholm")
            base_time = tz.localize(datetime(2024, 6, 21, 12, 0))

            test_data = [
                (base_time, 1.5, 2.0, 1.4, 2.1),
                (base_time + timedelta(minutes=15), 100.0, 2.0, 1.5, 2.0),
                (base_time + timedelta(minutes=30), 1.5, 100.0, 1.6, 2.1),
            ]

            for _i, (slot_start, load_kwh, pv_kwh, load_f, pv_f) in enumerate(test_data):
                conn.execute(
                    "INSERT INTO slot_observations VALUES (?, ?, ?)",
                    (slot_start.isoformat(), load_kwh, pv_kwh),
                )
                conn.execute(
                    "INSERT INTO slot_forecasts VALUES (?, ?, ?, ?)",
                    (slot_start.isoformat(), "aurora", load_f, pv_f),
                )
            conn.commit()

        df = _load_training_frame(engine, days_back=30)

        max_kwh = 10.0 * 0.25 * 2.0
        assert all(df["load_kwh"] <= max_kwh)
        assert all(df["pv_kwh"] <= max_kwh)


def test_compute_stats_bias_filters_spikes():
    """Verify that _compute_stats_bias filters out spike values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        config = {
            "system": {"grid": {"max_power_kw": 10.0}},
            "timezone": "Europe/Stockholm",
        }

        engine = LearningEngine.__new__(LearningEngine)
        engine.db_path = str(db_path)
        engine.config = config
        engine.timezone = pytz.timezone("Europe/Stockholm")

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE slot_observations (
                    slot_start TEXT PRIMARY KEY,
                    load_kwh REAL,
                    pv_kwh REAL
                )
            """)
            conn.execute("""
                CREATE TABLE slot_forecasts (
                    slot_start TEXT,
                    forecast_version TEXT,
                    load_forecast_kwh REAL,
                    pv_forecast_kwh REAL,
                    PRIMARY KEY (slot_start, forecast_version)
                )
            """)

            tz = pytz.timezone("Europe/Stockholm")
            base_time = tz.localize(datetime(2024, 6, 21, 12, 0))

            for i in range(10):
                slot_start = base_time + timedelta(minutes=15 * i)
                load_kwh = 100.0 if i == 5 else 1.5
                pv_kwh = 100.0 if i == 7 else 2.0

                conn.execute(
                    "INSERT INTO slot_observations VALUES (?, ?, ?)",
                    (slot_start.isoformat(), load_kwh, pv_kwh),
                )
                conn.execute(
                    "INSERT INTO slot_forecasts VALUES (?, ?, ?, ?)",
                    (slot_start.isoformat(), "aurora", 1.4, 2.1),
                )
            conn.commit()

        stats = _compute_stats_bias(engine, days_back=30)

        max_kwh = 10.0 * 0.25 * 2.0
        for (_dow, _hour), (pv_bias, load_bias) in stats.items():
            assert abs(pv_bias) < max_kwh
            assert abs(load_bias) < max_kwh
