"""
Terminal Value System (TVS)

Calculates the value of stored energy at the end of the planning horizon.
Encourages the solver to hold energy if it's valuable tomorrow, or dump it if it's cheap.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

import pandas as pd

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger("darkstar.strategy.tvs")


@dataclass
class TerminalValueConfig:
    risk_appetite: int = 3  # 1 (Safety) to 5 (Gambler)


class TerminalValueSystem:
    """
    Calculates the 'intrinsic value' of energy stored in the battery at the end of the horizon.
    """

    # Risk Multipliers (How much do we value 'safety stock' vs 'trading profits'?)
    # > 1.0: Valued HIGHER than market (Hoard energy)
    # < 1.0: Valued LOWER than market (Encourage cycling/dumping)
    RISK_MULTIPLIERS: ClassVar[dict[int, float]] = {
        1: 1.30,  # Safety: Huge premium on stored energy
        2: 1.15,  # Caution: Mild premium
        3: 1.00,  # Neutral: Fair market value
        4: 0.90,  # Bold: Slight discount (encourage use)
        5: 0.80,  # Gambler: Aggressive discount (dump info daily cycles)
    }

    def __init__(self, config: dict[str, Any]):
        s_index_cfg = config.get("s_index", {})
        self.risk_appetite = int(s_index_cfg.get("risk_appetite", 3))

    def calculate_terminal_value(
        self,
        df: pd.DataFrame,
        current_time: datetime,
    ) -> tuple[float, dict[str, Any]]:
        """
        Calculate the SEK/kWh value of energy at the end of the horizon.

        Args:
            df: DataFrame with 'import_price_sek_kwh' and sufficient future range.
            current_time: The current simulation time (now).

        Returns:
            Tuple of (terminal_value_sek_kwh, debug_metadata)
        """
        if df.empty:
            return 0.0, {"error": "empty_df"}

        # 1. Determine base market value (Tomorrow vs Today)
        # Check if we have prices for "Tomorrow" (any time after midnight tonight)
        # Note: df index is timezone-aware
        ts = pd.Timestamp(current_time)
        tomorrow_start = (ts + pd.Timedelta(days=1)).normalize()
        tomorrow_prices = df[df.index >= tomorrow_start]

        base_value = 0.0
        method = "unknown"

        if not tomorrow_prices.empty:
            method = "tomorrow_peaks"
            # We have tomorrow's prices. Value energy based on tomorrow's OPPORTUNITY.
            # Strategy: Value based on the PEAK prices (when we would discharge).
            # Using average of peaks is more realistic than average of all day.

            # Identify Morning Peak (06:00 - 09:00) and Evening Peak (17:00 - 21:00)
            tomorrow_h = tomorrow_prices.index.hour
            morning_mask = (tomorrow_h >= 6) & (tomorrow_h < 9)
            evening_mask = (tomorrow_h >= 17) & (tomorrow_h < 21)

            morning_avg = (
                tomorrow_prices.loc[morning_mask, "import_price_sek_kwh"].mean()
                if morning_mask.any()
                else 0.0
            )
            evening_avg = (
                tomorrow_prices.loc[evening_mask, "import_price_sek_kwh"].mean()
                if evening_mask.any()
                else 0.0
            )

            # If no peaks found (e.g. partial data), fallback to full day mean
            if morning_avg == 0 and evening_avg == 0:
                base_value = tomorrow_prices["import_price_sek_kwh"].mean()
                method = "tomorrow_mean (no peaks found)"
            else:
                # Value at the BEST opportunity (Max of peaks)
                base_value = max(morning_avg, evening_avg)

        else:
            method = "today_projection"
            # We don't have tomorrow's prices yet (usually before 13:00).
            # Use today's remaining average as a proxy, but adjust for weekend patterns.
            # E.g. If today is Friday, tomorrow is Saturday (cheaper).

            # Get remaining today prices
            today_future = df[df.index >= current_time]
            if today_future.empty:
                # Fallback to last known price
                base_value = df["import_price_sek_kwh"].iloc[-1]
                method = "last_known"
            else:
                base_value = today_future["import_price_sek_kwh"].mean()

            # Weekend Adjustment
            # 5 = Saturday, 6 = Sunday. If tomorrow (weekday + 1) is Sat/Sun, discount it.
            # current_time.weekday(): Mon=0, Sun=6
            tomorrow_weekday = (current_time.weekday() + 1) % 7
            is_weekend_tomorrow = tomorrow_weekday >= 5

            if is_weekend_tomorrow:
                adjustment = 0.95  # Expect 5% lower prices
                base_value *= adjustment
                method += "_weekend_adj"

        # 2. Apply Risk Multiplier
        risk_multiplier = self.RISK_MULTIPLIERS.get(self.risk_appetite, 1.0)
        final_value = base_value * risk_multiplier

        # Round for sanity
        final_value = round(final_value, 4)

        debug = {
            "method": method,
            "base_market_value": round(base_value, 4),
            "risk_appetite": self.risk_appetite,
            "risk_multiplier": risk_multiplier,
            "terminal_value_sek_kwh": final_value,
        }

        return final_value, debug
