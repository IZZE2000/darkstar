import json
import logging
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import pytz
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.deps import get_learning_store
from backend.learning.store import LearningStore
from inputs import (
    get_ha_entity_state,
    load_home_assistant_config,
    load_yaml,
    make_ha_headers,
)

logger = logging.getLogger("darkstar.api.services")

router_ha = APIRouter(prefix="/api/ha", tags=["ha"])
router_services = APIRouter(prefix="/api", tags=["services"])


# --- Helper ---
async def _fetch_ha_history_avg(entity_id: str, hours: int) -> float:
    """Fetch history from HA and calculate time-weighted average."""
    if not entity_id:
        return 0.0

    ha_config = load_home_assistant_config()
    url = ha_config.get("url")
    token = ha_config.get("token")
    if not url or not token:
        return 0.0

    headers = make_ha_headers(token)

    end_time = datetime.now(pytz.UTC)
    start_time = end_time - timedelta(hours=hours)

    # HA History API
    api_url = f"{url.rstrip('/')}/api/history/period/{start_time.isoformat()}"
    params = {
        "filter_entity_id": entity_id,
        "end_time": end_time.isoformat(),
        "significant_changes_only": False,
        "minimal_response": False,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(api_url, headers=headers, params=params)
            if resp.status_code != 200:
                return 0.0

            data = resp.json()
        if not data or not data[0]:
            return 0.0

        # Calculate Average
        states = data[0]
        total_weighted_sum = 0.0
        total_duration_sec = 0.0

        prev_time = start_time
        prev_val = 0.0

        # Initial value from first state? Or fetch state at start_time?
        # Simplified: Use first state's value as starting point
        try:
            prev_val = float(states[0]["state"])
            prev_time = datetime.fromisoformat(states[0]["last_changed"])
        except Exception:
            pass

        for s in states:
            try:
                curr_time = datetime.fromisoformat(s["last_changed"])
                val = float(s["state"])

                # Duration since last change
                duration = (curr_time - prev_time).total_seconds()
                if duration > 0:
                    total_weighted_sum += prev_val * duration
                    total_duration_sec += duration

                prev_time = curr_time
                prev_val = val
            except Exception:
                continue

        # Add remainder until now
        duration = (end_time - prev_time).total_seconds()
        if duration > 0:
            total_weighted_sum += prev_val * duration
            total_duration_sec += duration

        if total_duration_sec == 0:
            return 0.0

        return round(total_weighted_sum / total_duration_sec, 2)

    except Exception as e:
        logger.warning(f"Error fetching HA history for {entity_id}: {e}")
        return 0.0


@router_ha.get(
    "/entity/{entity_id}",
    summary="Get HA Entity",
    description="Returns the state of a specific Home Assistant entity.",
)
async def get_ha_entity(entity_id: str) -> dict[str, Any]:
    state = await get_ha_entity_state(entity_id)
    if not state:
        return {
            "entity_id": entity_id,
            "state": "unknown",
            "attributes": {"friendly_name": "Offline/Missing"},
            "last_changed": None,
        }
    return state


@router_ha.get(
    "/average",
    summary="Get Entity Average",
    description="Calculate average value for an entity over the last N hours.",
)
async def get_ha_average(entity_id: str | None = None, hours: int = 24) -> dict[str, Any]:
    """Calculate average value for an entity over the last N hours."""
    from backend.core.cache import cache
    from inputs import get_load_profile_from_ha, load_yaml

    # Check cache first
    cache_key = f"ha_average:{entity_id}:{hours}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    if not entity_id:
        # Default to load power sensor
        config = load_yaml("config.yaml")
        sensors: dict[str, Any] = config.get("input_sensors", {})
        entity_id = cast("str | None", sensors.get("load_power"))

    if not entity_id:
        return {"average": 0.0, "entity_id": None, "hours": hours}

    avg_val = await _fetch_ha_history_avg(entity_id, hours)

    # Fallback to static profile if history unavailable/zero
    if avg_val == 0.0:
        try:
            config = load_yaml("config.yaml")
            profile = await get_load_profile_from_ha(config)
            if profile:
                avg_val = sum(profile) / len(profile)
        except Exception as e:
            logger.warning(f"Fallback average calc failed: {e}")

    # Calculate daily_kwh estimate (avg * 24h)
    # Note: avg_val is usually Watts.
    # HA sensors are usually W. If fetch_ha_history_avg returns W, then /1000 is correct for kWh.
    # If it returns kW, then *24 is correct.
    # Let's assume the sensor is W (standard HA).
    # But wait, fetch_ha_history_avg just returns value.
    # The frontend expects 'average_load_kw'.
    # If standard sensor is W, we should divide by 1000 for kw.

    # Let's ensure we return kW.
    # If value > 100 (likely Watts), divide by 1000.
    # If value < 50 (likely kW), keep as is. Simple heuristic or just be explicit?
    # Let's trust the value is W from typical HA power sensors, so convert to kW.

    val_kw = avg_val / 1000.0 if avg_val > 100 else avg_val

    result = {
        "average_load_kw": round(val_kw, 3),
        "daily_kwh": round(val_kw * 24, 2),
        "entity_id": entity_id,
        "hours": hours,
    }

    # Cache for 60 seconds
    await cache.set(cache_key, result, ttl_seconds=60.0)

    return result


@router_ha.get(
    "/entities",
    summary="List HA Entities",
    description="List available Home Assistant entities.",
)
async def get_ha_entities() -> dict[str, list[dict[str, str]]]:
    """List available HA entities."""
    # Fetch from HA states
    config = load_home_assistant_config()
    url = config.get("url")
    token = config.get("token")
    if not url or not token:
        return {"entities": []}

    try:
        headers = make_ha_headers(token)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url.rstrip('/')}/api/states", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            # Filter and format
            entities: list[dict[str, str]] = []
            for s in data:
                eid = str(s.get("entity_id", ""))
                if eid.startswith(
                    (
                        "sensor.",
                        "binary_sensor.",
                        "input_boolean.",
                        "switch.",
                        "input_number.",
                        "input_select.",
                        "select.",
                        "number.",
                        "alarm_control_panel.",
                    )
                ):
                    entities.append(
                        {
                            "entity_id": eid,
                            "friendly_name": str(s.get("attributes", {}).get("friendly_name", eid)),
                            "domain": eid.split(".")[0],
                        }
                    )
            return {"entities": entities}
    except Exception as e:
        logger.warning(f"Error fetching HA entities: {e}")

    return {"entities": []}


@router_services.get(
    "/performance/data",
    summary="Get Performance Data",
    description="Get performance metrics for the Aurora card.",
)
async def get_performance_data(days: int = 7) -> dict[str, Any]:
    """Get performance metrics for Aurora card."""
    try:
        from backend.learning import get_learning_engine

        engine = get_learning_engine()
        if hasattr(engine, "get_performance_series"):
            # get_performance_series is now async
            data = await engine.get_performance_series(days_back=days)
            return cast("dict[str, Any]", data)
        else:
            return {
                "soc_series": [],
                "cost_series": [],
                "mae_pv_aurora": None,
                "mae_pv_baseline": None,
                "mae_load_aurora": None,
                "mae_load_baseline": None,
            }
    except Exception as e:
        return {
            "soc_series": [],
            "cost_series": [],
            "mae_pv_aurora": None,
            "mae_pv_baseline": None,
            "mae_load_aurora": None,
            "mae_load_baseline": None,
            "error": str(e),
        }


@router_ha.get(
    "/water_today",
    summary="[DEPRECATED] Get Water Heating Energy",
    description="DEPRECATED: Use /api/services/energy/today instead. Returns water_heating_kwh field.",
)
async def get_water_today() -> dict[str, Any]:
    """DEPRECATED: Get today's water heating energy from unified energy endpoint.

    This endpoint is deprecated and will be removed in a future version.
    Use /api/services/energy/today which now includes water_heating_kwh field.
    """
    logger.warning(
        "Deprecated endpoint /api/ha/water_today called. Use /api/services/energy/today instead."
    )

    config = load_yaml("config.yaml")

    # Check if water heater feature is enabled
    system_config: dict[str, Any] = config.get("system", {})
    has_water_heater = system_config.get("has_water_heater", False)

    if not has_water_heater:
        return {
            "water_kwh_today": 0.0,
            "cost": 0.0,
            "source": "disabled",
            "deprecated": True,
            "note": "Use /api/services/energy/today endpoint instead",
        }

    # Return deprecation notice - clients should migrate to energy/today
    return {
        "water_kwh_today": 0.0,
        "cost": 0.0,
        "source": "deprecated",
        "deprecated": True,
        "note": "Use /api/services/energy/today endpoint which now includes water_heating_kwh field",
    }


# --- Services Endpoints ---
# NOTE: /api/status has been moved to system.py (Rev ARC4)


@router_services.get(
    "/water/boost",
    summary="Get Water Boost Status",
    description="Get current water boost status from executor.",
)
async def get_water_boost():
    """Get current water boost status from executor."""
    from backend.api.routers.executor import get_executor_instance

    executor = get_executor_instance()
    if not executor:
        return {"boost": False, "source": "no_executor"}

    if hasattr(executor, "get_water_boost_status"):
        status = executor.get_water_boost_status()
        if status:
            return {"boost": True, "expires_at": status.get("expires_at"), "source": "executor"}
    return {"boost": False, "source": "executor"}


class WaterBoostRequest(BaseModel):
    duration_minutes: int = 60


@router_services.post(
    "/water/boost",
    summary="Set Water Boost",
    description="Activate water heater boost via executor quick action.",
)
async def set_water_boost(req: WaterBoostRequest) -> dict[str, str]:
    """Activate water heater boost via executor quick action."""
    try:
        from backend.api.routers.executor import (
            get_executor_instance,
        )

        executor = get_executor_instance()
        if not executor:
            logger.error("Executor unavailable for water boost")
            raise HTTPException(503, "Executor not available")
        if hasattr(executor, "set_water_boost"):
            # The executor.set_water_boost isn't strictly typed in Pyright's eyes yet maybe?
            # We fixed it in executor/actions.py, but need to be sure engine calls match.
            # Assuming set_water_boost(duration_minutes=...) exists on the executor instance
            # which is actually engine.py's ExecutorEngine or similar.
            # Actually get_executor_instance returns the Engine instance.
            result = executor.set_water_boost(duration_minutes=req.duration_minutes)  # pyright: ignore [reportUnknownMemberType]
            if not result.get("success"):
                logger.error(f"Failed to set water boost: {result.get('error')}")
                raise HTTPException(500, f"Failed to set water boost: {result.get('error')}")

            logger.info(f"Water boost activated successfully for {req.duration_minutes} minutes")
            return {
                "status": "success",
                "message": f"Water boost activated for {req.duration_minutes} minutes",
            }

        logger.error("Executor missing set_water_boost method")
        raise HTTPException(501, "Water boost not supported by executor")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting water boost: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, f"Internal error setting water boost: {e}") from e


@router_services.delete(
    "/water/boost",
    summary="Cancel Water Boost",
    description="Cancel active water boost.",
)
async def cancel_water_boost() -> dict[str, str]:
    """Cancel active water boost."""
    try:
        from backend.api.routers.executor import (
            get_executor_instance,
        )

        executor = get_executor_instance()
        if executor and hasattr(executor, "clear_water_boost"):
            executor.clear_water_boost()
            logger.info("Water boost cancelled successfully")
        return {"status": "success", "message": "Water boost cancelled"}
    except Exception as e:
        logger.error(f"Error cancelling water boost: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, f"Internal error cancelling water boost: {e}") from e


@router_services.get(
    "/energy/today",
    summary="Get Today's Energy",
    description="Get today's energy summary from database (SlotObservation table).",
)
async def get_energy_today(
    store: LearningStore = Depends(get_learning_store),
) -> dict[str, float]:
    """Get today's energy summary from database aggregation."""
    # Delegate to energy/range with period="today" to avoid duplicate query logic
    range_data = await get_energy_range(period="today", store=store)

    # Extract values from range response (using unified keys)
    grid_imp_kwh = range_data.get("grid_import_kwh", 0.0)
    grid_exp_kwh = range_data.get("grid_export_kwh", 0.0)
    pv_kwh = range_data.get("pv_production_kwh", 0.0)
    load_kwh = range_data.get("load_consumption_kwh", 0.0)
    batt_chg_kwh = range_data.get("battery_charge_kwh", 0.0)
    batt_dis_kwh = range_data.get("battery_discharge_kwh", 0.0)
    ev_kwh = range_data.get("ev_charging_kwh", 0.0)
    water_kwh = range_data.get("water_heating_kwh", 0.0)
    net_cost = range_data.get("net_cost_sek", 0.0)

    # Calculate battery cycles
    config = load_yaml("config.yaml")
    battery_cycles = 0.0
    try:
        cap = float(config.get("battery", {}).get("capacity_kwh", 0.0))
        if cap > 0:
            battery_cycles = batt_dis_kwh / cap
    except Exception:
        pass

    # Return unified response with both legacy aliases and new keys
    return {
        # New unified keys (match energy/range)
        "pv_production_kwh": round(pv_kwh, 2),
        "load_consumption_kwh": round(load_kwh, 2),
        "grid_import_kwh": round(grid_imp_kwh, 2),
        "grid_export_kwh": round(grid_exp_kwh, 2),
        "battery_charge_kwh": round(batt_chg_kwh, 2),
        "battery_discharge_kwh": round(batt_dis_kwh, 2),
        "ev_charging_kwh": round(ev_kwh, 2),
        "water_heating_kwh": round(water_kwh, 2),
        "net_cost_sek": round(net_cost, 2),
        "battery_cycles": round(battery_cycles, 2),
        # Legacy aliases (for backwards compatibility during transition)
        "solar": round(pv_kwh, 2),
        "consumption": round(load_kwh, 2),
        "grid_import": round(grid_imp_kwh, 2),
        "grid_export": round(grid_exp_kwh, 2),
        "net_cost_kr": round(net_cost, 2),
    }


@router_services.get(
    "/energy/range",
    summary="Get Energy Range",
    description="Get energy range data (today, yesterday, week, month, custom) from database.",
)
async def get_energy_range(
    period: str = "today",
    start_date: str | None = None,
    end_date: str | None = None,
    store: LearningStore = Depends(get_learning_store),
) -> dict[str, Any]:
    """Get energy range data from database (SlotObservation table)."""
    import pytz
    from sqlalchemy import func, select

    from backend.learning.models import SlotObservation

    config = load_yaml("config.yaml")

    try:
        tz = pytz.timezone(config.get("timezone", "Europe/Stockholm"))
        now_local = datetime.now(tz)
        today_local = now_local.date()

        # Determine date range based on period or custom dates
        query_start: date = today_local
        query_end: date = today_local

        if period == "custom" and start_date and end_date:
            # Parse custom dates (YYYY-MM-DD format)
            try:
                custom_start = datetime.strptime(start_date, "%Y-%m-%d").date()
                custom_end = datetime.strptime(end_date, "%Y-%m-%d").date()

                # Validate date range
                if custom_end < custom_start:
                    raise ValueError("End date must be after start date")

                query_start = custom_start
                query_end = custom_end
            except ValueError as e:
                if "does not match format" in str(e):
                    raise ValueError("Invalid date format. Use YYYY-MM-DD") from e
                raise
        elif period == "today":
            query_start = query_end = today_local
        elif period == "yesterday":
            query_end = today_local - timedelta(days=1)
            query_start = query_end
        elif period == "week":
            query_end = today_local
            query_start = today_local - timedelta(days=6)
        elif period == "month":
            query_end = today_local
            query_start = today_local - timedelta(days=29)

        # Optimize query: filter by string range to use index
        day_start = tz.localize(datetime(query_start.year, query_start.month, query_start.day))
        # End date is inclusive in the logic, so we want up to the end of that day.
        # Logic says: DATE(slot_start) <= end_date.
        # So we want < end_date + 1 day
        day_end_excl = tz.localize(
            datetime(query_end.year, query_end.month, query_end.day)
        ) + timedelta(days=1)

        start_iso = day_start.isoformat()
        end_iso = day_end_excl.isoformat()

        async with store.AsyncSession() as session:
            stmt = select(
                func.sum(func.coalesce(SlotObservation.import_kwh, 0)),
                func.sum(func.coalesce(SlotObservation.export_kwh, 0)),
                func.sum(func.coalesce(SlotObservation.batt_charge_kwh, 0)),
                func.sum(func.coalesce(SlotObservation.batt_discharge_kwh, 0)),
                func.sum(func.coalesce(SlotObservation.water_kwh, 0)),
                func.sum(func.coalesce(SlotObservation.pv_kwh, 0)),
                func.sum(func.coalesce(SlotObservation.load_kwh, 0)),
                func.sum(func.coalesce(SlotObservation.ev_charging_kwh, 0)),
                # Costs
                func.sum(
                    func.coalesce(SlotObservation.import_kwh, 0)
                    * func.coalesce(SlotObservation.import_price_sek_kwh, 0)
                ),
                func.sum(
                    func.coalesce(SlotObservation.export_kwh, 0)
                    * func.coalesce(SlotObservation.export_price_sek_kwh, 0)
                ),
                # Grid Charge Cost
                func.sum(
                    func.max(
                        0,
                        func.coalesce(SlotObservation.import_kwh, 0)
                        - func.coalesce(SlotObservation.load_kwh, 0),
                    )
                    * func.coalesce(SlotObservation.import_price_sek_kwh, 0)
                ),
                # Self Consumption Savings
                func.sum(
                    func.max(
                        0,
                        func.coalesce(SlotObservation.load_kwh, 0)
                        - func.coalesce(SlotObservation.import_kwh, 0),
                    )
                    * func.coalesce(SlotObservation.import_price_sek_kwh, 0)
                ),
                func.count(),
            ).where(SlotObservation.slot_start >= start_iso, SlotObservation.slot_start < end_iso)
            result = await session.execute(stmt)
            row = result.fetchone()

        if not row:
            raise ValueError("No data returned")

        grid_imp_kwh = float(row[0] or 0.0)
        grid_exp_kwh = float(row[1] or 0.0)
        batt_chg_kwh = float(row[2] or 0.0)
        batt_dis_kwh = float(row[3] or 0.0)
        water_kwh = float(row[4] or 0.0)
        pv_kwh = float(row[5] or 0.0)
        load_kwh = float(row[6] or 0.0)
        ev_kwh = float(row[7] or 0.0)

        import_cost = float(row[8] or 0.0)
        export_rev = float(row[9] or 0.0)
        grid_charge_cost = float(row[10] or 0.0)
        self_cons_savings = float(row[11] or 0.0)
        slot_count = int(row[12] or 0)

        net_cost = import_cost - export_rev

        # NOTE: No longer overlaying HA sensor values - using DB-only data
        # This ensures consistency with the recorder's isolation logic

        return {
            "period": period,
            "start_date": query_start.isoformat(),
            "end_date": query_end.isoformat(),
            "grid_import_kwh": round(grid_imp_kwh, 2),
            "grid_export_kwh": round(grid_exp_kwh, 2),
            "battery_charge_kwh": round(batt_chg_kwh, 2),
            "battery_discharge_kwh": round(batt_dis_kwh, 2),
            "water_heating_kwh": round(water_kwh, 2),
            "pv_production_kwh": round(pv_kwh, 2),
            "load_consumption_kwh": round(load_kwh, 2),
            "ev_charging_kwh": round(ev_kwh, 2),
            "import_cost_sek": round(import_cost, 2),
            "export_revenue_sek": round(export_rev, 2),
            "grid_charge_cost_sek": round(grid_charge_cost, 2),
            "self_consumption_savings_sek": round(self_cons_savings, 2),
            "net_cost_sek": round(net_cost, 2),
            "slot_count": slot_count,
        }
    except Exception as e:
        # Fallback with zeros
        return {
            "period": period,
            "start_date": datetime.now().date().isoformat(),
            "end_date": datetime.now().date().isoformat(),
            "grid_import_kwh": 0.0,
            "grid_export_kwh": 0.0,
            "battery_charge_kwh": 0.0,
            "battery_discharge_kwh": 0.0,
            "water_heating_kwh": 0.0,
            "pv_production_kwh": 0.0,
            "load_consumption_kwh": 0.0,
            "ev_charging_kwh": 0.0,
            "import_cost_sek": 0.0,
            "export_revenue_sek": 0.0,
            "grid_charge_cost_sek": 0.0,
            "self_consumption_savings_sek": 0.0,
            "net_cost_sek": 0.0,
            "slot_count": 0,
            "error": str(e),
        }


# --- Additional Missing Endpoints ---


@router_ha.get(
    "/services",
    summary="List HA Services",
    description="List available Home Assistant services.",
)
async def get_ha_services() -> dict[str, list[str]]:
    """List available HA services."""
    config = load_home_assistant_config()
    url = config.get("url")
    token = config.get("token")
    if not url or not token:
        return {"services": []}

    try:
        headers = make_ha_headers(token)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url.rstrip('/')}/api/services", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            # Flatten to list of "domain.service" strings
            services: list[str] = []
            for domain_obj in data:
                domain = str(domain_obj.get("domain", ""))
                for service_name in domain_obj.get("services", {}):
                    services.append(f"{domain}.{service_name}")
            return {"services": sorted(services)}
    except Exception as e:
        logger.warning(f"Error fetching HA services: {e}")

    return {"services": []}


@router_ha.post(
    "/test",
    summary="Test HA Connection",
    description="Test connection to Home Assistant API.",
)
async def test_ha_connection() -> dict[str, str]:
    """Test connection to Home Assistant."""
    config = load_home_assistant_config()
    url = config.get("url")
    token = config.get("token")

    if not url or not token:
        return {"status": "error", "message": "HA not configured"}

    try:
        headers = make_ha_headers(token)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url.rstrip('/')}/api/", headers=headers)
        if resp.status_code == 200:
            return {"status": "success", "message": "Connected to Home Assistant"}
        else:
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router_services.get(
    "/ha-socket",
    summary="Get HA Socket Status",
    description="Return status of the HA WebSocket connection.",
)
async def get_ha_socket_status() -> dict[str, Any]:
    """Return status of the HA WebSocket connection."""
    try:
        from backend.ha_socket import get_ha_socket_status as _get_status

        return _get_status()
    except ImportError:
        return {"status": "unavailable", "message": "HA socket module not loaded"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router_services.post(
    "/simulate",
    summary="Run Simulation",
    description="Run a simulation of the current schedule.",
)
async def run_simulation() -> dict[str, Any]:
    """Run schedule simulation."""
    try:
        from planner.simulation import simulate_schedule  # pyright: ignore [reportMissingImports]

        with Path("data/schedule.json").open() as f:
            schedule = json.load(f)

        config = load_yaml("config.yaml")
        initial_state: dict[str, Any] = {}  # Simplified simulation

        result = simulate_schedule(schedule, config, initial_state)
        return {"status": "success", "result": cast("dict[str, Any]", result)}
    except ImportError:
        return {"status": "error", "message": "Simulation module not available"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
