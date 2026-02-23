import unittest
from datetime import datetime

import pytz

from backend.learning.engine import LearningEngine


class TestMLAggregation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Create a mock engine with default config
        self.engine = LearningEngine(config_path="config.default.yaml")
        self.engine.timezone = pytz.UTC
        self.engine.sensor_map = {"sensor.pv_total": "pv", "sensor.solar_yield": "pv"}

    def test_sensor_aggregation(self):
        print("\n--- Testing ML Sensor Aggregation ---")

        # 1. Setup mock sensors that both map to 'pv'
        # Sensor A: 10 kWh cumulative at t0, 12 kWh at t1 (+2 kWh)
        # Sensor B: 5 kWh cumulative at t0, 6 kWh at t1 (+1 kWh)
        # Total should be +3 kWh

        t0 = datetime(2024, 6, 21, 12, 0, tzinfo=pytz.UTC)
        t1 = datetime(2024, 6, 21, 12, 15, tzinfo=pytz.UTC)
        t2 = datetime(2024, 6, 21, 12, 30, tzinfo=pytz.UTC)

        cumulative_data = {
            "sensor.pv_total": [(t0, 10.0), (t1, 12.0), (t2, 15.0)],
            "sensor.solar_yield": [(t0, 5.0), (t1, 6.0), (t2, 8.0)],
        }

        # 2. Run ETL
        slot_df = self.engine.etl_cumulative_to_slots(cumulative_data, resolution_minutes=15)

        # 3. Verify aggregation
        # Slot 1: (t1-t0) Sensor 1=2.0, Sensor 2=1.0 -> Total 3.0
        # Slot 2: (t2-t1) Sensor 1=3.0, Sensor 2=2.0 -> Total 5.0

        self.assertEqual(len(slot_df), 2)
        self.assertEqual(slot_df.iloc[0]["pv_kwh"], 3.0)
        self.assertEqual(slot_df.iloc[1]["pv_kwh"], 5.0)

        print(f"✅ Slot 1 PV: {slot_df.iloc[0]['pv_kwh']} kWh (Expected 3.0)")
        print(f"✅ Slot 2 PV: {slot_df.iloc[1]['pv_kwh']} kWh (Expected 5.0)")
        print("✅ Sensor aggregation in learning engine verified!")


if __name__ == "__main__":
    unittest.main()
