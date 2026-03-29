"""DST-safe time utility functions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, overload

import pandas as pd
import pytz
from pytz.exceptions import AmbiguousTimeError, NonExistentTimeError

if TYPE_CHECKING:
    from pytz import BaseTzInfo


def dst_safe_date_range(
    start: datetime | pd.Timestamp,
    end: datetime | pd.Timestamp,
    freq: str,
    tz: str | BaseTzInfo,
    **kwargs: object,
) -> pd.DatetimeIndex:
    """Generate a date range that handles DST transitions safely.

    This function generates the date range in UTC (which has no DST),
    then converts to the target timezone. This avoids NonExistentTimeError
    during spring-forward and AmbiguousTimeError during fall-back.

    Args:
        start: Start datetime (naive or timezone-aware)
        end: End datetime (naive or timezone-aware)
        freq: Frequency string (e.g., "15min")
        tz: Target timezone (pytz timezone object or string)
        **kwargs: Additional arguments passed to pd.date_range

    Returns:
        pd.DatetimeIndex: Date range in the target timezone
    """
    # Ensure tz is a pytz timezone object
    if isinstance(tz, str):
        tz = pytz.timezone(tz)

    # Convert naive datetimes to timezone-aware in the target timezone
    if start.tzinfo is None:
        start = tz.localize(start)
    if end.tzinfo is None:
        end = tz.localize(end)

    # Convert to UTC
    start_utc = start.astimezone(pytz.UTC)
    end_utc = end.astimezone(pytz.UTC)

    # Generate date range in UTC (no DST issues)
    utc_range = pd.date_range(start=start_utc, end=end_utc, freq=freq, tz="UTC", **kwargs)

    # Convert to target timezone
    return utc_range.tz_convert(tz)


@overload
def dst_safe_localize(timestamps: pd.Series, tz: str | BaseTzInfo) -> pd.Series: ...


@overload
def dst_safe_localize(timestamps: pd.DatetimeIndex, tz: str | BaseTzInfo) -> pd.DatetimeIndex: ...


@overload
def dst_safe_localize(timestamps: datetime, tz: str | BaseTzInfo) -> datetime: ...


def dst_safe_localize(
    timestamps: pd.Series | pd.DatetimeIndex | datetime,
    tz: str | BaseTzInfo,
) -> pd.Series | pd.DatetimeIndex | datetime:
    """Localize timestamps to a timezone, handling DST transitions.

    Args:
        timestamps: pd.Series, pd.DatetimeIndex, or single datetime object
        tz: Target timezone (pytz timezone object or string)

    Returns:
        Localized timestamps of the same type as input
    """
    # Ensure tz is a pytz timezone object
    if isinstance(tz, str):
        tz = pytz.timezone(tz)

    if isinstance(timestamps, pd.Series):
        # For Series, use dt accessor with try/except for ambiguous times
        try:
            return timestamps.dt.tz_localize(tz, nonexistent="shift_forward", ambiguous="infer")
        except ValueError:
            # If infer fails (not enough context), use is_dst=True for ambiguous times
            return timestamps.dt.tz_localize(tz, nonexistent="shift_forward", ambiguous=True)
    elif isinstance(timestamps, pd.DatetimeIndex):
        # For DatetimeIndex, use direct tz_localize with try/except
        try:
            return timestamps.tz_localize(tz, nonexistent="shift_forward", ambiguous="infer")
        except ValueError:
            # If infer fails, use is_dst=True for ambiguous times
            return timestamps.tz_localize(tz, nonexistent="shift_forward", ambiguous=True)
    elif isinstance(timestamps, datetime):
        # For single datetime objects, use try/except
        try:
            return tz.localize(timestamps)
        except (AmbiguousTimeError, NonExistentTimeError):
            return tz.localize(timestamps, is_dst=True)
    else:
        raise TypeError(f"Unsupported type for timestamps: {type(timestamps)}")
