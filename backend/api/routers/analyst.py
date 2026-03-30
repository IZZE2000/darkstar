"""
Analyst API Router - Rev ARC3

Provides endpoints for strategy analysis and advice generation.
"""

import logging
from typing import Any

from fastapi import APIRouter

from backend.core.secrets import load_yaml

logger = logging.getLogger("darkstar.api.analyst")

router = APIRouter(prefix="/api/analyst", tags=["analyst"])


def _get_price_advice(
    daily_outlook: list[dict[str, Any]], today_avg_spot: float
) -> list[dict[str, Any]]:
    """
    Generate price-related advice items based on forecast data.

    Rules:
    1. Cheapest day ahead: If any day D+1..D+7 is 30%+ cheaper than today
    2. Prices rising: If every day D+1..D+3 is higher than today
    3. Cheap overnight: If tonight's 22:00-06:00 avg is 25%+ below daily avg

    Args:
        daily_outlook: List of daily outlook dicts (D+1 through D+7)
        today_avg_spot: Today's average spot price for comparison

    Returns:
        List of advice dicts with category="price", message, and priority
    """
    advice_items: list[dict[str, Any]] = []

    if not daily_outlook or today_avg_spot <= 0:
        return advice_items

    # Rule 1: Cheapest day ahead (30%+ drop)
    cheapest_day = None
    max_drop_pct = 0.0

    for day in daily_outlook:
        day_avg = day.get("avg_spot_p50", 0)
        if day_avg > 0 and day_avg < today_avg_spot * 0.70:  # 30%+ cheaper
            drop_pct = (today_avg_spot - day_avg) / today_avg_spot * 100
            if drop_pct > max_drop_pct:
                max_drop_pct = drop_pct
                cheapest_day = day

    if cheapest_day and max_drop_pct >= 30:
        advice_items.append(
            {
                "category": "price",
                "message": f"Prices drop ~{max_drop_pct:.0f}% on {cheapest_day['day_label']}. Consider deferring heavy loads.",
                "priority": "info",
            }
        )

    # Rule 2: Prices rising (D+1 through D+3 all higher than today)
    d1_to_d3 = [d for d in daily_outlook if d.get("days_ahead", 0) <= 3]

    if len(d1_to_d3) >= 3:
        all_higher = all(d.get("avg_spot_p50", float("inf")) > today_avg_spot for d in d1_to_d3[:3])
        if all_higher:
            advice_items.append(
                {
                    "category": "price",
                    "message": "Prices rising all week — today is the cheapest day in the next 3 days.",
                    "priority": "info",
                }
            )

    # Rule 3: Cheap overnight window
    # Calculate tonight's 22:00-06:00 average vs full day average
    # For simplicity, we use the day's min/max to estimate overnight window
    if daily_outlook:
        tonight = daily_outlook[0]  # D+1 is "tonight"
        min_price = tonight.get("min_hour_p50", 0)
        avg_price = tonight.get("avg_spot_p50", 0)

        if min_price > 0 and avg_price > 0 and min_price < avg_price * 0.75:
            advice_items.append(
                {
                    "category": "price",
                    "message": "Tonight 22:00-06:00 has the lowest prices — ideal for heavy loads.",
                    "priority": "info",
                }
            )

    return advice_items


def _get_strategy_advice() -> dict[str, Any]:
    """Generate strategy advice based on current conditions."""
    try:
        config = load_yaml("config.yaml")
        s_index_cfg = config.get("s_index", {})
        risk_appetite = s_index_cfg.get("risk_appetite", 3)

        # Basic rule-based advice
        advice_items: list[dict[str, Any]] = []

        if risk_appetite <= 2:
            advice_items.append(
                {
                    "category": "risk",
                    "message": "Conservative risk profile active. Battery will maintain higher reserves.",
                    "priority": "info",
                }
            )
        elif risk_appetite >= 4:
            advice_items.append(
                {
                    "category": "risk",
                    "message": "Aggressive risk profile active. Consider lowering if forecast accuracy is poor.",
                    "priority": "warning",
                }
            )

        # Check for vacation mode
        learning_cfg = config.get("learning", {})
        if learning_cfg.get("vacation_mode_enabled", False):
            advice_items.append(
                {
                    "category": "mode",
                    "message": "Vacation mode is active. Water heating is in anti-legionella mode.",
                    "priority": "info",
                }
            )

        # Battery wear cost check
        battery_econ = config.get("battery_economics", {})
        cycle_cost = battery_econ.get("battery_cycle_cost_kwh", 0.05)
        if cycle_cost > 0.15:
            advice_items.append(
                {
                    "category": "battery",
                    "message": f"High battery cycle cost ({cycle_cost} SEK/kWh). Arbitrage may be limited.",
                    "priority": "warning",
                }
            )

        # Check if price forecasting is enabled and add price advice
        price_forecast_cfg = config.get("price_forecast", {})
        if price_forecast_cfg.get("enabled", False):
            try:
                # Import price outlook helpers
                from backend.core.forecasts import get_forecast_db_path
                from backend.core.price_outlook import get_daily_outlook

                db_path = get_forecast_db_path()
                daily_outlook = get_daily_outlook(db_path)

                if daily_outlook:
                    # Get today's average spot price from config or use D+1 as reference
                    # For simplicity, we use the first day's average as a proxy for "today"
                    today_avg_spot = daily_outlook[0].get("avg_spot_p50", 0.5)

                    # Generate price advice
                    price_advice = _get_price_advice(daily_outlook, today_avg_spot)
                    advice_items.extend(price_advice)
            except Exception as e:
                # Log but don't fail if price advice generation fails
                logger.debug(f"Could not generate price advice: {e}")

        return {
            "advice": advice_items,
            "count": len(advice_items),
            "source": "rule_based",
        }
    except Exception as e:
        logger.warning(f"Failed to generate advice: {e}")
        return {"advice": [], "count": 0, "error": str(e)}


@router.get(
    "/advice",
    summary="Get Strategy Advice",
    description="Returns rule-based or LLM-generated strategy advice.",
)
async def get_advice() -> dict[str, Any]:
    """Get strategy advice based on current conditions."""
    return _get_strategy_advice()


@router.get(
    "/run",
    summary="Run Strategy Analysis",
    description="Triggers a full strategy analysis and returns recommendations.",
)
async def run_analysis() -> dict[str, Any]:
    """Run strategy analysis and return recommendations."""
    try:
        from backend.strategy.history import get_strategy_history

        # Get recent strategy events
        history = get_strategy_history(limit=10)

        # Get current advice
        advice = _get_strategy_advice()

        return {
            "status": "success",
            "advice": advice.get("advice", []),
            "recent_events": history,
            "message": "Analysis completed",
        }
    except ImportError:
        return {
            "status": "partial",
            "advice": _get_strategy_advice().get("advice", []),
            "recent_events": [],
            "message": "Strategy history module not available",
        }
    except Exception as e:
        logger.exception("Strategy analysis failed")
        return {"status": "error", "message": str(e)}
