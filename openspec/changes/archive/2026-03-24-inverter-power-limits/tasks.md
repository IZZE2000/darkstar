## 1. Config & Types

- [x] 1.1 Add `max_inverter_ac_kw: float | None = None` field to `KeplerConfig` in `planner/solver/types.py` (after `max_import_power_kw`, line ~60). Add comment: `# Inverter AC output limit (PV + battery discharge combined)`

- [x] 1.2 Update `config.default.yaml` — replace the `system.inverter` section (lines 26-29) with:
  ```yaml
  inverter:
    max_ac_power_kw: 10.0              # Maximum inverter AC power output (PV + battery discharge)
    max_dc_input_kw: 12.0              # Maximum DC power from PV strings (clips PV forecast)
  ```
  Remove the old `max_power_kw` key and the "not implemented" comment.

- [x] 1.3 Update `config.default.yaml` — remove `inverter_ac_limit_kw: 8.8` line (line ~306) from the `executor.controller` section. Remove only this one line, leave everything else in the controller section intact.

- [x] 1.4 Remove `inverter_ac_limit_kw` from `executor/config.py`:
  - Remove `inverter_ac_limit_kw: float = 8.8` from the `ControllerConfig` dataclass (line ~148)
  - Remove the `inverter_ac_limit_kw=float(...)` parsing block from the config loading function (lines ~470-472)

## 2. Config Migration

- [x] 2.1 Add `"inverter"` to the `DEPRECATED_NESTED_KEYS["system"]` list in `backend/config_migration.py` (line ~102-105). This will cause the deprecated key sweep to remove `system.inverter.max_power_kw` (the old orphan key) after migration maps it.

- [x] 2.2 Add a new migration function `_migrate_inverter_keys` in `backend/config_migration.py` that:
  - Reads `system.inverter.max_power_kw` (old key)
  - If it exists AND `system.inverter.max_ac_power_kw` does NOT exist: set `system.inverter.max_ac_power_kw` to the old value
  - Returns `(config, changed_bool)` following the `MigrationStep` pattern
  - Does NOT touch `max_dc_input_kw` (no old equivalent to migrate)

- [x] 2.3 Call `_migrate_inverter_keys` in the `run_migration()` function, before the `remove_deprecated_keys` call. Follow the same pattern as `_migrate_ev_charger_fields` (line ~663). Merge the `changed` flag into `pre_merge_changes`.

## 3. Planner Adapter

- [x] 3.1 In `planner/solver/adapter.py`, read the new config keys. After the existing `system.get("grid", {}).get("max_power_kw")` block (around line 413-421), add:
  ```python
  max_inverter_ac_kw=(
      float(system.get("inverter", {}).get("max_ac_power_kw"))
      if system.get("inverter", {}).get("max_ac_power_kw")
      else None
  ),
  ```
  Pass this as the new `max_inverter_ac_kw` kwarg to `KeplerConfig`.

- [x] 3.2 In `planner/solver/adapter.py`, add PV DC clipping. Read `system.inverter.max_dc_input_kw` from config. If set, clip each slot's `pv_kwh` before building `KeplerInputSlot`. The clipping logic:
  ```python
  max_dc_input_kw = system.get("inverter", {}).get("max_dc_input_kw")
  # Then in the slot-building loop:
  if max_dc_input_kw is not None:
      slot_hours = (end - start).total_seconds() / 3600.0
      pv_kwh = min(pv_kwh, float(max_dc_input_kw) * slot_hours)
  ```
  Find where `KeplerInputSlot` objects are constructed and apply the clip to `pv_kwh` before it's passed in. Log a debug message when clipping occurs.

## 4. Solver Constraint

- [x] 4.1 In `planner/solver/kepler.py`, add the inverter AC output constraint. After the existing `max_export_power_kw` constraint block (lines ~315-316), add:
  ```python
  # Inverter AC output limit (PV + battery discharge combined)
  if config.max_inverter_ac_kw is not None:
      inverter_ac_kwh = config.max_inverter_ac_kw * h
      prob += discharge[t] + s.pv_kwh <= inverter_ac_kwh
  ```
  This uses `s.pv_kwh` which is the already-clipped PV constant for the slot, and `h` is the slot duration in hours (already computed as `slot_hours[t]`).

## 5. Frontend: Settings UI

- [x] 5.1 Add tooltip entries to `frontend/src/config-help.json`. Add these two entries (place them after the existing `system.grid.max_power_kw` entry):
  ```json
  "system.inverter.max_ac_power_kw": "Maximum AC power your inverter can produce. Limits combined PV + battery discharge output.",
  "system.inverter.max_dc_input_kw": "Maximum DC power from PV strings your inverter accepts. PV forecast is clipped to this value."
  ```
  Also remove the old entry: `"system.inverter.max_power_kw": "Maximum inverter AC power output"`

- [x] 5.2 Add field definitions in `frontend/src/pages/settings/types.ts`. In the System tab section that contains the `system.grid.max_power_kw` field (around line 169-175), add two new fields AFTER the grid max power field:
  ```typescript
  {
      key: 'system.inverter.max_ac_power_kw',
      label: 'Inverter Max AC Power (kW)',
      helper: 'Maximum AC power your inverter can produce.',
      path: ['system', 'inverter', 'max_ac_power_kw'],
      type: 'number',
  },
  {
      key: 'system.inverter.max_dc_input_kw',
      label: 'Inverter Max DC Input (kW)',
      helper: 'Maximum DC power from PV strings.',
      path: ['system', 'inverter', 'max_dc_input_kw'],
      type: 'number',
  },
  ```
  Also find and remove any existing field definition for `system.inverter.max_power_kw` if one exists.

## 6. Backend Validation

- [x] 6.1 Add validation warnings in `backend/api/routers/config.py` in the `_validate_config` function. After the battery capacity check (around line 354), add:
  ```python
  # Inverter: WARNING if AC power not configured
  inverter_cfg = system_cfg.get("inverter", {})
  if system_cfg.get("has_battery", True) or system_cfg.get("has_solar", True):
      if not inverter_cfg.get("max_ac_power_kw"):
          issues.append({
              "severity": "warning",
              "message": "Inverter AC power limit not configured",
              "guidance": "Set system.inverter.max_ac_power_kw to your inverter's maximum AC output power. "
              "Without this, the planner may schedule more export than your inverter can deliver.",
          })

  # Inverter: WARNING if DC input not configured (only relevant with solar)
  if system_cfg.get("has_solar", True):
      if not inverter_cfg.get("max_dc_input_kw"):
          issues.append({
              "severity": "warning",
              "message": "Inverter DC input limit not configured",
              "guidance": "Set system.inverter.max_dc_input_kw to your inverter's maximum DC input from PV strings. "
              "Without this, PV forecasts above your inverter's capacity won't be clipped.",
          })
  ```

## 7. Cleanup

- [x] 7.1 Update `docs/BACKLOG.md`: Remove the `[DRAFT] Inverter Clipping Support` section (lines ~36-58) and the `[Config] Inverter Max Power Config Orphan` section (lines ~69-74). These are now addressed by this change.

## 8. Tests

- [x] 8.1 Add solver test in `tests/planner/test_kepler_export.py` (or a new `tests/planner/test_inverter_limits.py`): test that when `max_inverter_ac_kw=10.0` is set, high PV + battery discharge is capped. Create a 2-slot scenario with `pv_kwh=2.0` (8kW), full battery, high export price — verify `discharge + pv_kwh <= 2.5` per slot.

- [x] 8.2 Add solver test: when `max_inverter_ac_kw` is `None`, behavior is unchanged (no constraint applied). Same scenario as 8.1 but without the AC limit — verify discharge is unconstrained by inverter.

- [x] 8.3 Add adapter test: verify PV clipping. Call the adapter with `max_dc_input_kw=12.0` and a slot with PV forecast of 18kW average (4.5 kWh in 15min) — verify the output slot has `pv_kwh=3.0`.

- [x] 8.4 Add adapter test: verify `max_inverter_ac_kw` is mapped from `system.inverter.max_ac_power_kw` to `KeplerConfig.max_inverter_ac_kw`. Call `config_to_kepler_config` with the key set and verify the field is populated.

- [x] 8.5 Add config migration test: verify `system.inverter.max_power_kw` is migrated to `system.inverter.max_ac_power_kw` when old key exists and new key doesn't.

- [x] 8.6 Add config migration test: verify existing `system.inverter.max_ac_power_kw` is NOT overwritten when both old and new keys exist.

- [x] 8.7 Add config validation test: verify warnings are returned when `max_ac_power_kw` and `max_dc_input_kw` are missing and `has_battery`/`has_solar` are true.
