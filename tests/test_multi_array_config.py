import logging

from backend.api.routers.config import _validate_config_for_save
from backend.config_migration import migrate_solar_arrays

# Mock logging to avoid clutter
logging.basicConfig(level=logging.INFO)


def test_migration():
    print("\n--- Testing Legacy Migration ---")
    config = {"system": {"solar_array": {"azimuth": 180, "tilt": 35, "kwp": 10.5}}}
    migrated_config, changed = migrate_solar_arrays(config)

    assert changed is True
    assert "solar_array" not in migrated_config["system"]
    assert "solar_arrays" in migrated_config["system"]
    assert len(migrated_config["system"]["solar_arrays"]) == 1
    assert migrated_config["system"]["solar_arrays"][0]["kwp"] == 10.5
    assert migrated_config["system"]["solar_arrays"][0]["name"] == "Main Array"
    print("✅ Legacy migration successful")


def assert_no_errors(issues, context=""):
    errors = [i for i in issues if i["severity"] == "error"]
    if errors:
        print(f"❌ Errors found in {context}:")
        for e in errors:
            print(f"  - {e['message']} ({e['guidance']})")
        raise AssertionError(f"Expected no errors in {context}")


def test_valid_configs():
    print("\n--- Testing Valid Configurations ---")

    # Base config with battery/water heater disabled to avoid side-effect errors
    base_config = {
        "system": {
            "has_solar": True,
            "has_battery": False,
            "has_water_heater": False,
            "solar_arrays": [],
        },
        "executor": {"enabled": False},
    }

    # Single array
    config_1 = base_config.copy()
    config_1["system"] = base_config["system"].copy()
    config_1["system"]["solar_arrays"] = [
        {"name": "South", "azimuth": 180, "tilt": 35, "kwp": 10.5}
    ]
    issues_1 = _validate_config_for_save(config_1)
    assert_no_errors(issues_1, "Single Array")
    print("✅ Single array valid")

    # Dual array
    config_2 = base_config.copy()
    config_2["system"] = base_config["system"].copy()
    config_2["system"]["solar_arrays"] = [
        {"name": "South", "azimuth": 180, "tilt": 35, "kwp": 10.5},
        {"name": "East", "azimuth": 90, "tilt": 35, "kwp": 5.0},
    ]
    issues_2 = _validate_config_for_save(config_2)
    assert_no_errors(issues_2, "Dual Array")
    print("✅ Dual array valid")

    # Max 6 arrays
    config_6 = base_config.copy()
    config_6["system"] = base_config["system"].copy()
    config_6["system"]["solar_arrays"] = [
        {"name": f"A{i}", "azimuth": 180, "tilt": 35, "kwp": 5.0} for i in range(6)
    ]
    issues_6 = _validate_config_for_save(config_6)
    assert_no_errors(issues_6, "Max (6) Arrays")
    print("✅ Maximum (6) arrays valid")


def test_invalid_configs():
    print("\n--- Testing Invalid Configurations ---")
    base_config = {
        "system": {
            "has_solar": True,
            "has_battery": False,
            "has_water_heater": False,
            "solar_arrays": [],
        },
        "executor": {"enabled": False},
    }

    # 0 arrays
    issues_0 = _validate_config_for_save(base_config)
    assert any(
        i["severity"] == "warning" and "no arrays configured" in i["message"] for i in issues_0
    )
    print("✅ 0 arrays caught (warning)")

    # 7 arrays
    config_7 = base_config.copy()
    config_7["system"] = base_config["system"].copy()
    config_7["system"]["solar_arrays"] = [
        {"name": f"A{i}", "azimuth": 180, "tilt": 35, "kwp": 5.0} for i in range(7)
    ]
    issues_7 = _validate_config_for_save(config_7)
    assert any(
        i["severity"] == "error" and "Too many solar arrays" in i["message"] for i in issues_7
    )
    print("✅ 7 arrays caught (error)")

    # Array > 50kWp
    config_big = base_config.copy()
    config_big["system"] = base_config["system"].copy()
    config_big["system"]["solar_arrays"] = [{"kwp": 51.0}]
    issues_big = _validate_config_for_save(config_big)
    assert any(
        i["severity"] == "error" and "exceeds max capacity (50kWp)" in i["message"]
        for i in issues_big
    )
    print("✅ Array > 50kWp caught (error)")

    # Total > 500kWp
    config_over_500 = base_config.copy()
    config_over_500["system"] = base_config["system"].copy()
    # 6 arrays of 90kWp = 540kWp. This stays within len <= 6 limit but exceeds total.
    config_over_500["system"]["solar_arrays"] = [{"kwp": 90.0} for _ in range(6)]
    issues_over_500 = _validate_config_for_save(config_over_500)
    assert any("Total PV capacity exceeds 500kWp" in i["message"] for i in issues_over_500)
    print("✅ Total > 500kWp caught (error)")

    # Invalid tilt
    config_tilt = base_config.copy()
    config_tilt["system"] = base_config["system"].copy()
    config_tilt["system"]["solar_arrays"] = [{"tilt": 95}]
    issues_tilt = _validate_config_for_save(config_tilt)
    assert any("tilt must be 0-90°" in i["message"] for i in issues_tilt)
    print("✅ Invalid tilt caught (error)")


if __name__ == "__main__":
    test_migration()
    test_valid_configs()
    test_invalid_configs()
    print("\n✨ All configuration tests passed!")
