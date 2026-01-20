import asyncio

from backend.learning.backfill import BackfillEngine


async def debug_sensors():
    engine = BackfillEngine()
    print(f"Config path: {engine.config_path}")
    print(f"Learning config: {engine.learning_config}")

    input_sensors = engine.config.get("input_sensors", {})
    print(f"Full input_sensors: {input_sensors}")
    print(f"Input sensors 'pv_power': {input_sensors.get('pv_power')}")
    print(f"Input sensors 'load_power': {input_sensors.get('load_power')}")

    raw_map = engine.learning_config.get("sensor_map")
    print(f"Initial raw_map: {raw_map}")

    if not raw_map:
        print("Auto-detecting sensors...")
        raw_map = {}
        mapping = {
            "pv_power": "pv",
            "load_power": "load",
            "battery_power": "battery",
            "grid_power": "grid",
            "grid_import_power": "import",
            "grid_export_power": "export",
            "water_power": "water",
            "battery_soc": "soc",
        }
        for config_key, canonical in mapping.items():
            entity_id = input_sensors.get(config_key)
            if entity_id:
                raw_map[entity_id] = canonical
                print(f"Mapped {config_key} ({entity_id}) -> {canonical}")

    print(f"Final raw_map: {raw_map}")


if __name__ == "__main__":
    asyncio.run(debug_sensors())
