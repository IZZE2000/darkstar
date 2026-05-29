## Context

Beta testers with real HA installations have cumulative energy sensors (like smart meters) that report in Wh. The current `_normalize_energy_to_kwh` function in `backend/core/ha_client.py` only recognizes a narrow set of unit strings (`"WH"`, `"WATT_HOUR"`, `"WATT_HOURS"`). When a sensor's `unit_of_measurement` attribute is missing, `None`, or uses a non-standard variant, the function silently assumes kWh.

For a sensor reporting `5,675,983 Wh` (≈ 5.7 MWh cumulative), this results in `5,675,983 kWh` being used — a 1000× overcount. This cascades into:

1. **Load profile explosion**: `get_load_profile_from_ha` returns `5,675,983 kWh/day` — used by the planner
2. **Solver failure**: MILP solver receives infeasible load forecasts → "Solver failed: Undefined"
3. **Zero energy recordings**: Recorder's delta-based calculation gets enormous values that trigger meter-reset detection or spike validation, falling back to 0.0

The fix must be backward-compatible: existing sensors that correctly report in kWh must not be affected.

## Current Code State

The function `_normalize_energy_to_kwh` exists at `backend/core/ha_client.py` line ~122. The file already has `import logging` and a module logger (`logger = logging.getLogger("darkstar.core.ha_client")`).

Key issues in the current implementation:
- **Line ~135-136**: `if not unit: return value` — silently assumes kWh when unit is missing. This is the core bug.
- **Line ~138**: `str(unit).upper().replace(" ", "_")` — only strips spaces, not dots, hyphens, or unicode middle-dots. Variants like `"W·h"` fall through to the unknown-unit fallback.
- **Line ~147**: Unknown unit silently returns the raw value assuming kWh — no logging.

The load profile function `get_load_profile_from_ha` (line ~378) already has:
- A per-slot cap at 10 kWh per 15-min slot (line ~524) — this is on the final averaged daily profile, AFTER normalization. This stays as-is.
- No total daily sanity bound — this is what we add.

## Goals / Non-Goals

**Goals:**
- Fix Wh→kWh normalization for all common HA sensor unit variants
- Handle the case where `unit_of_measurement` is missing/None and the value is clearly in Wh
- Add a sanity bound on load profile daily totals to prevent planner infeasibility
- Provide clear logging so users can see what unit was detected

**Non-Goals:**
- Rewriting the entire energy recording pipeline
- Adding UI for sensor unit configuration (users configure in HA, not Darkstar)
- Handling J, cal, BTU or other non-electrical energy units
- Changing the existing per-slot 10 kWh cap behavior

## Decisions

### Decision 1: Heuristic detection for missing units

When `unit_of_measurement` is missing/None, use a magnitude threshold to infer the unit.

**Approach**: If the raw value exceeds 100,000, assume Wh and divide by 1000. Rationale: A typical household's cumulative energy sensor in kWh reads 5,000–50,000 kWh. In Wh, the same reads 5,000,000–50,000,000. Values above 100k are extremely unlikely in kWh for residential installations (that's 100 MWh of cumulative energy).

**Alternative considered**: Require users to set `unit_of_measurement` in HA. Rejected because many HA integrations don't expose this attribute, and the user experience is poor — they'd see no data with no clear error.

### Decision 2: Normalize at the point of read

Keep normalization in `_normalize_energy_to_kwh` (called from recorder and ha_client) rather than adding a separate validation layer. This keeps the fix localized — one function change fixes both the recorder and the load profile fetcher.

### Decision 3: Propagate unit from first HA history state

The HA `/api/history/period` endpoint (even with `minimal_response=False`) only includes the full `attributes` dict on the **first** state entry in the response. All subsequent state entries have `"attributes": {}`. This means `unit_of_measurement` is only available on the first entry — the rest return `None`.

This is the actual root cause of the beta tester bug: the first state normalizes correctly (e.g., `5,675,983 Wh → 5,675.98 kWh`), but the second state has no unit, gets no normalization (`5,675,993` treated as kWh), and the delta becomes `5,670,317 kWh` — a single catastrophic spike.

**Approach**: In `get_load_profile_from_ha`, before the state loop, initialize `cached_unit = None`. On each iteration, if the current state has a non-empty `unit_of_measurement` attribute, update `cached_unit`. When passing `unit` to `_normalize_energy_to_kwh`, use the current state's unit if available, otherwise fall back to `cached_unit`. This matches HA's API contract: attributes on the first entry describe the entire series.

The magnitude heuristic in `_normalize_energy_to_kwh` (Decision 1) remains as a safety net for other callers (e.g., the recorder) and for the edge case where the first state entry also lacks attributes.

### Decision 4: Sanity bound on load profile output

Add a maximum daily total check in `get_load_profile_from_ha`. If the calculated daily total exceeds 500 kWh/day (a generous upper bound for any residential installation), log a warning and return the dummy profile instead. This prevents planner infeasibility even if normalization somehow fails. The check goes between the daily total calculation and the existing `total_daily <= 0` check.

### Decision 5: Strip all non-alphanumeric characters for unit matching

Replace `str(unit).upper().replace(" ", "_")` with a regex that strips ALL non-alphanumeric characters. This handles dots (`W·h`), hyphens (`watt-hour`), unicode middle-dots, spaces, and any other separator. After stripping, the match sets use underscore-free forms: `"WH"`, `"WATTHOUR"`, `"WATTHOURS"`, etc.

## Risks / Trade-offs

- **[False positive on magnitude heuristic]** → A commercial installation with >100 MWh cumulative could be incorrectly converted. **Mitigation**: The threshold is high enough that residential installs (our target) won't hit it. Document the threshold in config.default.yaml for override.
- **[Backward compat with existing kWh sensors]** → Sensors that correctly report kWh with no unit attribute could be affected if they have high values. **Mitigation**: 100,000 kWh threshold is extremely high for residential; normal homes are 5–30 MWh lifetime.
