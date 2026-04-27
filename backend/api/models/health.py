"""Pydantic models for health-related API responses."""

from pydantic import BaseModel


class HealthIssue(BaseModel):
    """A single health check issue."""

    category: str
    severity: str
    message: str
    guidance: str
    entity_id: str | None = None
    code: str | None = None
    details: dict[str, object] | None = None
    retry_in_s: int | None = None
    config_blocking: bool = False


class HealthResponse(BaseModel):
    """Response model for /api/health endpoint."""

    healthy: bool
    status: str
    mode: str
    rev: str
    issues: list[HealthIssue] = []
    checked_at: str | None = None
    critical_count: int = 0
    warning_count: int = 0
