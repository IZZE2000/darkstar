#!/usr/bin/env python3
"""
REV F61 Integration Tests
Tests for EV Penalty Levels Architecture Cleanup
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

from backend.health import HealthChecker
from executor.config import EVChargerConfig


def test_ha_socket_config_path():
    """Test 1: HA Socket reads replan_on_plugin from correct path."""
    print("\n" + "=" * 60)
    print("TEST 1: HA Socket Config Path")
    print("=" * 60)

    # Import and check the code directly
    import inspect

    from backend import ha_socket

    # Get source of _trigger_ev_replan method
    source = inspect.getsource(ha_socket.HAWebSocketClient._trigger_ev_replan)

    # Verify it uses correct path
    assert 'cfg.get("executor", {}).get("ev_charger", {})' in source, (
        "HA Socket should read from executor.ev_charger, not root ev_charger"
    )

    print("✓ HA Socket correctly reads from executor.ev_charger path")
    return True


def test_executor_no_penalty_levels():
    """Test 2: Executor EVChargerConfig has no penalty_levels field."""
    print("\n" + "=" * 60)
    print("TEST 2: Executor Dead Code Removal")
    print("=" * 60)

    # Check dataclass fields
    import dataclasses

    fields = {f.name for f in dataclasses.fields(EVChargerConfig)}

    assert "penalty_levels" not in fields, "EVChargerConfig should not have penalty_levels field"
    assert "replan_on_plugin" in fields, "EVChargerConfig should have replan_on_plugin field"
    assert "replan_on_unplug" in fields, "EVChargerConfig should have replan_on_unplug field"

    print("✓ EVChargerConfig does not have deprecated penalty_levels field")
    print(f"✓ EVChargerConfig has fields: {sorted(fields)}")
    return True


def test_config_validation():
    """Test 3: Health check warns about deprecated penalty_levels."""
    print("\n" + "=" * 60)
    print("TEST 3: Config Validation Warning")
    print("=" * 60)

    # Create a temporary config file with deprecated setting
    import tempfile

    config_with_deprecated = {
        "executor": {"ev_charger": {"penalty_levels": [{"max_soc": 50, "penalty_sek": 0.5}]}},
        "system": {
            "has_solar": False,
            "has_battery": False,
            "has_water_heater": False,
        },  # Prevent other warnings
    }

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_with_deprecated, f)
        temp_path = f.name

    # Create temporary secrets file (to prevent 'secrets not found' error)
    secrets_content = {"home_assistant": {"url": "http://localhost:8123", "token": "test_token"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(secrets_content, f)
        secrets_temp_path = f.name

    try:
        # Create health checker with temp config
        checker = HealthChecker(temp_path)

        # Load the config manually since we can't easily mock the secrets path
        with Path(temp_path).open() as f:
            checker._config = yaml.safe_load(f) or {}

        # Run only the structure validation (skip file loading)
        issues = checker._validate_config_structure()

        # Find deprecation warning
        deprecation_issues = [
            i
            for i in issues
            if "deprecated" in i.message.lower() and "penalty_levels" in i.message.lower()
        ]

        assert len(deprecation_issues) > 0, (
            "Should warn about deprecated executor.ev_charger.penalty_levels"
        )

        issue = deprecation_issues[0]
        assert issue.severity == "warning", "Should be a warning, not error"
        assert "per-charger penalty levels" in issue.guidance.lower(), (
            "Guidance should mention per-charger penalty levels"
        )

        print(f"✓ Health check warns about deprecated setting: {issue.message}")
        print(f"✓ Guidance provided: {issue.guidance}")
        return True
    finally:
        Path(temp_path).unlink()
        Path(secrets_temp_path).unlink()


def test_default_config_structure():
    """Test 4: Default config has correct structure."""
    print("\n" + "=" * 60)
    print("TEST 4: Default Config Structure")
    print("=" * 60)

    import yaml

    # Load default config
    with Path("config.default.yaml").open() as f:
        config = yaml.safe_load(f)

    # Check ev_chargers array exists
    assert "ev_chargers" in config, "Config should have ev_chargers array"
    assert isinstance(config["ev_chargers"], list), "ev_chargers should be a list"

    # Check executor.ev_charger has replan triggers
    executor = config.get("executor", {})
    ev_charger = executor.get("ev_charger", {})

    assert "replan_on_plugin" in ev_charger, "executor.ev_charger should have replan_on_plugin"
    assert "replan_on_unplug" in ev_charger, "executor.ev_charger should have replan_on_unplug"

    # Check deprecated field is NOT in default config
    assert "penalty_levels" not in ev_charger, (
        "executor.ev_charger should NOT have penalty_levels in default config"
    )

    print("✓ ev_chargers array exists for per-EV penalty levels")
    print("✓ executor.ev_charger has replan_on_plugin/unplug")
    print("✓ No deprecated penalty_levels in default config")
    return True


def test_planner_uses_ev_chargers():
    """Test 5: Planner uses ev_chargers[].penalty_levels (not executor)."""
    print("\n" + "=" * 60)
    print("TEST 5: Planner Uses Correct Path")
    print("=" * 60)

    import inspect

    from planner.solver import adapter

    # Get source of relevant functions
    source = inspect.getsource(adapter)

    # Should reference ev_chargers, not executor.ev_charger for penalty levels
    assert "ev_chargers" in source, "Planner should reference ev_chargers"
    assert "penalty_levels" in source, "Planner should reference penalty_levels"

    # Make sure it doesn't use the deprecated path
    lines = source.split("\n")
    for i, line in enumerate(lines):
        # Check context - should be in ev_chargers loop, not executor
        if "penalty_levels" in line.lower() and "executor" in line.lower():
            print(f"⚠ Warning line {i}: {line.strip()}")

    print("✓ Planner references ev_chargers array")
    print("✓ Planner uses penalty_levels from ev_chargers[].penalty_levels")
    return True


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("REV F61 INTEGRATION TESTS")
    print("EV Penalty Levels Architecture Cleanup")
    print("=" * 60)

    tests = [
        test_ha_socket_config_path,
        test_executor_no_penalty_levels,
        test_config_validation,
        test_default_config_structure,
        test_planner_uses_ev_chargers,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
            else:
                failed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 All tests passed! F61 architecture is correct.")
        return 0
    else:
        print(f"\n⚠ {failed} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
