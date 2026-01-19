"""Pydantic models for system-related API responses."""

from pydantic import BaseModel


class VersionResponse(BaseModel):
    """Response model for /api/version endpoint."""

    version: str


class StatusResponse(BaseModel):
    """Response model for /api/status endpoint."""

    status: str
    mode: str
    rev: str
    soc_percent: float
    pv_power_kw: float
    load_power_kw: float
    battery_power_kw: float
    grid_power_kw: float


class LogInfoResponse(BaseModel):
    """Response model for /api/system/log-info endpoint."""

    filename: str
    size_bytes: int
    last_modified: str


class LearningHealth(BaseModel):
    """Health metrics for the learning system."""

    total_runs: int
    status: str  # infant, statistician, graduate
    last_run: str | None


class DatabaseHealth(BaseModel):
    """Health metrics for the database."""

    size_mb: float
    slot_plans_count: int
    slot_observations_count: int
    health: str  # good, warning, error


class PlannerHealth(BaseModel):
    """Health metrics for the planner."""

    last_run: str | None
    status: str  # success, error, running
    next_scheduled: str | None


class SystemMetrics(BaseModel):
    """General system metrics."""

    errors_24h: int
    uptime_hours: float
    version: str


class SystemHealthResponse(BaseModel):
    """Response model for /api/system/health endpoint."""

    learning: LearningHealth
    database: DatabaseHealth
    planner: PlannerHealth
    system: SystemMetrics
