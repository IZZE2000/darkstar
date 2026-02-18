"""
Controller Logic

Action decision-making based on slot plan and current state.
Ported from the n8n Helios Executor "Controller" code node.

Determines:
- Which inverter work mode to set
- Whether to enable grid charging
- What charge/discharge currents to command
- SoC target to set
- Water heater temperature target
"""

import logging
from dataclasses import dataclass

# from typing import Any, Dict, Optional, Tuple
from .config import ControllerConfig, InverterConfig, WaterHeaterConfig
from .override import OverrideResult, SlotPlan, SystemState
from .profiles import InverterProfile

logger = logging.getLogger(__name__)


@dataclass
class ControllerDecision:
    """The controller's decision on what actions to take.

    Uses 4 mode intents: charge, export, idle, self_consumption.
    The executor looks up the mode definition from the profile to get
    the ordered list of actions to execute.
    """

    # Mode intent - the primary field (required)
    # Values: "charge", "export", "idle", "self_consumption"
    mode_intent: str

    # Charge/discharge values (templates for executor to resolve)
    charge_value: float = 0.0
    discharge_value: float = 0.0

    # SoC target
    soc_target: int = 10

    # Water heater
    water_temp: int = 40
    export_power_w: float = 0.0  # Planned grid export power in Watts

    # User's configured max limits (for templates like {{max_charge}})
    max_charge: float = 0.0
    max_discharge: float = 0.0

    # Flags
    write_charge_current: bool = False  # Only write if significant change
    write_discharge_current: bool = False
    control_unit: str = "A"  # "A" or "W"
    source: str = "plan"  # "plan" or "override"
    reason: str = ""


class Controller:
    """
    Determines actions based on slot plan and current state.

    Ported from n8n Helios Executor "Controller" JavaScript node.
    """

    def __init__(
        self,
        config: ControllerConfig,
        inverter_config: InverterConfig,
        water_heater_config: WaterHeaterConfig | None = None,
        profile: InverterProfile | None = None,
    ):
        self.config = config
        self.inverter_config = inverter_config
        self.water_heater_config = water_heater_config or WaterHeaterConfig()
        self.profile = profile

    def decide(
        self,
        slot: SlotPlan,
        state: SystemState,
        override: OverrideResult | None = None,
    ) -> ControllerDecision:
        """
        Determine what actions to take based on slot plan and override.

        Args:
            slot: The current slot's planned values
            state: Current system state
            override: Override result if any override is active

        Returns:
            ControllerDecision with all action parameters
        """
        # If override is active, apply override actions
        if override and override.override_needed:
            return self._apply_override(slot, state, override)

        # Normal operation - follow the plan
        return self._follow_plan(slot, state)

    def _apply_override(
        self,
        slot: SlotPlan,
        state: SystemState,
        override: OverrideResult,
    ) -> ControllerDecision:
        """Apply override actions instead of plan using 4 mode intents."""
        actions = override.actions or {}

        # Determine mode intent from override type
        mode_intent = "idle"  # default

        if override.override_type.value in ("force_charge", "emergency_charge"):
            mode_intent = "charge"
        elif override.override_type.value == "force_export":
            mode_intent = "export"

        # For overrides, we typically don't actively charge/discharge
        # unless specifically requested
        charge_value = 0.0
        discharge_value = 0.0
        write_charge = False
        write_discharge = False

        # Handle quick action charging
        if override.override_type.value in ("force_charge", "emergency_charge"):
            # Force charge - use max charging value
            if self.inverter_config.control_unit == "W":
                charge_value = self.config.max_charge_w
            else:
                charge_value = self.config.max_charge_a
            write_charge = True

        # Handle quick action exporting
        if override.override_type.value == "force_export":
            # Force export - allow max discharge
            if self.inverter_config.control_unit == "W":
                discharge_value = self.config.max_discharge_w
            else:
                discharge_value = self.config.max_discharge_a
            write_discharge = True

        # Get SoC target and water temp from override
        soc_target = int(actions.get("soc_target", 10))
        water_temp = int(actions.get("water_temp", 40))

        # User's configured max limits (for templates)
        unit = (
            self.profile.behavior.control_unit
            if self.profile
            else self.inverter_config.control_unit
        )
        max_charge = self.config.max_charge_w if unit == "W" else self.config.max_charge_a
        max_discharge = self.config.max_discharge_w if unit == "W" else self.config.max_discharge_a

        return ControllerDecision(
            mode_intent=mode_intent,
            charge_value=charge_value,
            discharge_value=discharge_value,
            export_power_w=0.0,
            soc_target=soc_target,
            water_temp=water_temp,
            max_charge=max_charge,
            max_discharge=max_discharge,
            write_charge_current=write_charge,
            write_discharge_current=write_discharge,
            control_unit=unit,
            source="override",
            reason=override.reason,
        )

    def _follow_plan(self, slot: SlotPlan, state: SystemState) -> ControllerDecision:
        """Follow the slot plan for normal operation using 4 mode intents."""
        # Determine mode intent based on slot plan
        # Order matters: export > charge > idle > self_consumption
        if slot.export_kw > 0:
            mode_intent = "export"
        elif slot.charge_kw > 0:
            mode_intent = "charge"
        elif state.current_soc_percent <= slot.soc_target:
            # At or below SoC target - use idle to hold battery
            mode_intent = "idle"
        else:
            # Above SoC target - use self_consumption
            mode_intent = "self_consumption"

        # Calculate charge/discharge values
        charge_value, write_charge = self._calculate_charge_limit(slot, state)
        discharge_value, write_discharge = self._calculate_discharge_limit(slot, state)

        # Planned grid export power (kW to W)
        export_power_w = slot.export_kw * 1000.0

        # SoC target from plan
        soc_target = slot.soc_target

        # Water heater from plan
        water_temp = self._determine_water_temp(slot)

        # User's configured max limits (for templates)
        unit = (
            self.profile.behavior.control_unit
            if self.profile
            else self.inverter_config.control_unit
        )
        max_charge = self.config.max_charge_w if unit == "W" else self.config.max_charge_a
        max_discharge = self.config.max_discharge_w if unit == "W" else self.config.max_discharge_a

        reason = self._generate_reason(slot, mode_intent)

        return ControllerDecision(
            mode_intent=mode_intent,
            charge_value=charge_value,
            discharge_value=discharge_value,
            export_power_w=export_power_w,
            soc_target=soc_target,
            water_temp=water_temp,
            max_charge=max_charge,
            max_discharge=max_discharge,
            write_charge_current=write_charge,
            write_discharge_current=write_discharge,
            control_unit=unit,
            source="plan",
            reason=reason,
        )

    def _calculate_charge_limit(self, slot: SlotPlan, state: SystemState) -> tuple[float, bool]:
        """
        Calculate the charge limit to command (Amps or Watts).
        """
        unit = self.inverter_config.control_unit
        if self.profile and self.profile.behavior.control_unit:
            unit = self.profile.behavior.control_unit

        if slot.charge_kw <= 0:
            logger.debug("No charge planned, returning 0")
            return 0.0, False

        if unit == "W":
            # Watts Logic
            raw_val = slot.charge_kw * 1000.0

            # Round to step
            is_grid_charge = slot.charge_kw > 0
            step = self.profile.behavior.round_step_w if self.profile else self.config.round_step_w

            # Use grid-specific rounding if available (Rev IP1 Phase 4)
            if is_grid_charge and self.profile and self.profile.behavior.grid_charge_round_step_w:
                step = self.profile.behavior.grid_charge_round_step_w
                logger.debug("Using grid-specific rounding step: %.1fW", step)

            rounded = round(raw_val / step) * step

            # Clamp
            min_w = self.profile.behavior.min_charge_w if self.profile else self.config.min_charge_w
            max_w = self.config.max_charge_w
            clamped = max(min_w, min(max_w, rounded))

            # Decide if we should write
            should_write = clamped >= min_w

            return clamped, should_write

        else:
            # Amps Logic (Default)
            # kW to Amps: I = P * 1000 / V
            raw_current = (slot.charge_kw * 1000) / self.config.min_voltage_v

            # Round to step
            round_step_a = (
                self.profile.behavior.round_step_a if self.profile else self.config.round_step_a
            )
            rounded = round(raw_current / round_step_a) * round_step_a

            # Clamp to limits
            min_a = self.profile.behavior.min_charge_a if self.profile else self.config.min_charge_a
            max_a = self.config.max_charge_a
            clamped = max(min_a, min(max_a, rounded))

            # Decide if we should write
            should_write = clamped >= min_a

            return clamped, should_write

    def _calculate_discharge_limit(self, slot: SlotPlan, state: SystemState) -> tuple[float, bool]:
        """
        Calculate the discharge limit to command.
        ALWAYS return MAX to allow load coverage.
        """
        if self.inverter_config.control_unit == "W":
            return self.config.max_discharge_w, True
        else:
            return self.config.max_discharge_a, True

    def _determine_water_temp(self, slot: SlotPlan) -> int:
        """Determine water heater target temperature from slot plan."""
        if slot.water_kw > 0:
            # Water heating is active - use configured normal temp
            return self.water_heater_config.temp_normal
        else:
            # No water heating - use configured off temp
            return self.water_heater_config.temp_off

    def _generate_reason(self, slot: SlotPlan, mode_intent: str) -> str:
        """Generate a human-readable reason for the decision."""
        parts: list[str] = []

        if slot.charge_kw > 0:
            parts.append(f"Charge {slot.charge_kw:.1f}kW")
        if slot.export_kw > 0:
            parts.append(f"Export {slot.export_kw:.1f}kW")
        if slot.water_kw > 0:
            parts.append(f"Water {slot.water_kw:.1f}kW")

        if not parts:
            parts.append("Hold/Idle")

        # Use mode intent directly for reason string
        mode_str = mode_intent.replace("_", " ").title()

        return f"Plan: {', '.join(parts)} | {mode_str} | SoC→{slot.soc_target}%"


def make_decision(
    slot: SlotPlan,
    state: SystemState,
    override: OverrideResult | None = None,
    config: ControllerConfig | None = None,
    inverter_config: InverterConfig | None = None,
    water_heater_config: WaterHeaterConfig | None = None,
    profile: InverterProfile | None = None,
) -> ControllerDecision:
    """
    Convenience function to make a controller decision.

    Args:
        slot: Current slot plan
        state: Current system state
        override: Override result if any
        config: Controller configuration
        inverter_config: Inverter configuration
        water_heater_config: Water heater temperature configuration

    Returns:
        ControllerDecision with all action parameters
    """
    controller = Controller(
        config or ControllerConfig(),
        inverter_config or InverterConfig(),
        water_heater_config,
        profile,
    )
    return controller.decide(slot, state, override)
