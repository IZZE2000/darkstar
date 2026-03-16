## Context

Two independent bugs are addressed in this change:

**Bug 1 — ChartCard overlay index mismatch**: The chart has 18 datasets created in a fixed order (`ds[0]`–`ds[17]`). The visibility control block that runs every render cycle uses hardcoded indices, but those indices were assigned to the wrong overlays. `ds[15]` is "Actual EV" but is hidden/shown by `overlays.export`. `ds[16]` is "Actual Export" but is hidden/shown by `overlays.water`. `ds[17]` ("Actual Water") has no visibility assignment at all.

**Bug 2 — Snapshot-based EV/water energy isolation**: `recorder.py` estimates EV and water heater energy per slot as `power_kw × 0.25h` using an instantaneous sensor read taken at recording time. The total load is computed from a precise cumulative delta. Any mismatch in timing — charger finishes mid-slot, sensor latency, slow HA response — causes the snapshot to read 0, and the full EV/water energy remains in `load_kwh`, contaminating ML training data. The fragility is demonstrated by Kristoffer's logs: 5 kW EV charging appears as 5 kW house load spikes.

The fix follows the same cumulative delta pattern already used for total load: an optional `energy_sensor` field per EV charger and water heater. When configured, the recorder reads start/end cumulative values and computes a precise energy delta. When not configured, the snapshot fallback is retained.

## Goals / Non-Goals

**Goals:**
- Fix ChartCard dataset visibility so EV/Export/Water overlays toggle the correct datasets
- Enable accurate per-slot EV and water heater energy isolation via optional cumulative energy sensors
- Surface a health check WARNING when a load is enabled but has no energy sensor configured
- Add `energy_sensor` field to the Settings UI (EV and Water tabs) with tooltip
- Document the new isolation approach in ARCHITECTURE.md

**Non-Goals:**
- HA History API integration (rejected — adds complexity and a new async code path; cumulative sensors are simpler, universal, and already present on all modern power-measuring devices in HA)
- Backfilling historical slots with corrected EV/water isolation (out of scope — only affects future recordings)
- Making `energy_sensor` required (remains optional; snapshot fallback retained for users who lack the sensor)

## Decisions

### Decision 1: `energy_sensor` on device arrays, not `input_sensors`

**Chosen**: Add `energy_sensor: ''` to each entry in `ev_chargers[]` and `water_heaters[]`.

**Rejected**: Add to `input_sensors` section (e.g., `ev_energy: sensor.xxx`).

**Rationale**: The entity-centric ARC15 design established that all configuration for a device lives in one place. Splitting power sensor and energy sensor across different config sections would violate this principle and add cognitive load. The device array is the single source of truth.

### Decision 2: Cumulative delta, not HA History API

**Chosen**: Read cumulative `energy_sensor` at start and end of each 15-minute recording cycle; compute delta.

**Rejected**: Query the HA `/api/history/period` endpoint to get all state changes during the slot and compute a time-weighted integral.

**Rationale**: The cumulative delta approach is identical to how total load isolation already works. It requires zero new async code paths, no new HA API surface area, and no additional error handling complexity. All modern HA power-measuring devices already have an accompanying cumulative energy entity. The HA History API adds latency, pagination complexity, and a new failure mode (history unavailable) for marginal benefit.

### Decision 3: Config propagation via template-aware merge, no migration scripts

**Chosen**: Add `energy_sensor: ''` to the default template entries in `config.default.yaml`. Existing users receive the field on next startup via `template_aware_merge`.

**Rejected**: Write a migration function in `config_migration.py`.

**Rationale**: The `template_aware_merge` system already handles this: it starts from the default template, overlays user config, and for array items merges by `id`. Any new field in the template with a default value is automatically populated for matched user entries. No migration script needed. This is the established pattern for all future optional fields.

### Decision 4: Health check WARNING (not CRITICAL)

**Chosen**: Emit `severity: "warning"` if an enabled EV charger or water heater has `energy_sensor: ''`.

**Rejected**: `severity: "critical"` or blocking startup.

**Rationale**: The system degrades gracefully (snapshot fallback). Energy isolation is less accurate but the system is fully operational. A critical alert would alarm users unnecessarily and could block them from using the system while they look up their energy sensor entity IDs.

## Risks / Trade-offs

**Risk: User has energy sensor but it resets (e.g., after HA restart)** → The cumulative delta will be negative or implausibly large; the existing spike-clamp logic in recorder.py sets the value to 0.0 and logs a warning. Same behavior as total load isolation. No new handling required.

**Risk: Energy sensor units (Wh vs kWh)** → The existing `get_ha_sensor_kw_normalized` / unit normalization logic handles Wh→kWh conversion for power sensors. The same normalization must be applied to energy sensors (kWh, Wh, MWh). Implementer must use the existing `normalize_energy_to_kwh` pattern.

**Risk: Two sensors for same device (power + energy) vs one** → Slight config overhead. Mitigated by making it optional and surfacing a yellow health advisory.

## Migration Plan

1. Deploy: new `energy_sensor` fields appear in config.yaml automatically on next startup (template merge)
2. Settings UI shows blank field — no user action required to continue operating
3. Health check emits yellow warning for enabled loads without `energy_sensor`
4. Users fill in energy sensor entity ID in Settings UI at their convenience
5. Recorder immediately starts using cumulative delta for new slots once configured
6. No rollback needed — snapshot fallback always available if field left blank
