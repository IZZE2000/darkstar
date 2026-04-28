## REMOVED Requirements

### Requirement: EXCESS_PV_HEATING override

**Reason**: Excess PV utilization is now handled proactively by the Kepler planner, which schedules water heater boost and custom entity sinks based on forecast excess PV. The reactive override is no longer needed and its removal eliminates notification spam and the water temperature dispatch bug.

**Migration**: Excess PV handling moves to the Kepler planner. No user action required — the planner automatically optimizes excess PV. Users who relied on the override for water heater boost should configure `excess_pv.sink: water_heater_boost` in Settings → Hardware Features.
