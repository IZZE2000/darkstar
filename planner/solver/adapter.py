"""
Kepler Adapter Module

Convert between Planner DataFrame format and Kepler solver types.
Migrated from backend/kepler/adapter.py during Rev K13 modularization.
"""

from datetime import datetime  # noqa: TC003
from typing import Any

import pandas as pd

from .types import IncentiveBucket, KeplerConfig, KeplerInput, KeplerInputSlot, KeplerResult


def _get_config_version(config: dict[str, Any]) -> int:
    """Detect config format version for ARC15 migration compatibility."""
    return int(config.get("config_version", 1))


def _aggregate_water_heaters(
    water_heaters: list[dict[str, Any]], legacy_wh: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Aggregate multiple water heaters into single KeplerConfig parameters.
    ARC15: Sum power ratings, use legacy water_heating or first heater for comfort settings.

    Args:
        water_heaters: List of water heater configs from new structure
        legacy_wh: Legacy water_heating section for fallback comfort settings
    """
    enabled_wh: list[dict[str, Any]] = [wh for wh in water_heaters if wh.get("enabled", True)]

    if not enabled_wh:
        return {
            "power_kw": 0.0,
            "min_kwh_per_day": 0.0,
            "comfort_level": 3,
            "enable_top_ups": True,
            "max_hours_between_heating": 8.0,
            "min_spacing_hours": 5.0,
            "defer_up_to_hours": 0.0,
        }

    # Sum power ratings and daily requirements
    total_power = sum(float(wh.get("power_kw", 0.0)) for wh in enabled_wh)
    total_min_kwh = sum(float(wh.get("min_kwh_per_day", 0.0)) for wh in enabled_wh)

    # Use first enabled heater's timing settings (device-specific)
    first_wh: dict[str, Any] = enabled_wh[0]

    # Comfort settings: use legacy water_heating section if available, otherwise heater's values
    # The water_heaters array has 'water_min_spacing_hours' not 'min_spacing_hours'
    spacing_hours: Any = first_wh.get("water_min_spacing_hours") or first_wh.get(
        "min_spacing_hours"
    )

    if legacy_wh:
        # Use legacy section for comfort settings (global user preferences)
        return {
            "power_kw": total_power,
            "min_kwh_per_day": total_min_kwh,
            "comfort_level": int(legacy_wh.get("comfort_level", 3)),
            "enable_top_ups": bool(legacy_wh.get("enable_top_ups", True)),
            "max_hours_between_heating": float(first_wh.get("max_hours_between_heating", 8.0)),
            "min_spacing_hours": float(spacing_hours or legacy_wh.get("min_spacing_hours", 5.0)),
            "defer_up_to_hours": float(legacy_wh.get("defer_up_to_hours", 0.0)),
        }
    else:
        # No legacy section - use defaults
        return {
            "power_kw": total_power,
            "min_kwh_per_day": total_min_kwh,
            "comfort_level": int(first_wh.get("comfort_level", 3)),
            "enable_top_ups": bool(first_wh.get("enable_top_ups", True)),
            "max_hours_between_heating": float(first_wh.get("max_hours_between_heating", 8.0)),
            "min_spacing_hours": float(spacing_hours or 5.0),
            "defer_up_to_hours": float(first_wh.get("defer_up_to_hours", 0.0)),
        }


def _aggregate_ev_chargers(ev_chargers: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate multiple EV chargers into single KeplerConfig parameters.
    ARC15: Sum max power, use largest battery capacity, merge incentive buckets.
    """
    enabled_ev: list[dict[str, Any]] = [ev for ev in ev_chargers if ev.get("enabled", True)]

    if not enabled_ev:
        return {
            "max_power_kw": 0.0,
            "battery_capacity_kwh": 0.0,
            "penalty_levels": [],
        }

    # Sum max charging power
    total_max_power = sum(float(ev.get("max_power_kw", 0.0)) for ev in enabled_ev)

    # Use largest battery capacity (conservative approach)
    max_battery_capacity = max(float(ev.get("battery_capacity_kwh", 0.0)) for ev in enabled_ev)

    # Merge incentive buckets from all EVs (take the most conservative penalties)
    all_buckets: list[dict[str, Any]] = []
    for ev in enabled_ev:
        levels: list[dict[str, Any]] = ev.get("penalty_levels", [])
        if levels:
            all_buckets.extend(levels)

    # If multiple EVs have penalty levels, merge by taking max penalty at each threshold
    merged_buckets: list[dict[str, Any]] = []
    if all_buckets:
        # Group by threshold SoC and take highest penalty
        threshold_map: dict[float, float] = {}
        for bucket in all_buckets:
            if "max_soc" in bucket:
                threshold = float(bucket["max_soc"])
                penalty = float(bucket.get("penalty_sek", 0.0))
                threshold_map[threshold] = max(threshold_map.get(threshold, 0.0), penalty)

        # Sort by threshold and create merged buckets
        for threshold in sorted(threshold_map.keys()):
            merged_buckets.append(
                {
                    "max_soc": threshold,
                    "penalty_sek": threshold_map[threshold],
                }
            )

    return {
        "max_power_kw": total_max_power,
        "battery_capacity_kwh": max_battery_capacity,
        "penalty_levels": merged_buckets,
    }


def planner_to_kepler_input(df: pd.DataFrame, initial_soc_kwh: float) -> KeplerInput:
    """
    Convert Planner DataFrame to KeplerInput.
    Expects DataFrame index to be timestamps (start_time).
    """
    slots: list[KeplerInputSlot] = []

    # Ensure required columns exist
    required_cols = ["load_forecast_kwh", "pv_forecast_kwh", "import_price_sek_kwh"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0.0

    if "export_price_sek_kwh" not in df.columns:
        df["export_price_sek_kwh"] = df["import_price_sek_kwh"]

    for idx, row in df.iterrows():
        start_time: datetime = idx  # type: ignore[assignment]
        if "end_time" in df.columns:
            end_time: datetime = row["end_time"]  # type: ignore[assignment]
        else:
            end_time = start_time + pd.Timedelta(minutes=15)

        # Prefer adjusted forecasts if available (already represents Base Load)
        load = float(row.get("adjusted_load_kwh", row.get("load_forecast_kwh", 0.0)))
        pv = float(row.get("adjusted_pv_kwh", row.get("pv_forecast_kwh", 0.0)))

        slots.append(
            KeplerInputSlot(
                start_time=start_time,
                end_time=end_time,
                load_kwh=load,
                pv_kwh=pv,
                import_price_sek_kwh=float(row["import_price_sek_kwh"]),
                export_price_sek_kwh=float(row["export_price_sek_kwh"]),
            )
        )

    return KeplerInput(slots=slots, initial_soc_kwh=initial_soc_kwh)  # type: ignore[arg-type]


def _comfort_level_to_penalty(
    comfort_level: int, daily_kwh: float = 0.0, heater_power_kw: float = 0.0
) -> dict[str, float]:
    """Map comfort level (1-5) to penalty configuration and dynamic window size.

    Level 1: Economy - comfort is nice-to-have, large windows for bulk heating
    Level 5: Maximum - almost hard constraint, small windows for frequent heating

    Args:
        comfort_level: 1-5 comfort level
        daily_kwh: Daily water heating requirement
        heater_power_kw: Water heater power rating
    """
    # Comfort multipliers for window sizing
    COMFORT_MULTIPLIERS = {
        1: 1.5,  # Economy: Larger windows = bulk heating in cheapest period
        2: 1.0,  # Balanced: Moderate windows
        3: 0.8,  # Neutral: Slight spacing preference
        4: 0.5,  # Priority: More frequent heating
        5: 0.25,  # Maximum: Very frequent = stable temperature
    }

    # Calculate dynamic window size
    if daily_kwh > 0 and heater_power_kw > 0:
        min_heating_hours = daily_kwh / heater_power_kw
        multiplier = COMFORT_MULTIPLIERS.get(comfort_level, 0.8)
        max_block_hours = min_heating_hours * multiplier
    else:
        # Fallback to current behavior if parameters missing
        max_block_hours = 2.0

    # Penalty parameters explained:
    # - water_reliability_penalty_sek: Applied ONCE PER DAY when daily minimum (min_kwh_per_day) is not met.
    #   Higher values = stricter enforcement of daily heating requirement.
    #   Example: 300 SEK = 300 SEK total penalty if day fails to meet minimum.
    # - water_block_start_penalty_sek: Applied ONCE PER HEATING BLOCK when a new heating session starts.
    #   Higher values = preference for fewer, longer blocks vs many short blocks.
    #   Example: 1.5 SEK = 1.5 SEK penalty for each heating block created.
    # - water_block_penalty_sek: Applied PER SLOT when heating block exceeds max_block_hours.
    #   Higher values = stricter enforcement of window size limits.
    #   Example: 10 SEK = 10 SEK penalty for each 15-minute slot that overshoots the window.
    # - max_block_hours: Maximum duration for a single heating block (calculated dynamically).
    #   Smaller values = more frequent heating = more stable temperature.

    COMFORT_MAP = {
        # Level: {reliability, block_start, block, max_block_hours}
        1: {
            "water_reliability_penalty_sek": 2.0,
            "water_block_start_penalty_sek": 1.5,
            "water_block_penalty_sek": 0.5,
            "max_block_hours": max_block_hours,
        },  # Economy
        2: {
            "water_reliability_penalty_sek": 7.0,
            "water_block_start_penalty_sek": 2.25,
            "water_block_penalty_sek": 1.0,
            "max_block_hours": max_block_hours,
        },  # Balanced
        3: {
            "water_reliability_penalty_sek": 15.0,
            "water_block_start_penalty_sek": 3.0,
            "water_block_penalty_sek": 2.0,
            "max_block_hours": max_block_hours,
        },  # Neutral
        4: {
            "water_reliability_penalty_sek": 30.0,
            "water_block_start_penalty_sek": 4.5,
            "water_block_penalty_sek": 5.0,
            "max_block_hours": max_block_hours,
        },  # Priority
        5: {
            "water_reliability_penalty_sek": 300.0,
            "water_block_start_penalty_sek": 1.0,
            "water_block_penalty_sek": 10.0,
            "max_block_hours": max_block_hours,
        },  # Maximum
    }
    # Default to Level 3 (Neutral) if invalid
    params = COMFORT_MAP.get(comfort_level, COMFORT_MAP[3]).copy()
    # Explicitly disable legacy gap penalty
    params["water_comfort_penalty_sek"] = 0.0
    return params


def _apply_bulk_mode_override(params: dict[str, float]) -> dict[str, float]:
    """Apply bulk heating mode override - forces single block behavior.

    Overrides ONLY block-related parameters while preserving reliability penalties.
    This allows users to request bulk heating (single block) while maintaining
    their chosen reliability level (e.g., Level 5 + bulk mode = strict reliability
    but consolidated heating).

    Args:
        params: Penalty parameters from comfort level

    Returns:
        Modified parameters with bulk mode overrides
    """
    params["max_block_hours"] = 24.0  # Allow entire day as one block
    params["water_block_penalty_sek"] = 0.0  # No penalty for long blocks
    # Keep water_reliability_penalty_sek and water_block_start_penalty_sek unchanged
    return params


def config_to_kepler_config(
    planner_config: dict[str, Any],
    overrides: dict[str, Any] | None = None,
    slots: list[Any] | None = None,
    force_water_on_slots: list[int] | None = None,
) -> KeplerConfig:
    """
    Convert the main config dictionary to KeplerConfig.

    Args:
        planner_config: Main configuration dictionary
        overrides: Optional runtime overrides
        slots: Optional list of KeplerInputSlot (Legacy argument, currently unused)
    """
    system = planner_config.get("system", {})
    battery = system.get("battery", planner_config.get("battery", {}))

    kepler_overrides: dict[str, Any] = {}
    if overrides and "kepler" in overrides:
        kepler_overrides = overrides["kepler"]

    def get_val(key: str, default: float) -> float:
        # Check runtime overrides first, then config file, then default
        # Check kepler_overrides (legacy support)
        if key in kepler_overrides:
            return float(kepler_overrides[key])

        val = planner_config.get(key)
        # Check overrides (standard)
        if overrides and key in overrides:
            val = overrides[key]
        return float(val) if val is not None else default

    # ARC15: Detect config format and load water heating settings
    config_version = _get_config_version(planner_config)
    water_heaters = planner_config.get("water_heaters", [])
    ev_chargers = planner_config.get("ev_chargers", [])
    legacy_wh = planner_config.get("water_heating", {})

    if config_version >= 2 and water_heaters:
        # Use new entity-centric structure (aggregate multiple heaters)
        # Pass legacy section for comfort settings fallback
        wh_cfg = _aggregate_water_heaters(water_heaters, legacy_wh)
    else:
        # Fallback to legacy format
        wh_cfg = legacy_wh

    # ARC15: Load EV charging settings
    if config_version >= 2 and ev_chargers:
        # Use new entity-centric structure (aggregate multiple chargers)
        ev_cfg = _aggregate_ev_chargers(ev_chargers)
        ev_enabled = any(ev.get("enabled", True) for ev in ev_chargers)
    else:
        # Fallback to legacy format
        ev_cfg = planner_config.get("ev_charger", {})
        ev_enabled = system.get("has_ev_charger", False)

    capacity = float(battery.get("capacity_kwh", 13.5))
    charge_eff = float(battery.get("charge_efficiency", 0.95))
    discharge_eff = float(battery.get("discharge_efficiency", 0.95))

    # Dynamic Power Limits (Rev F17)
    # Hardware limits (Amps or Watts) drive the Optimizer limits (kW)
    inverter_cfg = planner_config.get("executor", {}).get("inverter", {})
    control_unit = inverter_cfg.get("control_unit", "A")

    if control_unit == "W":
        max_charge_kw = float(battery.get("max_charge_w", 0.0)) / 1000.0
        max_discharge_kw = float(battery.get("max_discharge_w", 0.0)) / 1000.0
        print(
            f"[DEBUG] W mode: battery.max_charge_w={battery.get('max_charge_w')} -> {max_charge_kw} kW"
        )
        print(
            f"[DEBUG] W mode: battery.max_discharge_w={battery.get('max_discharge_w')} -> {max_discharge_kw} kW"
        )
    else:
        # Amps mode - use nominal voltage for planning
        voltage = float(battery.get("nominal_voltage_v", battery.get("system_voltage_v", 48.0)))
        max_charge_kw = (float(battery.get("max_charge_a", 0.0)) * voltage) / 1000.0
        max_discharge_kw = (float(battery.get("max_discharge_a", 0.0)) * voltage) / 1000.0
        print(
            f"[DEBUG] A mode: battery.max_charge_a={battery.get('max_charge_a')}, voltage={voltage} -> {max_charge_kw} kW"
        )
        print(
            f"[DEBUG] A mode: battery.max_discharge_a={battery.get('max_discharge_a')}, voltage={voltage} -> {max_discharge_kw} kW"
        )

    print(f"[DEBUG] control_unit={control_unit}")
    print(f"[DEBUG] battery section keys: {list(battery.keys())}")
    print(f"[DEBUG] Final: max_charge_kw={max_charge_kw}, max_discharge_kw={max_discharge_kw}")

    kepler_cfg = KeplerConfig(
        capacity_kwh=capacity,
        min_soc_percent=float(battery.get("min_soc_percent", 10.0)),
        max_soc_percent=float(battery.get("max_soc_percent", 100.0)),
        max_charge_power_kw=max_charge_kw,
        max_discharge_power_kw=max_discharge_kw,
        charge_efficiency=charge_eff,
        discharge_efficiency=discharge_eff,
        wear_cost_sek_per_kwh=float(
            planner_config.get("battery_economics", {}).get(
                "battery_cycle_cost_kwh", get_val("wear_cost_sek_per_kwh", 0.0)
            )
        ),
        max_export_power_kw=(
            float(system.get("grid", {}).get("max_power_kw"))
            if system.get("grid", {}).get("max_power_kw")
            else None
        ),
        max_import_power_kw=(
            float(system.get("grid", {}).get("max_power_kw"))
            if system.get("grid", {}).get("max_power_kw")
            else None
        ),
        ramping_cost_sek_per_kw=float(
            planner_config.get("kepler", {}).get(
                "ramping_cost_sek_per_kw", get_val("ramping_cost_sek_per_kw", 0.05)
            )
        ),
        curtailment_penalty_sek=float(
            planner_config.get("kepler", {}).get("curtailment_penalty_sek", 0.1)
        ),
        # Water heating as deferrable load
        water_heating_power_kw=float(wh_cfg.get("power_kw", 0.0)),
        water_heating_min_kwh=float(wh_cfg.get("min_kwh_per_day", 0.0)),
        # PRODUCTION FIX B1: Disable BOTH gap penalty AND spacing when enable_top_ups=false
        water_heating_max_gap_hours=float(
            wh_cfg.get("max_hours_between_heating", 8.0)
            if wh_cfg.get("enable_top_ups", True)
            else 0.0
        ),
        water_heated_today_kwh=0.0,  # Set in pipeline from HA sensor
        # Rev K23: Multi-Parameter Comfort Control (ALWAYS applied)
        # Rev K24: Apply bulk mode override if enable_top_ups=false
        # type: ignore[arg-type]
        **(
            _apply_bulk_mode_override(
                _comfort_level_to_penalty(
                    int(wh_cfg.get("comfort_level", 3)),
                    daily_kwh=float(wh_cfg.get("min_kwh_per_day", 0.0)),
                    heater_power_kw=float(wh_cfg.get("power_kw", 0.0)),
                )
            )
            if not wh_cfg.get("enable_top_ups", True)
            else _comfort_level_to_penalty(
                int(wh_cfg.get("comfort_level", 3)),
                daily_kwh=float(wh_cfg.get("min_kwh_per_day", 0.0)),
                heater_power_kw=float(wh_cfg.get("power_kw", 0.0)),
            )
        ),
        # Rev WH1: Disable spacing constraints when top-ups are disabled
        water_min_spacing_hours=float(
            wh_cfg.get("min_spacing_hours", 5.0) if wh_cfg.get("enable_top_ups", True) else 0.0
        ),
        water_spacing_penalty_sek=float(
            wh_cfg.get("spacing_penalty_sek", 0.20) if wh_cfg.get("enable_top_ups", True) else 0.0
        ),
        # Rev WH2: Smart Water Heating Logic
        force_water_on_slots=force_water_on_slots,
        defer_up_to_hours=float(wh_cfg.get("defer_up_to_hours", 0.0)),
        # Rev E4: Export Toggle
        enable_export=bool(planner_config.get("export", {}).get("enable_export", True)),
        # Rev // F51: Piecewise Incentive Buckets
        ev_charging_enabled=ev_enabled,
        ev_max_power_kw=float(ev_cfg.get("max_power_kw", 0.0)),
        ev_battery_capacity_kwh=float(ev_cfg.get("battery_capacity_kwh", 0.0)),
        ev_current_soc_percent=0.0,  # Set by pipeline from HA sensor
        ev_plugged_in=False,  # Set by pipeline from HA sensor
        ev_deadline=None,  # Set by pipeline from HA sensor
        ev_deadline_urgent=False,  # Set by pipeline from HA sensor
        ev_incentive_buckets=[
            IncentiveBucket(
                threshold_soc=float(p.get("max_soc", 100.0)),
                value_sek=float(p.get("penalty_sek", 0.0)),
            )
            for p in ev_cfg.get("penalty_levels", [])
            if "max_soc" in p or "penalty_sek" in p
        ]
        if ev_cfg.get("penalty_levels")
        else None,
    )

    return kepler_cfg


def kepler_result_to_dataframe(
    result: KeplerResult, capacity_kwh: float = 0.0, initial_soc_kwh: float = 0.0
) -> pd.DataFrame:
    """
    Convert KeplerResult to a DataFrame suitable for logging/comparison.
    Matches the column structure expected by the UI.
    """
    records: list[dict[str, Any]] = []
    prev_soc_kwh = initial_soc_kwh

    for s in result.slots:
        duration_h = (s.end_time - s.start_time).total_seconds() / 3600.0
        if duration_h <= 0:
            duration_h = 0.25

        charge_kw = s.charge_kwh / duration_h
        discharge_kw = s.discharge_kwh / duration_h

        action = "Hold"
        if charge_kw > 0.01:
            action = "Charge"
        elif discharge_kw > 0.01:
            action = "Export" if s.grid_export_kwh > 0.01 else "Discharge"

        entry_soc_kwh = prev_soc_kwh
        entry_soc_percent = (entry_soc_kwh / capacity_kwh * 100.0) if capacity_kwh > 0 else 0.0
        prev_soc_kwh = s.soc_kwh

        records.append(  # type: ignore[arg-type]
            {
                "start_time": s.start_time,
                "end_time": s.end_time,
                "kepler_charge_kwh": s.charge_kwh,
                "kepler_discharge_kwh": s.discharge_kwh,
                "kepler_import_kwh": s.grid_import_kwh,
                "kepler_export_kwh": s.grid_export_kwh,
                "kepler_soc_kwh": s.soc_kwh,
                "kepler_cost_sek": s.cost_sek,
                "planned_cost_sek": (s.grid_import_kwh * s.import_price_sek_kwh)
                - (s.grid_export_kwh * s.export_price_sek_kwh),
                "battery_charge_kw": charge_kw,
                "battery_discharge_kw": discharge_kw,
                "discharge_kw": discharge_kw,  # Alias for simulation.py compatibility
                "charge_kw": min(s.charge_kwh, s.grid_import_kwh) / duration_h,
                "projected_soc_kwh": s.soc_kwh,
                "projected_soc_percent": (
                    (s.soc_kwh / capacity_kwh * 100.0) if capacity_kwh > 0 else 0.0
                ),
                "_entry_soc_percent": entry_soc_percent,
                "action": action,
                "grid_import_kw": s.grid_import_kwh / duration_h,
                "grid_export_kw": s.grid_export_kwh / duration_h,
                "import_kwh": s.grid_import_kwh,
                "export_kwh": s.grid_export_kwh,
                "water_heating_kw": s.water_heat_kw,  # From Kepler MILP (Rev K17)
                "water_from_grid_kwh": 0.0,
                "water_from_pv_kwh": 0.0,
                "water_from_battery_kwh": 0.0,
                "ev_charging_kw": s.ev_charge_kw,  # From Kepler MILP (Rev K25)
                "projected_battery_cost": 0.0,
            }
        )

    df = pd.DataFrame(records)  # type: ignore[arg-type]
    if not df.empty:
        df.set_index("start_time", inplace=True)
    return df
