from datetime import datetime, timedelta

import pytest
import pytz

from backend.learning.engine import LearningEngine


@pytest.fixture
def engine(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
timezone: "Europe/Stockholm"
learning:
  sqlite_path: ":memory:"
input_sensors:
  pv_power: "sensor.pv"
  load_power: "sensor.load"
""")
    return LearningEngine(str(config_file))


def test_etl_power_units_watts(engine):
    tz = pytz.timezone("Europe/Stockholm")
    start = datetime(2026, 1, 20, 12, 0, tzinfo=tz)

    # 5000W constant over 15 mins = 1.25 kWh
    power_data = {
        "sensor.pv": [
            (start, 5000.0),
            (start + timedelta(minutes=5), 5000.0),
            (start + timedelta(minutes=10), 5000.0),
            (start + timedelta(minutes=15), 5000.0),
        ]
    }

    df = engine.etl_power_to_slots(power_data, resolution_minutes=15)
    assert not df.empty
    # The first slot is 12:00 to 12:15
    assert df.iloc[0]["pv_kwh"] == pytest.approx(1.25)


def test_etl_power_units_kw(engine):
    tz = pytz.timezone("Europe/Stockholm")
    start = datetime(2026, 1, 20, 12, 0, tzinfo=tz)

    # 5.0 kW constant over 15 mins = 1.25 kWh
    power_data = {
        "sensor.pv": [
            (start, 5.0),
            (start + timedelta(minutes=5), 5.0),
            (start + timedelta(minutes=10), 5.0),
            (start + timedelta(minutes=15), 5.0),
        ]
    }

    df = engine.etl_power_to_slots(power_data, resolution_minutes=15)
    assert not df.empty
    # The first slot is 12:00 to 12:15
    # If detected as kW: 5.0 * 0.25 = 1.25
    assert df.iloc[0]["pv_kwh"] == pytest.approx(1.25)


def test_etl_power_units_mixed(engine):
    tz = pytz.timezone("Europe/Stockholm")
    start = datetime(2026, 1, 20, 12, 0, tzinfo=tz)

    # Mixed data:
    # Sensor 1 (PV) in Watts
    # Sensor 2 (Load) in kW
    power_data = {
        "sensor.pv": [
            (start, 4000.0),
            (start + timedelta(minutes=15), 4000.0),
        ],
        "sensor.load": [
            (start, 2.0),
            (start + timedelta(minutes=15), 2.0),
        ],
    }

    df = engine.etl_power_to_slots(power_data, resolution_minutes=15)
    assert not df.empty
    assert df.iloc[0]["pv_kwh"] == pytest.approx(1.0)  # 4000/1000 * 0.25
    assert df.iloc[0]["load_kwh"] == pytest.approx(0.5)  # 2.0 * 0.25
