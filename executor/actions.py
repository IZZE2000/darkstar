"""
Action Dispatcher

Executes actions by calling Home Assistant services.
Handles idempotent execution (skip if already set) and
notification dispatch per action type.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from .config import ExecutorConfig
from .controller import ControllerDecision
from .profiles import InverterProfile

logger = logging.getLogger(__name__)


def _is_entity_configured(entity: str | None) -> bool:
    """Check if an entity ID is properly configured.

    Returns False if entity is:
    - None
    - Empty string
    - Whitespace only
    - Literal string "None" (case-insensitive)
    """
    if not entity:
        return False
    stripped = entity.strip()
    return stripped != "" and stripped.lower() != "none"


@dataclass
class ActionResult:
    """Result of executing an action."""

    action_type: str
    success: bool
    message: str = ""
    previous_value: Any | None = None
    new_value: Any | None = None
    entity_id: str | None = None  # NEW: The HA entity being controlled
    verified_value: Any | None = None  # NEW: Value read back after setting
    verification_success: bool | None = None  # NEW: Whether verification matched expected value
    skipped: bool = False  # True if action was skipped (already at target)
    duration_ms: int = 0


class HAClient:
    """
    Home Assistant API client for executing actions.

    Uses the REST API to call services and get entity states.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )

    def get_state(self, entity_id: str) -> dict[str, Any] | None:
        """Get the current state of an entity."""
        # Early validation: catch None/invalid entity_id before hitting HA API
        if not entity_id or (
            isinstance(entity_id, str) and entity_id.strip().lower() in ("", "none")
        ):
            logger.error(
                "get_state called with invalid entity_id: %r (type: %s) - "
                "check config.yaml for missing entity configuration",
                entity_id,
                type(entity_id).__name__,
            )
            return None

        try:
            response = self._session.get(
                f"{self.base_url}/api/states/{entity_id}",
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("Failed to get state of %s: %s", entity_id, e)
            return None

    def get_state_value(self, entity_id: str) -> str | None:
        """Get just the state value of an entity."""
        state = self.get_state(entity_id)
        if state:
            return state.get("state")
        return None

    def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """
        Call a Home Assistant service.

        Args:
            domain: Service domain (e.g., 'switch', 'select', 'number')
            service: Service name (e.g., 'turn_on', 'select_option', 'set_value')
            entity_id: Target entity ID (optional)
            data: Additional service data (optional)

        Returns:
            True if successful, False otherwise
        """
        payload = data or {}
        if entity_id:
            payload["entity_id"] = entity_id

        logger.debug(
            "HA call_service: %s.%s on %s with payload: %s", domain, service, entity_id, payload
        )

        try:
            response = self._session.post(
                f"{self.base_url}/api/services/{domain}/{service}",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(
                "Failed to call service %s.%s on %s: %s",
                domain,
                service,
                entity_id,
                e,
            )
            return False

    def _get_safe_domain(self, entity_id: str, allowed_domains: set[str]) -> str | None:
        """
        Get the domain from an entity ID and validate it is safe to control.

        Args:
            entity_id: The HA entity ID (e.g., 'input_select.mode')
            allowed_domains: Set of allowed domains (e.g., {'select', 'input_select'})

        Returns:
            The domain string if valid, None if invalid or unsafe.
        """
        if not entity_id:
            return None

        parts = entity_id.split(".", 1)
        if len(parts) != 2:
            logger.error("Invalid entity_id format: %s", entity_id)
            return None

        domain = parts[0]

        # Explicit safety guard against sensors
        if domain in ("sensor", "binary_sensor"):
            logger.error(
                "SAFETY GUARD: Cannot control read-only entity '%s'. "
                "Check config.yaml and use a controllable entity (e.g., input_number, helper).",
                entity_id,
            )
            return None

        if domain not in allowed_domains:
            logger.error(
                "Domain '%s' not allowed for this action. Allowed: %s. Entity: %s",
                domain,
                allowed_domains,
                entity_id,
            )
            return None

        return domain

    def set_select_option(self, entity_id: str, option: str) -> bool:
        """Set a select entity to a specific option."""
        domain = self._get_safe_domain(entity_id, {"select", "input_select"})
        if not domain:
            return False
        return self.call_service(domain, "select_option", entity_id, {"option": option})

    def set_switch(self, entity_id: str, state: bool) -> bool:
        """Turn a switch on or off."""
        domain = self._get_safe_domain(entity_id, {"switch", "input_boolean"})
        if not domain:
            return False
        service = "turn_on" if state else "turn_off"
        return self.call_service(domain, service, entity_id)

    def set_number(self, entity_id: str, value: float) -> bool:
        """Set a number entity to a specific value."""
        domain = self._get_safe_domain(entity_id, {"number", "input_number"})
        if not domain:
            return False
        return self.call_service(domain, "set_value", entity_id, {"value": value})

    def set_input_number(self, entity_id: str, value: float) -> bool:
        """Set an input_number entity to a specific value."""
        # Alias to set_number which now handles both
        return self.set_number(entity_id, value)

    def send_notification(
        self,
        service: str | None,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send a notification via a notify service.

        Args:
            service: Full notification service name (e.g., 'notify.mobile_app_phone')
            title: Notification title
            message: Notification message
            data: Additional notification data (optional)

        Returns:
            True if successful, False otherwise
        """
        if not service:
            return False

        # Parse service name (e.g., "notify.mobile_app_phone" -> domain="notify", service="mobile_app_phone")
        parts = service.split(".", 1)
        if len(parts) != 2:
            logger.error("Invalid notification service format: %s", service)
            return False

        domain, svc_name = parts
        payload: dict[str, Any] = {
            "title": title,
            "message": message,
        }
        if data:
            payload["data"] = data

        return self.call_service(domain, svc_name, data=payload)


class ActionDispatcher:
    """
    Dispatches actions to Home Assistant based on controller decisions.

    Features:
    - Idempotent execution (skip if already at target)
    - Configurable notifications per action type
    - Action result tracking
    """

    def __init__(
        self,
        ha_client: HAClient,
        config: ExecutorConfig,
        shadow_mode: bool = False,
        profile: InverterProfile | None = None,
    ):
        self.ha = ha_client
        self.config = config
        self.shadow_mode = shadow_mode
        self.profile = profile

    async def execute(self, decision: ControllerDecision) -> list[ActionResult]:
        """
        Execute all actions from a controller decision.

        Args:
            decision: The controller's decision on what actions to take

        Returns:
            List of ActionResult for each action attempted
        """
        results: list[ActionResult] = []

        # 1. Set work mode (Rev O1)
        if self.config.has_battery:
            result = await self._set_work_mode(decision.work_mode)
            results.append(result)

        # 2. Set grid charging (Rev O1)
        if self.config.has_battery:
            result = await self._set_grid_charging(decision.grid_charging)
            results.append(result)

        # 3. Set charge limit (Rev O1 + E3)
        if self.config.has_battery and decision.write_charge_current:
            result = await self._set_charge_limit(decision.charge_value, decision.control_unit)
            results.append(result)

        # 4. Set discharge limit (Rev O1 + E3)
        if self.config.has_battery and decision.write_discharge_current:
            result = await self._set_discharge_limit(
                decision.discharge_value, decision.control_unit
            )
            results.append(result)

        # 5. Set SoC target (Rev O1)
        if self.config.has_battery:
            result = await self._set_soc_target(decision.soc_target)
            results.append(result)

        # 6. Set water heater target (Rev O1)
        if self.config.has_water_heater:
            result = await self.set_water_temp(decision.water_temp)
            results.append(result)

        # 7. Set max export power (Bug fix #1)
        if self.config.has_battery:
            result = await self._set_max_export_power(decision.export_power_w)
            results.append(result)

        return results

    async def _set_work_mode(self, target_mode: str) -> ActionResult:
        """Set inverter work mode if different from current."""
        start = time.time()
        entity = self.config.inverter.work_mode_entity

        if not _is_entity_configured(entity):
            logger.debug("Skipping work_mode action: entity not configured")
            return ActionResult(
                action_type="work_mode",
                success=True,
                message="Work mode entity not configured. Configure in Settings → System → HA Entities",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        # Get current state
        current = self.ha.get_state_value(entity)

        if current == target_mode:
            return ActionResult(
                action_type="work_mode",
                success=True,
                message=f"Already at {target_mode}",
                previous_value=current,
                new_value=target_mode,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        if self.shadow_mode:
            logger.info("[SHADOW] Would set work_mode to %s (current: %s)", target_mode, current)
            return ActionResult(
                action_type="work_mode",
                success=True,
                message=f"[SHADOW] Would change {current} → {target_mode}",
                previous_value=current,
                new_value=target_mode,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        # Apply work mode change
        success = self.ha.set_select_option(entity, target_mode)

        # Handle composite mode entities (Rev IP2)
        # Some inverters (e.g. Sungrow) require setting multiple entities for a single mode change
        if success and self.profile:
            # unique string value -> mode object lookup
            mode_obj = None
            for m in [
                self.profile.modes.export,
                self.profile.modes.zero_export,
                self.profile.modes.self_consumption,
                self.profile.modes.charge_from_grid,
                self.profile.modes.force_discharge,
                self.profile.modes.idle,
            ]:
                if m and m.value == target_mode:
                    mode_obj = m
                    break

            if mode_obj and mode_obj.set_entities:
                logger.debug("Applying composite mode entities for %s", target_mode)
                for key, val in mode_obj.set_entities.items():
                    # Look up entity ID from custom_entities config
                    # Fallback to standard entities checks if needed, but custom_entities is preferred for profile-specifics
                    entity_id = self.config.inverter.custom_entities.get(key)
                    if not _is_entity_configured(entity_id):
                        logger.warning(
                            "Profile requires setting '%s' to '%s', but entity is not configured",
                            key,
                            val,
                        )
                        continue

                    logger.info("Composite Mode: Setting %s to %s", entity_id, val)
                    if isinstance(val, int | float):
                        self.ha.set_number(entity_id, float(val))
                    elif isinstance(val, str):
                        self.ha.set_select_option(entity_id, val)
                    elif isinstance(val, bool):
                        self.ha.set_switch(entity_id, val)

        # Mode settling delay (Rev IP1 Phase 3)
        if success and self.profile and self.profile.behavior.requires_mode_settling:
            settle_ms = self.profile.behavior.mode_settling_ms
            logger.debug(
                "Applying mode settling delay: %dms for %s", settle_ms, self.profile.metadata.name
            )
            await asyncio.sleep(settle_ms / 1000.0)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(entity, target_mode)

        duration = int((time.time() - start) * 1000)

        if success:
            self._maybe_notify("work_mode", f"Work mode changed to {target_mode}")

        return ActionResult(
            action_type="work_mode",
            success=success,
            message=f"Changed {current} → {target_mode}" if success else "Failed to set work mode",
            previous_value=current,
            new_value=target_mode,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
        )

    async def _set_grid_charging(self, enabled: bool) -> ActionResult:
        """Set grid charging switch."""
        start = time.time()
        entity = self.config.inverter.grid_charging_entity
        target = "on" if enabled else "off"

        # Handle grid charging via profile logic if available (Rev ARC13 Phase 4)
        if self.profile and not self.profile.capabilities.separate_grid_charging_switch:
            logger.debug(
                "Skipping grid_charging switch: profile '%s' uses mode-based charging",
                self.profile.metadata.name,
            )
            return ActionResult(
                action_type="grid_charging",
                success=True,
                message=f"Handled by work_mode ({target})",
                new_value=target,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        if not _is_entity_configured(entity):
            logger.debug("Skipping grid_charging action: entity not configured")
            return ActionResult(
                action_type="grid_charging",
                success=True,
                message="Grid charging entity not configured. Configure in Settings → System → HA Entities",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        # Get current state
        current = self.ha.get_state_value(entity)

        if current == target:
            return ActionResult(
                action_type="grid_charging",
                success=True,
                message=f"Already {target}",
                previous_value=current,
                new_value=target,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        if self.shadow_mode:
            logger.info("[SHADOW] Would set grid_charging to %s (current: %s)", target, current)
            return ActionResult(
                action_type="grid_charging",
                success=True,
                message=f"[SHADOW] Would change {current} → {target}",
                previous_value=current,
                new_value=target,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        # Handle grid charging via profile logic if available
        success = self.ha.set_switch(entity, enabled)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(entity, target)

        duration = int((time.time() - start) * 1000)

        action = "start" if enabled else "stop"
        if success:
            self._maybe_notify(f"charge_{action}", f"Grid charging {action}ed")

        return ActionResult(
            action_type="grid_charging",
            success=success,
            message=f"Changed {current} → {target}" if success else "Failed to set grid charging",
            previous_value=current,
            new_value=target,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
        )

    async def _set_charge_limit(self, value: float, unit: str) -> ActionResult:
        """Set max charging limit (Amps or Watts)."""
        start = time.time()

        if unit == "W":
            entity = self.config.inverter.max_charging_power_entity
            unit_label = "W"
        else:
            entity = self.config.inverter.max_charging_current_entity
            unit_label = "A"

        if not _is_entity_configured(entity):
            logger.debug("Skipping charge_limit action: entity not configured for unit %s", unit)
            return ActionResult(
                action_type="charge_limit",
                success=True,
                message=f"Max charge {unit_label} entity not configured. Configure in Settings.",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        logger.info("Setting charge_limit: %.1f %s on entity: %s", value, unit_label, entity)

        if self.shadow_mode:
            logger.info("[SHADOW] Would set charge_limit to %s %s", value, unit_label)
            return ActionResult(
                action_type="charge_limit",
                success=True,
                message=f"[SHADOW] Would set to {value} {unit_label}",
                new_value=value,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        success = self.ha.set_number(entity, value)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(entity, value)

        duration = int((time.time() - start) * 1000)
        logger.info("Set charge_limit result: success=%s, duration=%dms", success, duration)

        return ActionResult(
            action_type="charge_limit",
            success=success,
            message=f"Set to {value} {unit_label}" if success else "Failed to set charge limit",
            new_value=value,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
        )

    async def _set_discharge_limit(self, value: float, unit: str) -> ActionResult:
        """Set max discharging limit (Amps or Watts)."""
        start = time.time()

        if unit == "W":
            entity = self.config.inverter.max_discharging_power_entity
            unit_label = "W"
        else:
            entity = self.config.inverter.max_discharging_current_entity
            unit_label = "A"

        if not _is_entity_configured(entity):
            logger.debug("Skipping discharge_limit action: entity not configured for unit %s", unit)
            return ActionResult(
                action_type="discharge_limit",
                success=True,
                message=f"Max discharge {unit_label} entity not configured. Configure in Settings.",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        result_label = f"{value} {unit_label}"
        logger.info("Setting discharge_limit: %s on entity: %s", result_label, entity)

        if self.shadow_mode:
            logger.info(
                "[SHADOW] Would set discharge_limit to %s %s on entity %s",
                value,
                unit_label,
                entity,
            )
            return ActionResult(
                action_type="discharge_limit",
                success=True,
                message=f"[SHADOW] Would set to {result_label}",
                new_value=value,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        # Safety Guard: Prevent extremely high Amps (Rev E3 Bug Fix)
        if unit == "A" and value > 500:
            logger.error(
                "SAFETY GUARD: Refusing to set discharge limit to %.0fA (limit exceeded)", value
            )
            return ActionResult(
                action_type="discharge_limit",
                success=False,
                message=f"Refused dangerously high limit: {value}A",
                entity_id=entity,
                skipped=False,
                duration_ms=int((time.time() - start) * 1000),
            )

        success = self.ha.set_number(entity, value)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(entity, value)

        duration = int((time.time() - start) * 1000)
        logger.info("Set discharge_limit result: success=%s, duration=%dms", success, duration)

        return ActionResult(
            action_type="discharge_limit",
            success=success,
            message=f"Set to {value} {unit_label}" if success else "Failed to set discharge limit",
            new_value=value,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
        )

    async def _set_soc_target(self, target: int) -> ActionResult:
        """Set SoC target."""
        start = time.time()
        entity = self.config.inverter.soc_target_entity

        if not _is_entity_configured(entity):
            # Check if this entity is actually required by the profile
            is_required = True
            if self.profile:
                # If we have a profile, check if soc_target_entity is in its required list
                is_required = "soc_target_entity" in self.profile.entities.required

            if not is_required:
                # Silent skip - not configured and not required
                return ActionResult(
                    action_type="soc_target",
                    success=True,
                    message="",  # Empty message = no log
                    skipped=True,
                    duration_ms=int((time.time() - start) * 1000),
                )

            logger.debug("Skipping soc_target action: entity not configured")
            return ActionResult(
                action_type="soc_target",
                success=True,
                message="SoC target entity not configured. Configure in Settings → System → HA Entities",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        current = self.ha.get_state_value(entity)
        try:
            current_val = int(float(current)) if current else None
        except (ValueError, TypeError):
            current_val = None

        if current_val == target:
            return ActionResult(
                action_type="soc_target",
                success=True,
                message=f"Already at {target}%",
                previous_value=current_val,
                new_value=target,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        if self.shadow_mode:
            logger.info(
                "[SHADOW] Would set soc_target to %s%% (current: %s%%)", target, current_val
            )
            return ActionResult(
                action_type="soc_target",
                success=True,
                message=f"[SHADOW] Would change {current_val}% → {target}%",
                previous_value=current_val,
                new_value=target,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        success = self.ha.set_input_number(entity, float(target))

        # Verification
        verified_value = None
        verification_success = None
        if success:
            v_val, v_ok = await self._verify_action(entity, target)
            verification_success = v_ok
            try:
                verified_value = int(float(v_val)) if v_val else None
            except (ValueError, TypeError):
                verified_value = v_val

        duration = int((time.time() - start) * 1000)

        if success and self.config.notifications.on_soc_target_change:
            self._send_notification(f"SoC target changed to {target}%")

        return ActionResult(
            action_type="soc_target",
            success=success,
            message=(
                f"Changed {current_val}% → {target}%" if success else "Failed to set SoC target"
            ),
            previous_value=current_val,
            new_value=target,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
        )

    async def set_water_temp(self, target: int) -> ActionResult:
        """Set water heater target temperature."""
        start = time.time()
        entity = self.config.water_heater.target_entity

        if not _is_entity_configured(entity):
            logger.debug("Skipping water_temp action: entity not configured")
            return ActionResult(
                action_type="water_temp",
                success=True,
                message="Water heater target entity not configured. Configure in Settings → System → HA Entities",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        current = self.ha.get_state_value(entity)
        try:
            current_val = int(float(current)) if current else None
        except (ValueError, TypeError):
            current_val = None

        if current_val == target:
            return ActionResult(
                action_type="water_temp",
                success=True,
                message=f"Already at {target}°C",
                previous_value=current_val,
                new_value=target,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        if self.shadow_mode:
            logger.info(
                "[SHADOW] Would set water_temp to %s°C (current: %s°C)", target, current_val
            )
            return ActionResult(
                action_type="water_temp",
                success=True,
                message=f"[SHADOW] Would change {current_val}°C → {target}°C",
                previous_value=current_val,
                new_value=target,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        success = self.ha.set_input_number(entity, float(target))

        # Verification
        verified_value = None
        verification_success = None
        if success:
            v_val, v_ok = await self._verify_action(entity, target)
            verification_success = v_ok
            try:
                verified_value = int(float(v_val)) if v_val else None
            except (ValueError, TypeError):
                verified_value = v_val

        duration = int((time.time() - start) * 1000)

        # Determine if this is start or stop
        is_heating = target > self.config.water_heater.temp_off
        action = "start" if is_heating else "stop"
        if success:
            self._maybe_notify(f"water_heat_{action}", f"Water heater target: {target}°C")

        return ActionResult(
            action_type="water_temp",
            success=success,
            message=(
                f"Changed {current_val}°C → {target}°C" if success else "Failed to set water temp"
            ),
            previous_value=current_val,
            new_value=target,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
        )

    async def _set_max_export_power(self, watts: float) -> ActionResult:
        """Set max grid export power (Bug Fix #1)."""
        start = time.time()
        entity = self.config.inverter.grid_max_export_power_entity

        if not _is_entity_configured(entity):
            logger.debug("Skipping max_export_power action: entity not configured")
            return ActionResult(
                action_type="max_export_power",
                success=True,
                message="Export power entity not configured. Configure in Settings → System → HA Entities",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        # Check current value and apply write threshold to prevent EEPROM wear
        current = self.ha.get_state_value(entity)
        try:
            current_val = float(current) if current else None
        except (ValueError, TypeError):
            current_val = None

        if current_val is not None:
            change = abs(watts - current_val)
            if change < self.config.controller.write_threshold_w:
                return ActionResult(
                    action_type="max_export_power",
                    success=True,
                    message=f"Change {change:.0f}W < threshold {self.config.controller.write_threshold_w:.0f}W, skipping",
                    previous_value=current_val,
                    new_value=watts,
                    entity_id=entity,
                    skipped=True,
                    duration_ms=int((time.time() - start) * 1000),
                )

        if self.shadow_mode:
            logger.info("[SHADOW] Would set max_export_power to %s W", watts)
            return ActionResult(
                action_type="max_export_power",
                success=True,
                message=f"[SHADOW] Would set to {watts} W",
                new_value=watts,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
            )

        success = self.ha.set_number(entity, watts)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(entity, watts)

        duration = int((time.time() - start) * 1000)

        logger.info("Set max_export_power: %.0f W on %s (success=%s)", watts, entity, success)

        return ActionResult(
            action_type="max_export_power",
            success=success,
            message=f"Set to {watts} W" if success else "Failed to set export power",
            previous_value=current_val,
            new_value=watts,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
        )

    async def _verify_action(
        self, entity_id: str, expected_value: Any, timeout: float = 2.0
    ) -> tuple[Any, bool]:
        """
        Verify that an action successfully changed the state of an entity.

        Args:
            entity_id: The HA entity ID to check
            expected_value: The value we expect the entity to have
            timeout: Max time to wait for state update (seconds)

        Returns:
            tuple of (actual_value, success)
        """
        # Wait 1s for HA/Inverter to update
        await asyncio.sleep(1.0)

        start_wait = time.time()
        actual_value = None

        while time.time() - start_wait < timeout:
            actual_value = self.ha.get_state_value(entity_id)

            # Support loose matching for numeric types
            if isinstance(expected_value, int | float) and actual_value is not None:
                try:
                    # STRICTER TOLERANCE (REV UI11): 1.0 -> 0.1
                    if abs(float(actual_value) - float(expected_value)) < 0.1:
                        return actual_value, True
                except (ValueError, TypeError):
                    pass
            elif str(actual_value) == str(expected_value):
                return actual_value, True

            await asyncio.sleep(0.5)

        logger.warning(
            "Verification FAILED for %s: Expected %s, got %s",
            entity_id,
            expected_value,
            actual_value,
        )
        return actual_value, False

    def _maybe_notify(self, action_type: str, message: str) -> None:
        """Send notification if enabled for this action type."""
        notif = self.config.notifications

        # Map action types to notification flags
        should_notify = {
            "charge_start": notif.on_charge_start,
            "charge_stop": notif.on_charge_stop,
            "export_start": notif.on_export_start,
            "export_stop": notif.on_export_stop,
            "water_heat_start": notif.on_water_heat_start,
            "water_heat_stop": notif.on_water_heat_stop,
            "work_mode": notif.on_export_start or notif.on_export_stop,
            "override": notif.on_override_activated,
            "error": notif.on_error,
        }.get(action_type, False)

        if should_notify:
            self._send_notification(message)

    def _send_notification(self, message: str, title: str = "Darkstar Executor") -> None:
        """Send a notification via the configured service."""
        if self.shadow_mode:
            logger.info("[SHADOW] Would send notification: %s", message)
            return

        try:
            self.ha.send_notification(
                self.config.notifications.service,
                title,
                message,
            )
        except Exception as e:
            logger.warning("Failed to send notification: %s", e)

    def notify_override(self, override_type: str, reason: str) -> None:
        """Send notification about an override activation."""
        if self.config.notifications.on_override_activated:
            self._send_notification(
                f"Override: {override_type}\n{reason}",
                title="Darkstar Override Active",
            )

    def notify_error(self, error: str) -> None:
        """Send notification about an error."""
        if self.config.notifications.on_error:
            self._send_notification(
                f"Error: {error}",
                title="Darkstar Executor Error",
            )
