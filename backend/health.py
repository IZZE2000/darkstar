"""
Health Check System

Centralized health monitoring for Darkstar.
Validates HA connection, entity availability, config validity, and planner metrics via SQLite.
"""

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytz
import yaml

from backend.exceptions import PVForecastError

logger = logging.getLogger(__name__)

# REV F60: Forecast error tracking (like executor's recent_errors)
# Phase 8: Thread-safe access with lock
_forecast_errors: deque[dict[str, Any]] = deque(maxlen=10)
_forecast_status: str = "ok"  # "ok", "degraded", "error"
_forecast_lock: threading.Lock = threading.Lock()

# REV F65 Phase 5b: Load forecast status tracking
_load_forecast_status: str = "ok"  # "ok", "degraded"
_load_forecast_reason: str = ""  # "ml", "baseline", "demo", ""
_load_forecast_lock: threading.Lock = threading.Lock()


def record_forecast_error(error: Exception, context: dict[str, Any] | None = None) -> None:
    """Record a forecast error for health monitoring.

    Args:
        error: The exception that occurred
        context: Additional context about the forecast attempt
    """
    global _forecast_status

    error_entry: dict[str, Any] = {
        "timestamp": datetime.now(pytz.UTC).isoformat(),
        "type": type(error).__name__,
        "message": str(error),
        "context": context or {},
    }

    if isinstance(error, PVForecastError):
        error_entry["solar_arrays"] = getattr(error, "solar_arrays", 0)  # type: ignore[dict-item]
        error_entry["details"] = getattr(error, "details", {})  # type: ignore[dict-item]

    with _forecast_lock:
        _forecast_status = "error" if isinstance(error, PVForecastError) else "degraded"
        _forecast_errors.append(error_entry)

    logger.error("Forecast error recorded: %s", error_entry["message"])


def clear_forecast_errors() -> None:
    """Clear forecast errors (called after successful forecast)."""
    global _forecast_status
    with _forecast_lock:
        _forecast_errors.clear()
        _forecast_status = "ok"


def get_forecast_errors(limit: int = 5) -> list[dict[str, Any]]:
    """Get recent forecast errors (newest first)."""
    with _forecast_lock:
        return list(_forecast_errors)[-limit:]


def get_forecast_status() -> dict[str, Any]:
    """Get current forecast health status."""
    with _forecast_lock:
        return {
            "status": _forecast_status,
            "last_errors": list(_forecast_errors)[-5:],
            "error_count": len(_forecast_errors),
        }


def set_load_forecast_status(status: str, reason: str = "") -> None:
    """Set load forecast status for health monitoring.

    Args:
        status: "ok" or "degraded"
        reason: "ml" (ML models working), "baseline" (using baseline avg),
                "demo" (using demo data), "no_ml" (ML unavailable but data exists)
    """
    global _load_forecast_status, _load_forecast_reason
    with _load_forecast_lock:
        _load_forecast_status = status
        _load_forecast_reason = reason

    if status == "degraded":
        logger.warning(f"⚠️ Load forecast degraded: {reason}")


def get_load_forecast_status() -> dict[str, Any]:
    """Get current load forecast health status."""
    with _load_forecast_lock:
        return {
            "status": _load_forecast_status,
            "reason": _load_forecast_reason,
        }


def clear_load_forecast_status() -> None:
    """Clear load forecast degraded status (called after successful ML forecast)."""
    global _load_forecast_status, _load_forecast_reason
    with _load_forecast_lock:
        _load_forecast_status = "ok"
        _load_forecast_reason = ""


@dataclass
class HealthIssue:
    """A single health issue with guidance."""

    category: str  # "ha_connection", "entity", "config", "planner", "executor"
    severity: str  # "critical", "warning", "info"
    message: str  # User-friendly message
    guidance: str  # How to fix
    entity_id: str | None = None  # Specific entity involved (if applicable)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "guidance": self.guidance,
            "entity_id": self.entity_id,
        }


@dataclass
class HealthStatus:
    """Overall system health status."""

    healthy: bool
    issues: list[HealthIssue] = field(default_factory=list[HealthIssue])
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now(pytz.UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "issues": [issue.to_dict() for issue in self.issues],
            "checked_at": self.checked_at,
            "critical_count": len([i for i in self.issues if i.severity == "critical"]),
            "warning_count": len([i for i in self.issues if i.severity == "warning"]),
        }


class HealthChecker:
    """
    Comprehensive system health checker.

    Validates:
    - Home Assistant connection
    - Configured entity availability
    - Config file validity
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}
        self._secrets: dict[str, Any] = {}

    async def check_all(self) -> HealthStatus:
        """Run all health checks and return combined status."""
        issues: list[HealthIssue] = []

        # Load config first (needed for other checks)
        config_issues = self.check_config_validity()
        issues.extend(config_issues)

        # If config is valid, proceed with other checks
        if not any(i.category == "config" and i.severity == "critical" for i in issues):
            issues.extend(await self.check_ha_connection())

            # Only check entities if HA is connected
            if not any(i.category == "ha_connection" for i in issues):
                issues.extend(await self.check_entities())

        # Check executor health
        issues.extend(self.check_executor())

        # Check recorder health (REV // Complete Cost Reality Fix)
        issues.extend(self.check_recorder())

        # Check forecast health (REV F60)
        issues.extend(self.check_forecast())

        # Check load forecast health (REV F65 Phase 5c)
        issues.extend(self.check_load_forecast())

        # Determine overall health
        has_critical = any(i.severity == "critical" for i in issues)
        healthy = not has_critical

        return HealthStatus(healthy=healthy, issues=issues)

    def check_config_validity(self) -> list[HealthIssue]:
        """Validate config.yaml exists and has required structure."""
        issues: list[HealthIssue] = []

        # Load config
        try:
            with self.config_path.open(encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            issues.append(
                HealthIssue(
                    category="config",
                    severity="critical",
                    message="Configuration file not found",
                    guidance=(
                        f"Copy config.default.yaml to {self.config_path} "
                        "and configure your settings."
                    ),
                )
            )
            return issues
        except yaml.YAMLError as e:
            issues.append(
                HealthIssue(
                    category="config",
                    severity="critical",
                    message=f"Invalid YAML syntax in config file: {e}",
                    guidance=(
                        "Fix the YAML syntax error in config.yaml. "
                        "Check for incorrect indentation or special characters."
                    ),
                )
            )
            return issues

        # Load secrets
        try:
            with Path("secrets.yaml").open(encoding="utf-8") as f:
                self._secrets = yaml.safe_load(f) or {}
        except FileNotFoundError:
            issues.append(
                HealthIssue(
                    category="config",
                    severity="critical",
                    message="Secrets file not found",
                    guidance=(
                        "Create secrets.yaml with your Home Assistant URL and token. "
                        "See README for format."
                    ),
                )
            )
        except yaml.YAMLError as e:
            issues.append(
                HealthIssue(
                    category="config",
                    severity="critical",
                    message=f"Invalid YAML syntax in secrets file: {e}",
                    guidance="Fix the YAML syntax error in secrets.yaml.",
                )
            )

        # Validate required config sections
        issues.extend(self._validate_config_structure())

        return issues

    def _validate_config_structure(self) -> list[HealthIssue]:
        """Validate config has required sections and correct types."""
        issues: list[HealthIssue] = []

        if not self._config:
            return issues

        # Check input_sensors section exists
        if not self._config.get("input_sensors"):
            issues.append(
                HealthIssue(
                    category="config",
                    severity="warning",
                    message="No input_sensors configured",
                    guidance=(
                        "Add input_sensors section to config.yaml "
                        "to enable Home Assistant integration."
                    ),
                )
            )

        # Validate HA secrets
        if self._secrets:
            ha_config = self._secrets.get("home_assistant", {})
            if not ha_config.get("url"):
                issues.append(
                    HealthIssue(
                        category="config",
                        severity="critical",
                        message="Home Assistant URL not configured",
                        guidance=(
                            "Add home_assistant.url to secrets.yaml "
                            "(e.g., http://homeassistant.local:8123)"
                        ),
                    )
                )
            if not ha_config.get("token"):
                issues.append(
                    HealthIssue(
                        category="config",
                        severity="critical",
                        message="Home Assistant token not configured",
                        guidance=(
                            "Add home_assistant.token to secrets.yaml. "
                            "Generate a Long-Lived Access Token in HA."
                        ),
                    )
                )

        # REV LCL01: Validate system profile toggle consistency
        system_cfg = self._config.get("system", {})
        water_cfg = self._config.get("water_heating", {})
        battery_cfg = self._config.get("battery", {})

        # Battery misconfiguration = critical (breaks MILP solver)
        if system_cfg.get("has_battery", True):
            capacity = battery_cfg.get("capacity_kwh", 0)
            try:
                capacity = float(capacity) if capacity else 0.0
            except (ValueError, TypeError):
                capacity = 0.0
            if capacity <= 0:
                issues.append(
                    HealthIssue(
                        category="config",
                        severity="critical",
                        message="Battery enabled but capacity not configured",
                        guidance=(
                            "Set battery.capacity_kwh to your battery's capacity (e.g., 27.0), "
                            "or set system.has_battery to false."
                        ),
                    )
                )

        # Water heater misconfiguration = warning (feature disabled, not broken)
        if system_cfg.get("has_water_heater", True):
            power_kw = water_cfg.get("power_kw", 0)
            try:
                power_kw = float(power_kw) if power_kw else 0.0
            except (ValueError, TypeError):
                power_kw = 0.0
            if power_kw <= 0:
                issues.append(
                    HealthIssue(
                        category="config",
                        severity="warning",
                        message="Water heater enabled but power not configured",
                        guidance="Set water_heating.power_kw to your heater's power (e.g., 3.0), "
                        "or set system.has_water_heater to false.",
                    )
                )

        # Solar misconfiguration = warning (PV forecasts will be zero)
        if system_cfg.get("has_solar", True):
            solar_cfg = system_cfg.get("solar_array", {})
            kwp = solar_cfg.get("kwp", 0)
            try:
                kwp = float(kwp) if kwp else 0.0
            except (ValueError, TypeError):
                kwp = 0.0
            if kwp <= 0:
                issues.append(
                    HealthIssue(
                        category="config",
                        severity="warning",
                        message="Solar enabled but panel size not configured",
                        guidance="Set system.solar_array.kwp to your PV capacity (e.g., 10.0), "
                        "or set system.has_solar to false.",
                    )
                )

        # REV F61: Check for deprecated executor.ev_charger.penalty_levels
        executor_cfg = self._config.get("executor", {})
        ev_cfg = executor_cfg.get("ev_charger", {})
        if ev_cfg.get("penalty_levels"):
            issues.append(
                HealthIssue(
                    category="config",
                    severity="warning",
                    message="Deprecated setting: executor.ev_charger.penalty_levels",
                    guidance="This setting is deprecated and ignored. Use per-charger penalty levels in the EV Chargers section instead (accessible in Settings > Parameters).",
                )
            )

        return issues

    async def check_ha_connection(self) -> list[HealthIssue]:
        """Check if Home Assistant is reachable."""
        issues: list[HealthIssue] = []

        if not self._secrets:
            return issues  # Already reported in config check

        ha_config = self._secrets.get("home_assistant", {})
        url = ha_config.get("url", "").rstrip("/")
        token = ha_config.get("token", "")

        if not url or not token:
            return issues  # Already reported in config check

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{url}/api/",
                    headers={"Authorization": f"Bearer {token}"},
                )

            if response.status_code == 401:
                issues.append(
                    HealthIssue(
                        category="ha_connection",
                        severity="critical",
                        message="Home Assistant authentication failed",
                        guidance=(
                            "Your HA token is invalid or expired. "
                            "Generate a new Long-Lived Access Token in HA → Profile → Security."
                        ),
                    )
                )
            elif response.status_code != 200:
                issues.append(
                    HealthIssue(
                        category="ha_connection",
                        severity="critical",
                        message=f"Home Assistant returned error: HTTP {response.status_code}",
                        guidance="Check that your Home Assistant URL is correct and HA is running.",
                    )
                )

        except httpx.TimeoutException:
            issues.append(
                HealthIssue(
                    category="ha_connection",
                    severity="critical",
                    message="Home Assistant connection timed out",
                    guidance="Home Assistant is slow or unreachable. Check network connectivity.",
                )
            )
        except httpx.RequestError as e:
            issues.append(
                HealthIssue(
                    category="ha_connection",
                    severity="critical",
                    message=f"Cannot connect to Home Assistant: {e}",
                    guidance=f"Check that Home Assistant is running and reachable at {url}",
                )
            )
        except Exception as e:
            issues.append(
                HealthIssue(
                    category="ha_connection",
                    severity="critical",
                    message=f"Unexpected error connecting to HA: {e}",
                    guidance="Check your network and Home Assistant configuration.",
                )
            )

        return issues

    async def check_entities(self) -> list[HealthIssue]:
        """Check if configured entities exist in Home Assistant."""
        issues: list[HealthIssue] = []

        if not self._config or not self._secrets:
            return issues

        ha_config = self._secrets.get("home_assistant", {})
        url = ha_config.get("url", "").rstrip("/")
        token = ha_config.get("token", "")

        if not url or not token:
            return issues

        # Feature flags
        system_cfg = self._config.get("system", {})
        has_battery = system_cfg.get("has_battery", True)
        has_water_heater = system_cfg.get("has_water_heater", True)
        has_solar = system_cfg.get("has_solar", True)

        # Collect all entity IDs from config with feature context
        # (entity_id, config_key, required)
        entities_to_check: list[tuple[str, str, bool]] = []

        # Input sensors
        input_sensors = self._config.get("input_sensors", {})

        # Grid meter configuration
        grid_meter_type = system_cfg.get("grid_meter_type", "net")
        is_net_metering = grid_meter_type == "net"

        # Define which sensors are HARD requirements for core functionality
        # If False, a missing entity is a WARNING, not a CRITICAL error.
        # REV F65: Cumulative and today sensors are REQUIRED for forecasting/ML
        learning_cfg = self._config.get("learning", {})
        is_learning_enabled = learning_cfg.get("enable", False)

        sensor_requirements = {
            # Core energy sensors (CRITICAL)
            "battery_soc": has_battery,
            "load_power": True,
            "pv_power": has_solar,
            "grid_power": is_net_metering,
            "grid_import_power": not is_net_metering,
            "grid_export_power": not is_net_metering,
            # Cumulative sensors (REQUIRED for forecasting/ML - F65)
            "total_load_consumption": is_learning_enabled,
            "total_pv_production": is_learning_enabled,
            "total_grid_import": is_learning_enabled,
            "total_grid_export": is_learning_enabled,
            "total_battery_charge": is_learning_enabled,
            "total_battery_discharge": is_learning_enabled,
            # Today's sensors (REQUIRED for dashboard - F65)
            "today_load_consumption": True,
            "today_pv_production": True,
            "today_grid_import": True,
            "today_grid_export": True,
            "today_battery_charge": True,
            "today_battery_discharge": True,
            # Features (WARNING if missing but enabled)
            "water_power": has_water_heater,
            "water_heater_consumption": has_water_heater,
            "alarm_state": False,  # Optional
            "vacation_mode": False,  # Optional
        }

        # Sensors that should be completely skipped if not relevant for current meter type
        sensors_to_skip = []
        if is_net_metering:
            sensors_to_skip = ["grid_import_power", "grid_export_power"]
        else:
            sensors_to_skip = ["grid_power"]

        for key, entity_id in input_sensors.items():
            if key in sensors_to_skip:
                continue

            if entity_id and isinstance(entity_id, str):
                # Is this sensor tied to a hardware toggle?
                hardware_enabled = sensor_requirements.get(key, True)

                # Skip checking if hardware is disabled
                if hardware_enabled is False and key in ["battery_soc", "pv_power", "water_power"]:
                    continue

                entities_to_check.append((entity_id, f"input_sensors.{key}", hardware_enabled))

        # Executor entities
        executor = self._config.get("executor", {})
        if executor:
            # Inverter entities - Require has_battery
            if has_battery:
                inverter = executor.get("inverter", {})
                for key in [
                    "work_mode_entity",
                    "grid_charging_entity",
                    "max_charging_current_entity",
                    "max_discharging_current_entity",
                ]:
                    entity_id = inverter.get(key)
                    if entity_id:
                        entities_to_check.append((entity_id, f"executor.inverter.{key}", True))

                # Check soc_target_entity (requires battery)
                soc_target = executor.get("soc_target_entity")
                if soc_target:
                    entities_to_check.append((soc_target, "executor.soc_target_entity", True))

            # Water heater - Require has_water_heater
            if has_water_heater:
                water = executor.get("water_heater", {})
                target_entity = water.get("target_entity")
                if target_entity:
                    entities_to_check.append(
                        (target_entity, "executor.water_heater.target_entity", True)
                    )

            # General toggle entities - Always check
            for key in ["automation_toggle_entity"]:
                entity_id = executor.get(key)
                if entity_id:
                    entities_to_check.append((entity_id, f"executor.{key}", True))

        # NEW: Check for MISSING required sensors that aren't even in input_sensors
        for req_key, is_required in sensor_requirements.items():
            if is_required and req_key not in input_sensors:
                # Core sensor is missing from config entirely
                issues.append(
                    HealthIssue(
                        category="config",
                        severity="critical",
                        message=f"Missing required sensor: {req_key}",
                        guidance=(
                            f"Add '{req_key}' to input_sensors in config.yaml. "
                            f"This is required for {grid_meter_type} metering."
                        ),
                    )
                )

        # REV F65: Add forecasting-specific warnings when learning is enabled
        if is_learning_enabled:
            cumulative_sensors = [
                "total_load_consumption",
                "total_pv_production",
                "total_grid_import",
                "total_grid_export",
                "total_battery_charge",
                "total_battery_discharge",
            ]
            missing_cumulative = [
                s for s in cumulative_sensors if s not in input_sensors or not input_sensors.get(s)
            ]
            if missing_cumulative:
                issues.append(
                    HealthIssue(
                        category="config",
                        severity="warning",
                        message="Forecasting may use inaccurate fallback data",
                        guidance=(
                            f"Learning/forecasting is enabled but missing cumulative sensors: "
                            f"{', '.join(missing_cumulative)}. "
                            f"Forecasting will fall back to dummy sine wave profiles. "
                            f"Add these sensors to input_sensors for accurate forecasts."
                        ),
                    )
                )

        # REV F65: Add Today's Stats warning
        today_sensors = [
            "today_load_consumption",
            "today_pv_production",
            "today_grid_import",
            "today_grid_export",
            "today_battery_charge",
            "today_battery_discharge",
        ]
        missing_today = [
            s for s in today_sensors if s not in input_sensors or not input_sensors.get(s)
        ]
        if missing_today:
            issues.append(
                HealthIssue(
                    category="config",
                    severity="warning",
                    message="Dashboard 'Today's Stats' will show incomplete data",
                    guidance=(
                        f"Missing today's sensors: {', '.join(missing_today)}. "
                        f"The dashboard 'Today's Stats' card will not display correctly. "
                        f"Add these sensors to input_sensors for complete daily statistics."
                    ),
                )
            )

        # Check each entity
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for entity_id, config_key, is_required in entities_to_check:
                try:
                    response = await client.get(
                        f"{url}/api/states/{entity_id}",
                        headers=headers,
                    )

                    if response.status_code == 404:
                        # Downgrade severity if not a hard requirement
                        severity = "critical" if is_required else "warning"
                        issues.append(
                            HealthIssue(
                                category="entity",
                                severity=severity,
                                message=f"Entity not found: {entity_id}",
                                guidance=(
                                    f"Check that '{entity_id}' exists in Home Assistant. "
                                    f"Update {config_key} in config.yaml if renamed."
                                ),
                                entity_id=entity_id,
                            )
                        )
                    elif response.status_code == 200:
                        # Check for unavailable state
                        state_data = response.json()
                        state_value = state_data.get("state")
                        if state_value == "unavailable":
                            issues.append(
                                HealthIssue(
                                    category="entity",
                                    severity="warning",
                                    message=f"Entity unavailable: {entity_id}",
                                    guidance=(
                                        f"The entity '{entity_id}' exists but is "
                                        "currently unavailable. Check your device/integration."
                                    ),
                                    entity_id=entity_id,
                                )
                            )
                except httpx.RequestError:
                    # Connection issues already reported in check_ha_connection
                    pass

        return issues

    def check_executor(self) -> list[HealthIssue]:
        """Check executor health status."""
        issues: list[HealthIssue] = []

        try:
            from backend.api.routers.executor import get_executor_health  # type: ignore[import]

            # type: ignore
            executor_health: dict[str, Any] = get_executor_health()  # type: ignore[call]

            if not executor_health.get("is_healthy"):  # type: ignore
                if executor_health.get("should_be_running") and not executor_health.get(  # type: ignore
                    "is_running"
                ):
                    issues.append(
                        HealthIssue(
                            category="executor",
                            severity="critical",
                            message="Executor should be running but is not active",
                            guidance=(
                                "The executor is enabled in config but not running. "
                                "Check executor logs or restart the service."
                            ),
                        )
                    )
                elif executor_health.get("has_error"):  # type: ignore
                    error_msg: str = str(executor_health.get("error", "Unknown error"))  # type: ignore
                    issues.append(
                        HealthIssue(
                            category="executor",
                            severity="warning",
                            message=f"Executor last run failed: {error_msg}",
                            guidance=(
                                "Check executor logs for details. "
                                "The error may be transient or indicate a configuration issue."
                            ),
                        )
                    )
        except Exception as e:
            logger.debug("Could not check executor health: %s", e)
            # Don't add an issue - executor health check is optional

        return issues

    def check_recorder(self) -> list[HealthIssue]:
        """Check recorder service health."""
        issues: list[HealthIssue] = []

        try:
            from backend.services.recorder_service import recorder_service

            status = recorder_service.status
            if not status.running:
                issues.append(
                    HealthIssue(
                        category="recorder",
                        severity="critical",
                        message="Recorder service is not running",
                        guidance="The observation recorder is inactive. This prevents 'Real' data from appearing in charts. Check server logs.",
                    )
                )
            elif status.last_error:
                issues.append(
                    HealthIssue(
                        category="recorder",
                        severity="warning",
                        message=f"Recorder encountered an error: {status.last_error}",
                        guidance="Check recorder logs for recent failures. Some observations may be missing.",
                    )
                )

            # Check if last recording was too long ago (e.g., > 30 mins)
            if status.last_record_at:
                from datetime import UTC, datetime

                delta = datetime.now(UTC) - status.last_record_at
                if delta.total_seconds() > 1800:  # 30 minutes
                    issues.append(
                        HealthIssue(
                            category="recorder",
                            severity="warning",
                            message=f"Recorder has not saved data in {int(delta.total_seconds() / 60)} minutes",
                            guidance="The recorder appears to be stalled. Check server logs.",
                        )
                    )
        except Exception as e:
            logger.debug("Could not check recorder health: %s", e)

        return issues

    def check_forecast(self) -> list[HealthIssue]:
        """Check PV forecast health status."""
        issues: list[HealthIssue] = []

        forecast_info = get_forecast_status()
        status = forecast_info.get("status", "ok")

        if status == "error":
            # Get the most recent error
            recent_errors = forecast_info.get("last_errors", [])
            if recent_errors:
                latest = recent_errors[-1]
                error_msg = latest.get("message", "Unknown forecast error")

                issues.append(
                    HealthIssue(
                        category="forecast",
                        severity="critical",
                        message=f"PV Forecast Failed: {error_msg}",
                        guidance=(
                            "The PV forecast system is unable to generate accurate solar predictions. "
                            "Planning may be using outdated or invalid data. "
                            "Check your solar array configuration and Open-Meteo service availability."
                        ),
                    )
                )
        elif status == "degraded":
            issues.append(
                HealthIssue(
                    category="forecast",
                    severity="warning",
                    message="PV forecast experiencing issues",
                    guidance="Some forecast requests have failed but the system is still operational.",
                )
            )

        return issues

    def check_load_forecast(self) -> list[HealthIssue]:
        """Check Load forecast health status (REV F65 Phase 5c)."""
        issues: list[HealthIssue] = []

        load_info = get_load_forecast_status()
        status = load_info.get("status", "ok")
        reason = load_info.get("reason", "")

        if status == "degraded":
            if reason == "demo":
                issues.append(
                    HealthIssue(
                        category="forecast",
                        severity="warning",
                        message="Load forecast using demo data (0.5 kWh flat)",
                        guidance=(
                            "No historical load data available. The system is using a flat demo profile. "
                            "Configure 'total_load_consumption' sensor in input_sensors to enable accurate load forecasting."
                        ),
                    )
                )
            elif reason == "baseline":
                issues.append(
                    HealthIssue(
                        category="forecast",
                        severity="info",
                        message="Load forecast using baseline average (insufficient training data)",
                        guidance=(
                            "Not enough historical data to train ML models. The system is using baseline average (0.5 kWh/slot). "
                            "After 4+ days of data collection, statistical corrections will be applied. "
                            "After 14+ days, ML models will be trained for accurate predictions."
                        ),
                    )
                )
            elif reason == "no_ml":
                issues.append(
                    HealthIssue(
                        category="forecast",
                        severity="warning",
                        message="Load forecast ML models unavailable",
                        guidance=(
                            "Historical data exists but ML models are not trained. "
                            "Run the ML training pipeline to enable accurate load predictions. "
                            "Current forecast uses HA historical profile."
                        ),
                    )
                )

        return issues


async def get_health_status(config_path: str = "config.yaml") -> HealthStatus:
    """Convenience function to get current health status."""
    checker = HealthChecker(config_path)
    return await checker.check_all()
