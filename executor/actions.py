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
from .profiles import InverterProfile, ModeAction

logger = logging.getLogger(__name__)


class HACallError(Exception):
    """Home Assistant API call error with detailed context."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        exception_type: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.exception_type = exception_type

        error_parts = [message]
        if status_code is not None:
            error_parts.append(f"HTTP {status_code}")
        if response_body:
            error_parts.append(f"Response: {response_body}")
        if exception_type:
            error_parts.append(f"({exception_type})")

        super().__init__(" | ".join(error_parts))


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


# Standard inverter entity keys that live directly in executor.inverter.*
# Any profile entity key NOT in this set goes into executor.inverter.custom_entities.*
_STANDARD_INVERTER_KEYS: frozenset[str] = frozenset(
    [
        "work_mode",
        "soc_target",
        "grid_charging_enable",
        "grid_charge_power",
        "minimum_reserve",
        "grid_max_export_power",
        "grid_max_export_power_switch",
        "max_charge_current",
        "max_discharge_current",
        "max_charge_power",
        "max_discharge_power",
    ]
)


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
    error_details: str | None = None  # REV F52 Phase 5: HA API error details (status, body, etc.)
    # ARC16: Track the controller's intended mode vs applied mode
    requested_mode: str | None = None  # The mode_intent from controller (e.g., "idle")
    applied_mode: str | None = None  # The actual mode whose entities were applied


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
        if not entity_id or entity_id.strip().lower() in ("", "none"):
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
            True if successful

        Raises:
            HACallError: If the API call fails
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
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            response_body = e.response.text if e.response is not None else None
            raise HACallError(
                message=f"Failed to call service {domain}.{service} on {entity_id}",
                status_code=status_code,
                response_body=response_body,
                exception_type=type(e).__name__,
            ) from e
        except requests.RequestException as e:
            raise HACallError(
                message=f"Failed to call service {domain}.{service} on {entity_id}",
                exception_type=type(e).__name__,
            ) from e

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
            raise HACallError(
                message=f"Invalid domain for select entity {entity_id}",
                exception_type="DomainValidationError",
            )
        return self.call_service(domain, "select_option", entity_id, {"option": option})

    def set_switch(self, entity_id: str, state: bool) -> bool:
        """Turn a switch on or off."""
        domain = self._get_safe_domain(entity_id, {"switch", "input_boolean"})
        if not domain:
            raise HACallError(
                message=f"Invalid domain for switch entity {entity_id}",
                exception_type="DomainValidationError",
            )
        service = "turn_on" if state else "turn_off"
        return self.call_service(domain, service, entity_id)

    def set_number(self, entity_id: str, value: float) -> bool:
        """Set a number entity to a specific value."""
        domain = self._get_safe_domain(entity_id, {"number", "input_number"})
        if not domain:
            raise HACallError(
                message=f"Invalid domain for number entity {entity_id}",
                exception_type="DomainValidationError",
            )
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

    Uses profile-driven architecture where each mode defines an ordered list
    of entity+value actions. The executor is a generic loop.

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

    def _resolve_entity_id(self, key: str) -> str | None:
        """
        Resolve entity key to actual HA entity ID.

        Resolution order:
        1. User override: executor.inverter.custom_entities[key]
        2. Standard config: executor.inverter[key]
        3. Profile default: entities[key].default_entity
        """
        if not self.profile:
            return None

        entity_def = self.profile.entities.get(key)
        if not entity_def:
            return None

        override = self.config.inverter.custom_entities.get(key)
        if override:
            return override

        standard = getattr(self.config.inverter, key, None)
        if standard:
            return standard

        return entity_def.default_entity

    def _resolve_value(self, value: str | int | float | bool, decision: ControllerDecision) -> Any:
        """
        Resolve dynamic template values from ControllerDecision.

        Templates are strings in the form {{field_name}} where field_name
        is a property on ControllerDecision.
        """
        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            field_name = value[2:-2]
            if not hasattr(decision, field_name):
                logger.error("Unknown template variable: %s", field_name)
                return value
            return getattr(decision, field_name)
        return value

    async def _write_entity(
        self,
        entity_id: str,
        value: Any,
        domain: str,
    ) -> bool:
        """
        Write value to HA entity using appropriate service call.

        Args:
            entity_id: The HA entity ID to write to
            value: The value to write
            domain: The HA domain (select, number, switch, input_number)

        Returns:
            True if successful
        """
        try:
            if domain in ("number", "input_number"):
                return self.ha.set_number(entity_id, float(value))
            elif domain == "select":
                return self.ha.set_select_option(entity_id, str(value))
            elif domain in ("switch", "input_boolean"):
                return self.ha.set_switch(entity_id, bool(value))
            else:
                logger.error("Unknown entity domain: %s", domain)
                return False
        except HACallError as e:
            logger.error("Failed to write to %s: %s", entity_id, e)
            return False

    def _values_match(self, current: str | None, target: Any) -> bool:
        """Check if current value matches target value."""
        if current is None:
            return False
        try:
            current_float = float(current)
            target_float = float(target)
            return abs(current_float - target_float) < 0.01
        except (ValueError, TypeError):
            if isinstance(target, bool):
                current_lower = str(current).strip().lower()
                if target and current_lower == "on":
                    return True
                if not target and current_lower == "off":
                    return True
            return str(current).strip().lower() == str(target).strip().lower()

    async def _verify_action(self, entity_id: str, expected: Any) -> tuple[Any, bool | None]:
        """Verify that an action was applied correctly."""
        state = self.ha.get_state_value(entity_id)
        if state is None:
            return None, None

        matches = self._values_match(state, expected)
        return state, matches

    async def execute(self, decision: ControllerDecision) -> list[ActionResult]:
        """
        Execute all actions from a controller decision using profile-driven approach.

        Args:
            decision: The controller's decision with mode_intent

        Returns:
            List of ActionResult for each action attempted
        """
        if not self.profile:
            logger.error("No profile loaded - cannot execute actions")
            return [
                ActionResult(
                    action_type="error",
                    success=False,
                    message="No inverter profile loaded",
                )
            ]

        mode_intent = decision.mode_intent

        try:
            mode_def = self.profile.get_mode(mode_intent)
        except Exception as e:
            logger.error("Failed to get mode '%s' from profile: %s", mode_intent, e)
            return [
                ActionResult(
                    action_type="error",
                    success=False,
                    message=f"Profile error: {e}",
                )
            ]

        logger.info(
            "Executing mode '%s' (%s) for profile '%s'",
            mode_intent,
            mode_def.description,
            self.profile.metadata.name,
        )

        results: list[ActionResult] = []

        for action in mode_def.actions:
            result = await self._execute_action(action, decision, mode_intent)
            results.append(result)

            if action.settle_ms and action.settle_ms > 0:
                logger.debug("Settle delay: %dms after %s", action.settle_ms, action.entity)
                await asyncio.sleep(action.settle_ms / 1000.0)

        if results:
            successful = sum(1 for r in results if r.success)
            logger.info(
                "Mode '%s' executed: %d/%d actions successful",
                mode_intent,
                successful,
                len(results),
            )

        return results

    async def _execute_action(
        self,
        action: ModeAction,
        decision: ControllerDecision,
        mode_intent: str,
    ) -> ActionResult:
        """Execute a single mode action."""
        start_time = time.time()

        if not self.profile:
            return ActionResult(
                action_type=action.entity,
                success=False,
                message="No profile loaded",
                requested_mode=mode_intent,
                applied_mode=mode_intent,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        entity_def = self.profile.entities.get(action.entity)
        if not entity_def:
            return ActionResult(
                action_type=action.entity,
                success=False,
                message=f"Entity '{action.entity}' not defined in profile",
                requested_mode=mode_intent,
                applied_mode=mode_intent,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        entity_id = self._resolve_entity_id(action.entity)

        if not entity_id:
            return ActionResult(
                action_type=action.entity,
                success=False,
                message=f"Entity '{action.entity}' not configured",
                requested_mode=mode_intent,
                applied_mode=mode_intent,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        resolved_value = self._resolve_value(action.value, decision)

        previous_value = self.ha.get_state_value(entity_id)

        if self._values_match(previous_value, resolved_value):
            return ActionResult(
                action_type=action.entity,
                success=True,
                message=f"Already at {resolved_value}",
                previous_value=previous_value,
                new_value=resolved_value,
                entity_id=entity_id,
                skipped=True,
                requested_mode=mode_intent,
                applied_mode=mode_intent,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        if self.shadow_mode:
            logger.info(
                "[SHADOW] Would set %s to %s (current: %s)",
                entity_id,
                resolved_value,
                previous_value,
            )
            return ActionResult(
                action_type=action.entity,
                success=True,
                message=f"[SHADOW] Would change {previous_value} → {resolved_value}",
                previous_value=previous_value,
                new_value=resolved_value,
                entity_id=entity_id,
                skipped=True,
                requested_mode=mode_intent,
                applied_mode=mode_intent,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        success = await self._write_entity(entity_id, resolved_value, entity_def.domain)

        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(
                entity_id, resolved_value
            )

        duration_ms = int((time.time() - start_time) * 1000)

        if success:
            self._maybe_notify(action.entity, f"Set {action.entity} to {resolved_value}")

        return ActionResult(
            action_type=action.entity,
            success=success,
            message=f"{previous_value} → {resolved_value}"
            if success
            else f"Failed to set {action.entity}",
            previous_value=previous_value,
            new_value=resolved_value,
            entity_id=entity_id,
            verified_value=verified_value,
            verification_success=verification_success,
            requested_mode=mode_intent,
            applied_mode=mode_intent,
            duration_ms=duration_ms,
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
                error_details=None,
            )

        if entity is None:
            return ActionResult(
                action_type="water_temp",
                success=False,
                message="Entity is None after validation",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
                error_details=None,
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
                error_details=None,
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
                error_details=None,
            )

        error_details = None
        try:
            success = self.ha.set_input_number(entity, float(target))  # type: ignore[arg-type]
        except HACallError as e:
            success = False
            error_details = str(e)
            logger.error("Failed to set water_temp: %s", error_details)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            v_val, v_ok = await self._verify_action(entity, target)  # type: ignore[arg-type]
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
                f"Changed {current_val}°C → {target}°C"
                if success
                else f"Failed: {error_details}"
                if error_details
                else "Failed to set water temp"
            ),
            previous_value=current_val,
            new_value=target,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
            error_details=error_details,
        )

    async def _set_max_export_power(self, watts: float) -> ActionResult | None:
        """Set max grid export power."""
        start = time.time()

        entity = self.config.inverter.grid_max_export_power

        # Check if profile supports grid export limit via entity registry
        if self.profile and "grid_max_export_power" not in self.profile.entities:
            logger.debug(
                "Skipping max_export_power action: profile '%s' does not define grid_max_export_power entity",
                self.profile.metadata.name,
            )
            return None  # Silent skip - no entry in execution history

        if not _is_entity_configured(entity):
            # Check if this entity is actually required by the profile
            is_required = True
            if self.profile and "grid_max_export_power" in self.profile.entities:
                is_required = self.profile.entities["grid_max_export_power"].required

            if not is_required:
                # Silent skip - not configured and not required
                return None  # Silent skip - no entry in execution history

            logger.debug("Skipping max_export_power action: entity not configured")
            return ActionResult(
                action_type="max_export_power",
                success=True,
                message="Export power entity not configured. Configure in Settings → System → HA Entities",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
                error_details=None,
            )

        # Check current value and apply write threshold to prevent EEPROM wear
        if entity is None:
            return ActionResult(
                action_type="max_export_power",
                success=False,
                message="Entity is None after validation",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
                error_details=None,
            )

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
                    error_details=None,
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
                error_details=None,
            )

        error_details = None
        try:
            success = self.ha.set_number(entity, watts)
        except HACallError as e:
            success = False
            error_details = str(e)
            logger.error("Failed to set max_export_power: %s", error_details)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(entity, watts)

        # 5. Handle Export Switch (F49)
        # If a switch is configured, turn it ON when setting a limit.
        # This ensures that inverter actually enforces the numeric value.
        switch_entity = self.config.inverter.grid_max_export_power_switch
        if success and _is_entity_configured(switch_entity) and switch_entity is not None:
            logger.info("Enabling export power limit switch: %s", switch_entity)
            try:
                self.ha.set_switch(switch_entity, True)
            except HACallError as e:
                logger.warning("Failed to enable export power limit switch: %s", str(e))

        duration = int((time.time() - start) * 1000)

        logger.info("Set max_export_power: %.0f W on %s (success=%s)", watts, entity, success)

        return ActionResult(
            action_type="max_export_power",
            success=success,
            message=f"Set to {watts} W"
            if success
            else f"Failed: {error_details}"
            if error_details
            else "Failed to set export power",
            previous_value=current_val,
            new_value=watts,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
            error_details=error_details,
        )

    async def set_ev_charger_switch(
        self, entity_id: str, turn_on: bool, charging_kw: float = 0.0
    ) -> ActionResult:
        """
        Control EV charger switch with shadow mode support.

        Args:
            entity_id: The HA switch entity ID for the EV charger
            turn_on: True to turn on, False to turn off
            charging_kw: Planned charging power in kW (for logging/notifications)

        Returns:
            ActionResult with details of the action
        """
        start = time.time()
        action_type = "ev_charge_start" if turn_on else "ev_charge_stop"
        action_label = "ON" if turn_on else "OFF"

        # Check current state
        current_state = self.ha.get_state_value(entity_id)
        is_currently_on = current_state == "on" if current_state else False

        # Idempotent skip
        if turn_on == is_currently_on:
            return ActionResult(
                action_type=action_type,
                success=True,
                message=f"EV charger already {action_label}",
                previous_value=current_state,
                new_value=turn_on,
                entity_id=entity_id,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
                error_details=None,
            )

        # Shadow mode check
        if self.shadow_mode:
            logger.info(
                "[SHADOW] EV Charger: Would turn %s %s (current: %s)",
                action_label,
                entity_id,
                current_state,
            )
            return ActionResult(
                action_type=action_type,
                success=True,
                message=f"[SHADOW] Would turn {action_label}",
                previous_value=current_state,
                new_value=turn_on,
                entity_id=entity_id,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
                error_details=None,
            )

        # Execute action
        error_details = None
        try:
            self.ha.set_switch(entity_id, turn_on)
            success = True
        except HACallError as e:
            success = False
            error_details = str(e)
            logger.error("Failed to control EV charger %s: %s", entity_id, error_details)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(
                entity_id, "on" if turn_on else "off"
            )

        duration = int((time.time() - start) * 1000)

        # Notification (via _maybe_notify)
        if turn_on:
            self._maybe_notify("ev_charge_start", f"EV charging started ({charging_kw:.1f} kW)")
        else:
            self._maybe_notify("ev_charge_stop", "EV charging stopped")

        return ActionResult(
            action_type=action_type,
            success=success,
            message=f"EV charger turned {action_label}"
            if success
            else f"Failed: {error_details}"
            if error_details
            else f"Failed to turn {action_label} EV charger",
            previous_value=current_state,
            new_value=turn_on,
            entity_id=entity_id,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
            error_details=error_details,
        )

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
