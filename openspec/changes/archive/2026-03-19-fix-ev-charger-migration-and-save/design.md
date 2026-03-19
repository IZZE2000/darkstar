## Context

The `feat(multi-device-ev-chargers)` commit introduced two bugs:

1. **Migration order bug**: `migrate_config()` calls `remove_deprecated_keys()` (step 2) before `_migrate_ev_charger_fields()` (step 7). `DEPRECATED_NESTED_KEYS` lists `executor.ev_charger: ["switch_entity", "replan_on_plugin", "replan_on_unplug"]`, so these are deleted before migration can copy them to `ev_chargers[0]`. Result: user switch entity is silently lost.

2. **Type mismatch bug**: `config.yaml` has `departure_time: 18:00` (unquoted). PyYAML (used by `core/secrets.py` `load_yaml`) applies YAML 1.1 sexagesimal parsing and returns the integer `1080`. The frontend stores `1080` in the form. On save, the entire `ev_chargers` array is included in the patch (any field change triggers full array). `_validate_config_for_save()` then calls `re.match(pattern, 1080)` → `TypeError` → HTTP 500.

## Goals / Non-Goals

**Goals:**
- Restore correct migration order so switch entity and replan settings are preserved
- Unblock config save by making departure_time validation type-safe
- Fix the YAML source of the integer to prevent recurrence

**Non-Goals:**
- Switching `load_yaml` from PyYAML to ruamel (broader change, out of scope)
- Recovering user's already-lost switch entity value (data already wiped from their config.yaml)
- Adding general type coercion across all string config fields

## Decisions

### Decision: Reorder migration steps, not restructure them

Move the `_migrate_ev_charger_fields()` call to before `remove_deprecated_keys()` in `migrate_config()`. The existing spec (config-migration) already states this ordering implicitly — "migrate then remove". The bug is purely implementation drift.

**Alternative considered**: Run migration inside `_migrate_ev_charger_fields` by reading keys before they're removed, then deleting them manually. Rejected: more complex, duplicates logic that `remove_deprecated_keys` already handles correctly.

### Decision: Coerce departure_time to str in validation, AND fix YAML source

Apply `str(ev.get("departure_time", "") or "")` in `_validate_config_for_save()`. This defensive coercion handles any future case where an integer leaks through (e.g., other callers, future YAML quirks).

Additionally fix `config.yaml` to quote bare time values. This removes the integer at the source, so the frontend and API both receive the correct string type.

**Alternative considered**: Fix only the YAML source. Rejected: the validator should be type-safe regardless of where input comes from.

### Decision: Quote time values in config.yaml with double-quotes

`departure_time: "18:00"` (double-quoted string). This is the canonical form and is unambiguous in both YAML 1.1 and 1.2.

## Risks / Trade-offs

- **[Data loss already occurred]** → The user's `switch_entity` value was already wiped from `config.yaml` by the buggy migration. The fix prevents future loss but cannot recover the lost value. User must re-enter it.
- **[Migration order change]** → Any future migration step that also touches `executor.ev_charger` before step 7 would still be vulnerable. Mitigation: the spec now explicitly requires migration before removal.

## Migration Plan

1. Apply code fixes (migration reorder + validation coercion)
2. Apply config.yaml fix (quote time values)
3. On next startup, `migrate_config()` will run correctly — but since switch_entity was already wiped in the previous migration, the value will not be restored. This is acceptable; user must re-enter.
