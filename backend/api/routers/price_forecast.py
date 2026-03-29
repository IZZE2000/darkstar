"""
Price forecast API router for Nordpool spot price predictions.

Provides endpoints to retrieve 7-day price forecasts (p10/p50/p90) when
price forecasting is enabled and models are trained.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.core.secrets import load_yaml
from backend.learning import get_learning_engine
from ml.price_forecast import derive_consumer_prices, get_price_forecasts_from_db

logger = logging.getLogger("darkstar.api.price_forecast")
router = APIRouter(prefix="/api/price-forecast", tags=["price-forecast"])


class PriceForecastResponse(BaseModel):
    """Response model for price forecast endpoint."""

    status: str
    message: str
    forecasts: list[dict[str, Any]]


def _load_config() -> dict[str, Any]:
    """Load configuration from config.yaml."""
    try:
        return load_yaml("config.yaml")
    except Exception:
        return {}


def _is_price_forecast_enabled(config: dict[str, Any]) -> bool:
    """Check if price forecasting is enabled in config."""
    price_config = config.get("price_forecast", {})
    return price_config.get("enabled", False)


def _price_model_exists(config: dict[str, Any]) -> bool:
    """Check if a trained price model exists."""
    price_config = config.get("price_forecast", {})
    model_name = price_config.get("model_name", "price_model.lgb")
    model_path = Path("data/ml/models") / model_name
    return model_path.exists()


@router.get("", response_model=PriceForecastResponse)
async def get_price_forecasts(request: Request) -> PriceForecastResponse:
    """
    Get price forecasts for D+1 through D+7.

    Returns spot price forecasts (p10/p50/p90) along with derived
    import/export prices when price forecasting is enabled and a
    trained model is available.

    Response includes:
    - status: "enabled" | "disabled" | "no_model" | "no_data"
    - message: Human-readable status description
    - forecasts: Array of forecast records with slot_start, spot_p10/p50/p90,
                 import_p50, export_p50, days_ahead
    """
    config = _load_config()

    # Check if price forecasting is enabled
    if not _is_price_forecast_enabled(config):
        return PriceForecastResponse(
            status="disabled",
            message="Price forecasting is disabled in configuration",
            forecasts=[],
        )

    # Check if model exists
    if not _price_model_exists(config):
        return PriceForecastResponse(
            status="no_model",
            message="Price forecast model not yet trained (insufficient data)",
            forecasts=[],
        )

    # Get forecasts from database
    try:
        engine = get_learning_engine()
        db_path = str(engine.db_path)
    except Exception:
        db_path = "data/planner_learning.db"

    forecasts = await get_price_forecasts_from_db(db_path=db_path, limit=1000)

    if not forecasts:
        return PriceForecastResponse(
            status="no_data",
            message="No price forecasts available yet",
            forecasts=[],
        )

    # Enrich forecasts with derived consumer prices
    enriched_forecasts: list[dict[str, Any]] = []
    for forecast in forecasts:
        # Derive import/export prices
        consumer_prices = derive_consumer_prices(
            spot_p10=forecast.get("spot_p10") or 0,
            spot_p50=forecast.get("spot_p50") or 0,
            spot_p90=forecast.get("spot_p90") or 0,
            config=config,
        )

        enriched_forecast = {
            "slot_start": forecast["slot_start"],
            "days_ahead": forecast["days_ahead"],
            "spot_p10": forecast.get("spot_p10"),
            "spot_p50": forecast.get("spot_p50"),
            "spot_p90": forecast.get("spot_p90"),
            "import_p50": consumer_prices.get("import_p50"),
            "export_p50": consumer_prices.get("export_p50"),
        }
        enriched_forecasts.append(enriched_forecast)

    # Sort by slot_start
    enriched_forecasts.sort(key=lambda x: x["slot_start"])

    return PriceForecastResponse(
        status="enabled",
        message=f"Retrieved {len(enriched_forecasts)} price forecasts",
        forecasts=enriched_forecasts,
    )


@router.get("/status")
async def get_price_forecast_status(request: Request) -> dict[str, Any]:
    """
    Get status of the price forecasting system.

    Returns configuration and model status without fetching forecast data.
    """
    config = _load_config()
    price_config = config.get("price_forecast", {})

    enabled = _is_price_forecast_enabled(config)
    model_exists = _price_model_exists(config)

    # Get model info if it exists
    model_info = None
    if model_exists:
        model_name = price_config.get("model_name", "price_model.lgb")
        model_path = Path("data/ml/models") / model_name
        try:
            stat = model_path.stat()
            model_info = {
                "name": model_name,
                "size_bytes": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        except Exception:
            pass

    return {
        "enabled": enabled,
        "config": {
            "min_training_samples": price_config.get("min_training_samples", 500),
            "model_name": price_config.get("model_name", "price_model.lgb"),
        },
        "model_available": model_exists,
        "model_info": model_info,
    }
