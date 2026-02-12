"""Custom exceptions for Darkstar Energy Manager."""


class PVForecastError(Exception):
    """Raised when PV forecast generation fails.

    This is a critical error that prevents accurate energy planning.
    Unlike other forecast failures, we do NOT fall back to dummy data
    as that would cause the planner to make incorrect decisions.

    Attributes:
        message: Explanation of the error
        original_exception: The underlying exception that caused the failure
        solar_arrays: Number of solar arrays being forecast
        details: Additional context about the forecast attempt
    """

    def __init__(
        self,
        message: str,
        original_exception: Exception | None = None,
        solar_arrays: int = 0,
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.original_exception = original_exception
        self.solar_arrays = solar_arrays
        self.details = details or {}

    def __str__(self) -> str:
        parts = [self.message]
        if self.original_exception:
            parts.append(f"Original error: {self.original_exception}")
        if self.solar_arrays:
            parts.append(f"Solar arrays: {self.solar_arrays}")
        return " | ".join(parts)
