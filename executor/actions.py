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
from .profiles import InverterProfile, WorkMode

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

    def _get_mode_def_for_value(self, mode_value: str) -> Any | None:
        """Get the WorkMode definition for a given mode value string.

        Args:
            mode_value: The mode value string (e.g., "Auto", "Charge from Grid")

        Returns:
            WorkMode object if found, None otherwise
        """
        if not self.profile:
            return None

        for attr in [
            "export",
            "zero_export",
            "self_consumption",
            "force_discharge",
            "charge_from_grid",
            "idle",
        ]:
            mode = getattr(self.profile.modes, attr, None)
            if mode and mode.value == mode_value:
                return mode
        return None

    async def execute(self, decision: ControllerDecision) -> list[ActionResult]:
        """
        Execute all actions from a controller decision.

        Args:
            decision: The controller's decision on what actions to take

        Returns:
            List of ActionResult for each action attempted
        """
        results: list[ActionResult] = []
        target_mode = decision.work_mode

        # 1. Set work mode (Rev O1)
        if self.config.has_battery:
            mode_results = await self._set_work_mode(
                target_mode, is_charging=decision.grid_charging
            )
            results.extend(mode_results)

        # Get mode definition for skip flag checking (REV F53 Phase 1)
        mode_def = self._get_mode_def_for_value(target_mode) if self.profile else None

        # Optimization: Identify if we should skip power limits based on mode (REV IP4)
        # We skip discharge/export limits in Charge and Hold/Idle modes to prevent conflict.
        is_charging = False
        is_idle = False
        if self.profile:
            if (
                self.profile.modes.charge_from_grid
                and target_mode == self.profile.modes.charge_from_grid.value
            ):
                is_charging = True
            if self.profile.modes.idle and target_mode == self.profile.modes.idle.value:
                is_idle = True

        # 2. Set grid charging (Rev O1)
        # Skip if profile uses mode-based charging (REV F53 Phase 1)
        if self.config.has_battery:
            skip_grid_charging = (
                self.profile and not self.profile.capabilities.separate_grid_charging_switch
            )
            if skip_grid_charging:
                logger.debug(
                    "Skipping grid_charging action: profile '%s' uses mode-based charging",
                    self.profile.metadata.name,
                )
            else:
                result = await self._set_grid_charging(decision.grid_charging)
                if result is not None:
                    results.append(result)

        # 3. Set charge limit (Rev O1 + E3)
        if self.config.has_battery and decision.write_charge_current:
            result = await self._set_charge_limit(decision.charge_value, decision.control_unit)
            results.append(result)

        # 4. Set discharge limit (Rev O1 + E3 + Rev F54 Phase 4)
        # Skip if in Charge or Idle mode (Generic optimization REV IP4)
        # OR if profile mode has skip_discharge_limit flag (REV F53 Phase 1)
        if self.config.has_battery and decision.write_discharge_current:
            skip_discharge = is_charging or is_idle
            if not skip_discharge and mode_def and mode_def.skip_discharge_limit:
                skip_discharge = True
                logger.debug(
                    "Skipping discharge_limit action: mode '%s' has skip_discharge_limit=true",
                    target_mode,
                )
            if skip_discharge:
                logger.debug("Skipping discharge_limit action: mode is %s", target_mode)
            else:
                result = await self._set_discharge_limit(
                    decision.discharge_value, decision.control_unit
                )
                if result is not None:
                    results.append(result)

        # 5. Set SoC target (Rev O1 + Rev F54 Phase 3)
        if self.config.has_battery:
            result = await self._set_soc_target(decision.soc_target)
            if result is not None:
                results.append(result)

        # 6. Set water heater target (Rev O1)
        if self.config.has_water_heater:
            result = await self.set_water_temp(decision.water_temp)
            results.append(result)

        # 7. Set max export power (Bug fix #1 + Rev F54 Phase 5)
        # Skip if in Charge or Idle mode (Generic optimization REV IP4)
        # OR if profile mode has skip_export_power flag (REV F53 Phase 1)
        if self.config.has_battery:
            skip_export = is_charging or is_idle
            if not skip_export and mode_def and mode_def.skip_export_power:
                skip_export = True
                logger.debug(
                    "Skipping max_export_power action: mode '%s' has skip_export_power=true",
                    target_mode,
                )
            if skip_export:
                logger.debug("Skipping max_export_power action: mode is %s", target_mode)
            else:
                result = await self._set_max_export_power(decision.export_power_w)
                if result is not None:
                    results.append(result)

        return results

    async def _apply_composite_entities(
        self,
        target_mode: str,
        is_charging: bool,
        mode_changed: bool,
    ) -> list[ActionResult]:
        """Apply composite mode entities for inverters that require multiple entity changes.

        This is called even when work_mode hasn't changed, to support inverters like Sungrow
        where multiple logical modes share the same work_mode value (e.g., "Forced mode")
        but have different composite entity requirements.

        Args:
            target_mode: The target work mode string value
            is_charging: Whether we're in a charging intent context
            mode_changed: Whether the primary work_mode entity was actually changed

        Returns:
            List of ActionResult objects for composite entity operations
        """
        results: list[ActionResult] = []

        if not self.profile:
            return results

        # unique string value -> mode object lookup
        mode_obj = None

        # Rev F52 Phase 4: Ambiguous Mode Resolution
        # Determine which mode object matches the target string AND intent
        # Priority:
        # 1. If is_charging=True, check charge_from_grid first
        # 2. Check all other modes

        # Helper to find matching mode in a list
        def find_mode(mode_list: list[WorkMode | None]) -> WorkMode | None:
            for m in mode_list:
                if m and m.value == target_mode:
                    return m
            return None

        if is_charging:
            mode_obj = find_mode([self.profile.modes.charge_from_grid])

        if not mode_obj:
            # Standard lookup order (Export/Zero/Self/ForceDischarge/Idle)
            # Note: We exclude charge_from_grid here if is_charging is False to avoid accidental match
            # if it shares a value with another mode (e.g. Sungrow Forced Mode)
            candidates = [
                self.profile.modes.export,
                self.profile.modes.zero_export,
                self.profile.modes.self_consumption,
                self.profile.modes.force_discharge,
                self.profile.modes.idle,
            ]
            # Only include charge_from_grid as fallback if we haven't checked it yet (unlikely path)
            if not is_charging:
                # If we are NOT charging, we explicitly prefer Export/ForceDischarge over GridCharge
                pass
            else:
                candidates.append(self.profile.modes.charge_from_grid)

            mode_obj = find_mode(candidates)

        if mode_obj and mode_obj.set_entities:
            logger.debug(
                "Applying composite mode entities for %s (Intent: Charging=%s, ModeChanged=%s)",
                target_mode,
                is_charging,
                mode_changed,
            )
            for key, val in mode_obj.set_entities.items():
                # Look up entity ID from custom_entities config
                # Fallback to standard entities checks if needed, but custom_entities is preferred for profile-specifics
                aux_start = time.time()
                entity_id = self.config.inverter.custom_entities.get(key)
                if not _is_entity_configured(entity_id):
                    logger.error(
                        "Profile requires setting '%s' to '%s', but entity is not configured (add to executor.inverter)",
                        key,
                        val,
                    )
                    results.append(
                        ActionResult(
                            action_type="composite_mode",
                            success=False,
                            message=f"Entity '{key}' not configured in executor.inverter",
                            previous_value=None,
                            new_value=val,
                            entity_id=None,
                            error_details=f"Missing composite entity mapping for '{key}'",
                            duration_ms=int((time.time() - aux_start) * 1000),
                        )
                    )
                    continue

                # Capture previous state
                aux_previous = self.ha.get_state_value(entity_id)

                # Idempotent skip
                # Idempotent skip: only skip if value matches AND (mode didn't change and intent didn't change)
                # This ensures we re-assert the composite values on mode transitions even if same.
                if str(aux_previous) == str(val) and not mode_changed:
                    results.append(
                        ActionResult(
                            action_type="composite_mode",
                            success=True,
                            message=f"{key} already at {val}",
                            previous_value=aux_previous,
                            new_value=val,
                            entity_id=entity_id,
                            skipped=True,
                            duration_ms=int((time.time() - aux_start) * 1000),
                            error_details=None,
                        )
                    )
                    continue

                if self.shadow_mode:
                    logger.info(
                        "[SHADOW] Composite Mode: Would set %s to %s (current: %s)",
                        entity_id,
                        val,
                        aux_previous,
                    )
                    results.append(
                        ActionResult(
                            action_type="composite_mode",
                            success=True,
                            message=f"[SHADOW] Would change {aux_previous} → {val}",
                            previous_value=aux_previous,
                            new_value=val,
                            entity_id=entity_id,
                            skipped=True,
                            duration_ms=int((time.time() - aux_start) * 1000),
                            error_details=None,
                        )
                    )
                    continue

                logger.info("Composite Mode: Setting %s to %s", entity_id, val)
                aux_success = False
                aux_error_details = None
                try:
                    if isinstance(val, int | float):
                        aux_success = self.ha.set_number(entity_id, float(val))
                    elif isinstance(val, str):
                        aux_success = self.ha.set_select_option(entity_id, val)
                    elif isinstance(val, bool):
                        aux_success = self.ha.set_switch(entity_id, val)
                except HACallError as e:
                    aux_success = False
                    aux_error_details = str(e)
                    logger.error(
                        "Composite mode entity %s failed: %s", entity_id, aux_error_details
                    )

                # Verification
                aux_verified_value = None
                aux_verification_success = None
                if aux_success:
                    aux_verified_value, aux_verification_success = await self._verify_action(
                        entity_id, val
                    )

                results.append(
                    ActionResult(
                        action_type="composite_mode",
                        success=aux_success,
                        message=f"{key}: {aux_previous} → {val}"
                        if aux_success
                        else f"{key} failed: {aux_error_details}"
                        if aux_error_details
                        else f"Failed to set {key}",
                        previous_value=aux_previous,
                        new_value=val,
                        entity_id=entity_id,
                        verified_value=aux_verified_value,
                        verification_success=aux_verification_success,
                        duration_ms=int((time.time() - aux_start) * 1000),
                        error_details=aux_error_details,
                    )
                )

        return results

    async def _set_work_mode(
        self, target_mode: str, is_charging: bool = False
    ) -> list[ActionResult]:
        """Set inverter work mode if different from current."""
        start = time.time()
        results: list[ActionResult] = []
        entity = self.config.inverter.work_mode_entity

        if not _is_entity_configured(entity):
            logger.debug("Skipping work_mode action: entity not configured")
            results.append(
                ActionResult(
                    action_type="work_mode",
                    success=True,
                    message="Work mode entity not configured. Configure in Settings → System → HA Entities",
                    skipped=True,
                    duration_ms=int((time.time() - start) * 1000),
                    error_details=None,
                )
            )
            return results

        # Get current state
        current = self.ha.get_state_value(entity)

        # Track if primary work_mode entity actually changed
        mode_changed = current != target_mode
        success = True
        error_details = None

        if mode_changed:
            if self.shadow_mode:
                logger.info(
                    "[SHADOW] Would set work_mode to %s (current: %s)", target_mode, current
                )
                success = True
            else:
                # Apply work mode change
                try:
                    success = self.ha.set_select_option(entity, target_mode)
                except HACallError as e:
                    success = False
                    error_details = str(e)
                    logger.error("Failed to set work mode: %s", error_details)
        else:
            logger.debug("Work mode already at target: %s", target_mode)

        # Handle composite mode entities (Rev IP2 + Rev F54 Phase 1)
        # Some inverters (e.g. Sungrow) require setting multiple entities for a single mode change.
        # CRITICAL: Process composite entities EVEN when work_mode hasn't changed, because
        # inverters like Sungrow use the same work_mode value for multiple logical modes
        # (e.g., "Forced mode" for both export and charge), differing only in composite entities.
        if self.profile:
            composite_results = await self._apply_composite_entities(
                target_mode, is_charging, mode_changed
            )
            results.extend(composite_results)

        # Mode settling delay (Rev IP1 Phase 3)
        if success and self.profile and self.profile.behavior.requires_mode_settling:
            settle_ms = self.profile.behavior.mode_settling_ms
            logger.debug(
                "Applying mode settling delay: %dms for %s",
                settle_ms,
                self.profile.metadata.name,
            )
            await asyncio.sleep(settle_ms / 1000.0)

        # Verification for primary mode
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(entity, target_mode)

        duration = int((time.time() - start) * 1000)

        if success and mode_changed:
            self._maybe_notify("work_mode", f"Work mode changed to {target_mode}")

        primary_msg = ""
        if success:
            if not mode_changed:
                primary_msg = f"Already at {target_mode}"
            elif self.shadow_mode:
                primary_msg = f"[SHADOW] Would change {current} → {target_mode}"
            else:
                primary_msg = f"Changed {current} → {target_mode}"
        else:
            primary_msg = f"Failed: {error_details}" if error_details else "Failed to set work mode"

        results.insert(
            0,
            ActionResult(
                action_type="work_mode",
                success=success,
                message=primary_msg,
                previous_value=current,
                new_value=target_mode,
                entity_id=entity,
                verified_value=verified_value,
                verification_success=verification_success,
                skipped=(not mode_changed)
                or self.shadow_mode,  # Skip if already at target or shadow mode
                duration_ms=duration,
                error_details=error_details,
            ),
        )

        return results

    async def _set_grid_charging(self, enabled: bool) -> ActionResult | None:
        """Set grid charging switch."""
        start = time.time()
        entity = self.config.inverter.grid_charging_entity
        target = "on" if enabled else "off"

        # Handle grid charging via profile logic if available (Rev ARC13 Phase 4 + Rev F54 Phase 2)
        if self.profile:
            if not self.profile.capabilities.grid_charging_control:
                logger.debug(
                    "Skipping grid_charging action: profile '%s' does not support grid charging control",
                    self.profile.metadata.name,
                )
                return None  # Silent skip - no entry in execution history
            if not self.profile.capabilities.separate_grid_charging_switch:
                logger.debug(
                    "Skipping grid_charging switch: profile '%s' uses mode-based charging",
                    self.profile.metadata.name,
                )
                return None  # Silent skip - no entry in execution history

        if not _is_entity_configured(entity):
            logger.debug("Skipping grid_charging action: entity not configured")
            return ActionResult(
                action_type="grid_charging",
                success=True,
                message="Grid charging entity not configured. Configure in Settings → System → HA Entities",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
                error_details=None,
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
                error_details=None,
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
                error_details=None,
            )

        # Handle grid charging via profile logic if available
        error_details = None
        try:
            success = self.ha.set_switch(entity, enabled)
        except HACallError as e:
            success = False
            error_details = str(e)
            logger.error("Failed to set grid charging: %s", error_details)

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
            message=f"Changed {current} → {target}"
            if success
            else f"Failed: {error_details}"
            if error_details
            else "Failed to set grid charging",
            previous_value=current,
            new_value=target,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
            error_details=error_details,
        )

    async def _set_charge_limit(self, value: float, unit: str) -> ActionResult:
        """Set max charging limit (Amps or Watts)."""
        start = time.time()

        # Generic Split Charging Support (REV IP4)
        # If we are in 'charge_from_grid' mode and a specific grid entity is defined, use it.
        entity = None
        current_mode = self.ha.get_state_value(self.config.inverter.work_mode_entity)
        is_grid_mode = (
            self.profile
            and self.profile.modes.charge_from_grid
            and current_mode == self.profile.modes.charge_from_grid.value
        )

        if is_grid_mode:
            # Use standardized grid_charge_power (Rev IP4)
            entity = self.config.inverter.grid_charge_power
            if _is_entity_configured(entity):
                logger.debug("Using dedicated grid_charge_power: %s", entity)
            else:
                entity = None  # Fall back to standard logic

        if not entity:
            if unit == "W":
                entity = self.config.inverter.max_charging_power_entity
            else:
                entity = self.config.inverter.max_charging_current_entity

        unit_label = unit

        if not _is_entity_configured(entity):
            logger.debug("Skipping charge_limit action: entity not configured for unit %s", unit)
            return ActionResult(
                action_type="charge_limit",
                success=True,
                message=f"Max charge {unit_label} entity not configured. Configure in Settings.",
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
                error_details=None,
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
                error_details=None,
            )

        error_details = None
        try:
            success = self.ha.set_number(entity, value)
        except HACallError as e:
            success = False
            error_details = str(e)
            logger.error("Failed to set charge limit: %s", error_details)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(entity, value)

        # Sync to forced power entity if applicable (Rev IP2 Phase 3 + IP5)
        # Check for 'forced_power' (new) or 'forced_power_entity' (legacy)
        forced_entity_id = self.config.inverter.custom_entities.get(
            "forced_power"
        ) or self.config.inverter.custom_entities.get("forced_power_entity")

        if success and self.profile and _is_entity_configured(forced_entity_id):
            current_mode_val = self.ha.get_state_value(self.config.inverter.work_mode_entity)
            if (
                self.profile.modes.charge_from_grid
                and current_mode_val == self.profile.modes.charge_from_grid.value
            ):
                logger.info("Syncing charge limit to forced power entity: %s", forced_entity_id)
                self.ha.set_number(forced_entity_id, value)

        duration = int((time.time() - start) * 1000)
        logger.info("Set charge_limit result: success=%s, duration=%dms", success, duration)

        return ActionResult(
            action_type="charge_limit",
            success=success,
            message=f"Set to {value} {unit_label}"
            if success
            else f"Failed: {error_details}"
            if error_details
            else "Failed to set charge limit",
            new_value=value,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
            error_details=error_details,
        )

    async def _set_discharge_limit(self, value: float, unit: str) -> ActionResult | None:
        """Set max discharging limit (Amps or Watts)."""
        start = time.time()

        # 1. Profile-aware Skip Logic (Rev IP11 + Rev F54 Phase 4)
        # If the current mode handles discharge limits internally, we skip the write.
        if self.profile:
            current_mode = self.ha.get_state_value(self.config.inverter.work_mode_entity)
            # Find the mode definition matching current HA state
            mode_def = None
            for attr in [
                "export",
                "zero_export",
                "self_consumption",
                "force_discharge",
                "charge_from_grid",
                "idle",
            ]:
                m = getattr(self.profile.modes, attr, None)
                if m and m.value == current_mode:
                    mode_def = m
                    break

            if mode_def and mode_def.skip_discharge_limit:
                logger.info(
                    "Skipping discharge limit write: mode '%s' manages limits internally (Profile: %s)",
                    current_mode,
                    self.profile.metadata.name,
                )
                return None  # Silent skip - no entry in execution history

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
                error_details=None,
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
                error_details=None,
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
                error_details=f"Safety guard: {value}A exceeds 500A limit",
            )

        error_details = None
        try:
            success = self.ha.set_number(entity, value)
        except HACallError as e:
            success = False
            error_details = str(e)
            logger.error("Failed to set discharge limit: %s", error_details)

        # Verification
        verified_value = None
        verification_success = None
        if success:
            verified_value, verification_success = await self._verify_action(entity, value)

        # Sync to forced power entity if applicable (Rev IP2 Phase 3 + IP5)
        # Check for 'forced_power' (new) or 'forced_power_entity' (legacy)
        forced_entity_id = self.config.inverter.custom_entities.get(
            "forced_power"
        ) or self.config.inverter.custom_entities.get("forced_power_entity")

        if success and self.profile and _is_entity_configured(forced_entity_id):
            current_mode_val = self.ha.get_state_value(self.config.inverter.work_mode_entity)
            is_forced = False
            if (
                self.profile.modes.export and current_mode_val == self.profile.modes.export.value
            ) or (
                self.profile.modes.force_discharge
                and current_mode_val == self.profile.modes.force_discharge.value
            ):
                is_forced = True

            if is_forced:
                logger.info("Syncing discharge limit to forced power entity: %s", forced_entity_id)
                self.ha.set_number(forced_entity_id, value)

        duration = int((time.time() - start) * 1000)
        logger.info("Set discharge_limit result: success=%s, duration=%dms", success, duration)

        return ActionResult(
            action_type="discharge_limit",
            success=success,
            message=f"Set to {value} {unit_label}"
            if success
            else f"Failed: {error_details}"
            if error_details
            else "Failed to set discharge limit",
            new_value=value,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
            error_details=error_details,
        )

    async def _set_soc_target(self, target: int) -> ActionResult | None:
        """Set SoC target."""
        start = time.time()
        entity = self.config.inverter.soc_target_entity

        # Handle profile without SoC target support (Rev F54 Phase 3)
        if self.profile and not self.profile.capabilities.supports_soc_target:
            logger.debug(
                "Skipping soc_target action: profile '%s' does not support SoC target control",
                self.profile.metadata.name,
            )
            return None  # Silent skip - no entry in execution history

        if not _is_entity_configured(entity):
            # Check if this entity is actually required by the profile
            is_required = True
            if self.profile:
                # If we have a profile, check if soc_target_entity is in its required list
                is_required = "soc_target_entity" in self.profile.entities.required

            if not is_required:
                # Silent skip - not configured and not required
                return None  # Silent skip - no entry in execution history

            logger.debug("Skipping soc_target action: entity not configured")
            return ActionResult(
                action_type="soc_target",
                success=True,
                message="SoC target entity not configured. Configure in Settings → System → HA Entities",
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
                action_type="soc_target",
                success=True,
                message=f"Already at {target}%",
                previous_value=current_val,
                new_value=target,
                entity_id=entity,
                skipped=True,
                duration_ms=int((time.time() - start) * 1000),
                error_details=None,
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
                error_details=None,
            )

        error_details = None
        try:
            success = self.ha.set_input_number(entity, float(target))
        except HACallError as e:
            success = False
            error_details = str(e)
            logger.error("Failed to set soc_target: %s", error_details)

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
                f"Changed {current_val}% → {target}%"
                if success
                else f"Failed: {error_details}"
                if error_details
                else "Failed to set SoC target"
            ),
            previous_value=current_val,
            new_value=target,
            entity_id=entity,
            verified_value=verified_value,
            verification_success=verification_success,
            duration_ms=duration,
            error_details=error_details,
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
            success = self.ha.set_input_number(entity, float(target))
        except HACallError as e:
            success = False
            error_details = str(e)
            logger.error("Failed to set water_temp: %s", error_details)

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
        """Set max grid export power (Bug Fix #1)."""
        start = time.time()

        # Profile-aware Skip Logic (Rev F52 Phase 6 + Rev F54 Phase 5)
        # If the current mode handles export limits internally, we skip the write.
        if self.profile:
            current_mode = self.ha.get_state_value(self.config.inverter.work_mode_entity)
            # Find the mode definition matching current HA state
            mode_def = None
            for attr in [
                "export",
                "zero_export",
                "self_consumption",
                "force_discharge",
                "charge_from_grid",
                "idle",
            ]:
                m = getattr(self.profile.modes, attr, None)
                if m and m.value == current_mode:
                    mode_def = m
                    break

            if mode_def and mode_def.skip_export_power:
                logger.info(
                    "Skipping export power write: mode '%s' manages limits internally (Profile: %s)",
                    current_mode,
                    self.profile.metadata.name,
                )
                return None  # Silent skip - no entry in execution history

        entity = self.config.inverter.grid_max_export_power_entity

        if self.profile and not self.profile.capabilities.supports_grid_export_limit:
            logger.debug(
                "Skipping max_export_power action: profile '%s' does not support grid export limit control",
                self.profile.metadata.name,
            )
            return None  # Silent skip - no entry in execution history

        if not _is_entity_configured(entity):
            # Check if this entity is actually required by the profile
            is_required = True
            if self.profile:
                is_required = "grid_max_export_power_entity" in self.profile.entities.required

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
        if success and _is_entity_configured(switch_entity):
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
