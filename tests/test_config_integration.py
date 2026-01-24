"""
Config Integration Test
=======================
Verifies that config.default.yaml values are correctly mapped
to KeplerConfig via the adapter.
"""

from pathlib import Path

import pytest
import yaml

from planner.solver.adapter import config_to_kepler_config


@pytest.fixture
def default_config():
    """Load the default config YAML."""
    config_path = Path(__file__).parent.parent / "config.default.yaml"
    with config_path.open() as f:
        return yaml.safe_load(f)


def test_config_mapping(default_config):
    """Test that all exposed keys in config.default.yaml map to KeplerConfig correctly."""
    raw_config = default_config

    # Create dummy slots/overrides
    k_config = config_to_kepler_config(raw_config)

    # 1. Target SoC Penalty
    assert k_config.target_soc_penalty_sek == raw_config["kepler"]["target_soc_penalty_sek"]

    # 2. Curtailment Penalty
    assert k_config.curtailment_penalty_sek == raw_config["kepler"]["curtailment_penalty_sek"]

    # 3. Water Reliability Penalty
    assert (
        k_config.water_reliability_penalty_sek
        == raw_config["water_heating"]["reliability_penalty_sek"]
    )

    # 4. Water Block Penalty
    assert k_config.water_block_penalty_sek == raw_config["water_heating"]["block_penalty_sek"]

    # 5. Wear Cost
    # Note: Adapter looks at battery_economics first
    assert (
        k_config.wear_cost_sek_per_kwh == raw_config["battery_economics"]["battery_cycle_cost_kwh"]
    )

    # 6. Basic Battery Parameters
    assert k_config.min_soc_percent == raw_config["battery"]["min_soc_percent"]
    assert k_config.max_soc_percent == raw_config["battery"]["max_soc_percent"]
    assert k_config.charge_efficiency == raw_config["battery"]["charge_efficiency"]

    # 7. Water Block Start Penalty
    assert (
        k_config.water_block_start_penalty_sek
        == raw_config["water_heating"]["block_start_penalty_sek"]
    )

    # 8. Defer Hours
    assert k_config.defer_up_to_hours == raw_config["water_heating"]["defer_up_to_hours"]

    # 9. Ramping Cost
    assert k_config.ramping_cost_sek_per_kw == raw_config["kepler"]["ramping_cost_sek_per_kw"]
