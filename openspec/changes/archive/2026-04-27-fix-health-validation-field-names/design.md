## Context

Three config health warnings fire as false positives against valid v2 configs. All three are read-only validation bugs — no schema changes, no migrations, no new logic required.

The root cause in each case is the same pattern: validation code references a field name that was renamed or restructured during the ARC14/ARC15 config schema migrations, but the validation code was not updated at the time.

- `system.solar_array` (singular) → `system.solar_arrays` (plural list) — ARC14
- `water_heating.power_kw` (flat field) → `water_heaters[].power_kw` (per-heater) — ARC15
- `battery.max_charge_power_kw` / `battery.max_discharge_power_kw` → `battery.max_charge_w` / `battery.max_discharge_w` — used the wrong names from day one in the new preflight.py

## Goals / Non-Goals

**Goals:**
- Stop the three false positive warnings for users on the v2 config schema
- Each fix is a targeted field name correction with no behavioral change

**Non-Goals:**
- Backwards compatibility with config_version < 2 (not in scope; v1 configs migrate on load)
- Refactoring the health check architecture
- Adding new health checks

## Decisions

**Read from the list directly, don't aggregate.**
For solar, sum `kwp` across all `solar_arrays[]` entries. Any array with kwp > 0 satisfies the check. For water heater, any enabled heater in `water_heaters[]` with `power_kw > 0` satisfies the check. This matches how the rest of the codebase (planner, forecaster) reads these fields.

**For battery watts→kW: divide, don't rename.**
`max_charge_w` and `max_discharge_w` are stored in watts in the config. The preflight check should read those fields and divide by 1000 before comparing to 0. This is consistent with how the rest of the planner reads battery power limits.

## Risks / Trade-offs

No meaningful risks — these are read-only validation fixes with no side effects. If a user genuinely has 0 kWp configured across all solar arrays, the warning will correctly fire.
