import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add root to sys.path to import inputs
sys.path.append(str(Path.cwd()))

from inputs import get_ha_sensor_kw_normalized


@pytest.mark.asyncio
async def test_get_ha_sensor_kw_normalized():
    # Mock data for W
    mock_w = {"state": "1500", "attributes": {"unit_of_measurement": "W"}}
    # Mock data for kW
    mock_kw = {"state": "1.5", "attributes": {"unit_of_measurement": "kW"}}
    # Mock data for no units
    mock_none = {"state": "2.5", "attributes": {}}

    with patch("inputs.get_ha_entity_state") as mock_get:
        # Test W normalization
        mock_get.return_value = mock_w
        val = await get_ha_sensor_kw_normalized("any")
        assert val == 1.5

        # Test kW preservation
        mock_get.return_value = mock_kw
        val = await get_ha_sensor_kw_normalized("any")
        assert val == 1.5

        # Test no unit preservation
        mock_get.return_value = mock_none
        val = await get_ha_sensor_kw_normalized("any")
        assert val == 2.5

        # Test error handling
        mock_get.return_value = {"state": "invalid"}
        val = await get_ha_sensor_kw_normalized("any")
        assert val is None

        mock_get.return_value = None
        val = await get_ha_sensor_kw_normalized("any")
        assert val is None


if __name__ == "__main__":
    try:
        asyncio.run(test_get_ha_sensor_kw_normalized())
        print("Unit test passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
