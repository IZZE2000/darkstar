## 1. Expand Unit String Matching

File: `backend/core/ha_client.py`, function `_normalize_energy_to_kwh`

- [x] 1.1 Replace the unit cleaning logic on line ~138 (`str(unit).upper().replace(" ", "_")`) with: `re.sub(r'[^A-Z0-9]', '', str(unit).upper())`. Add `import re` at the top of the file if not already present. This strips ALL non-alphanumeric characters (dots, hyphens, unicode middle-dots, spaces, underscores) before matching.
- [x] 1.2 Update the match sets to use underscore-free forms (since all non-alphanumeric chars are now stripped): Wh group (÷1000): `("WH", "WATTHOUR", "WATTHOURS")` — kWh group (×1): `("KWH", "KILOWATTHOUR", "KILOWATTHOURS")` — MWh group (×1000): `("MWH", "MEGAWATTHOUR", "MEGAWATTHOURS")`. These replace the existing match sets on lines ~140-145.

## 2. Add Magnitude-Based Heuristic for Missing Units

File: `backend/core/ha_client.py`, function `_normalize_energy_to_kwh`

- [x] 2.1 Replace the early return on lines ~135-136 (`if not unit: return value`) with magnitude-based detection: if `unit` is None or empty string AND `value > 100_000`, return `value / 1000.0` (assume Wh). Otherwise return `value` as-is (assume kWh). The threshold is strictly greater-than: a value of exactly 100,000 should be treated as kWh.

## 3. Add Normalization Logging

File: `backend/core/ha_client.py`, function `_normalize_energy_to_kwh`. The file already has `import logging` and `logger = logging.getLogger("darkstar.core.ha_client")` — do NOT add these again.

- [x] 3.1 Add logging for every code path in `_normalize_energy_to_kwh`:
  - Unit detected from attribute → `logger.debug("Energy normalization: %s %s → %s kWh (from unit_of_measurement)", value, unit, result)`
  - No unit, value > 100k (Wh inferred from magnitude) → `logger.info("Energy normalization: %s (no unit) → %s kWh (Wh inferred from magnitude)", value, result)`
  - No unit, value ≤ 100k (kWh assumed) → `logger.debug("Energy normalization: %s (no unit) → %s kWh (assumed kWh)", value, value)`
  - Unknown unit string (no match in any group) → `logger.warning("Energy normalization: unknown unit '%s' for value %s, assuming kWh", unit, value)`

## 4. Add Daily Total Sanity Bound

File: `backend/core/ha_client.py`, function `get_load_profile_from_ha`

- [x] 4.1 After `total_daily = sum(daily_profile)` (line ~513) and BEFORE the existing `if total_daily <= 0:` check (line ~514), insert a new check: if `total_daily > 500`, log a warning and return `get_dummy_load_profile(config)`. Use print to match the existing logging style in this function: `print(f"Warning: Daily total {total_daily:.1f} kWh/day for {entity_id} exceeds 500 kWh sanity bound, using dummy profile")`

## 5. Propagate Unit from First HA History State

File: `backend/core/ha_client.py`, function `get_load_profile_from_ha`

This is the primary fix. The HA `/api/history/period` endpoint only includes `attributes` (including `unit_of_measurement`) on the **first** state entry in the response. All subsequent entries have `attributes: {}`. Without unit propagation, the second state onwards passes `unit=None` to `_normalize_energy_to_kwh`, causing inconsistent normalization (first value divided by 1000, rest left raw → catastrophic delta spike).

- [x] 5.1 Before the `for state in states:` loop (line ~460), initialize a variable: `cached_unit: str | None = None`
- [x] 5.2 Inside the loop, after `unit = attributes.get("unit_of_measurement")` (line ~475), add: if `unit` is not None and not empty string, update `cached_unit = unit`. Then on the next line, if `unit` is None or empty string, set `unit = cached_unit`. This must happen BEFORE the call to `_normalize_energy_to_kwh` on line ~476. The result is that the unit from the first state entry (or any later entry that provides one) is reused for all subsequent entries that lack attributes.
- [x] 5.3 Do NOT change `_normalize_energy_to_kwh` itself — the magnitude heuristic stays as a safety net for other callers and for cases where even the first state lacks a unit.

## 6. Unit Tests for Normalization

File: `tests/backend/test_energy_normalization.py` (already created by prior tasks)

- [x] 6.1 Add unit tests for `_normalize_energy_to_kwh` (import from `backend.core.ha_client`). Test ALL of the following scenarios with exact expected values:
  - `("Wh", 500000)` → `500.0` (standard Wh)
  - `("WH", 500000)` → `500.0` (uppercase Wh)
  - `("wh", 500000)` → `500.0` (lowercase Wh)
  - `("kWh", 500.0)` → `500.0` (standard kWh)
  - `("KWH", 500.0)` → `500.0` (uppercase kWh)
  - `("MWh", 0.5)` → `500.0` (standard MWh)
  - `("MWH", 0.5)` → `500.0` (uppercase MWh)
  - `("W·h", 500000)` → `500.0` (unicode middle-dot variant)
  - `("W h", 500000)` → `500.0` (space-separated variant)
  - `("watthour", 500000)` → `500.0` (lowercase full word)
  - `("watt-hour", 500000)` → `500.0` (hyphenated variant)
  - `("WATT_HOUR", 500000)` → `500.0` (underscore variant — existing format)
  - `("kilowatt-hours", 500.0)` → `500.0` (hyphenated kWh variant)
  - `(None, 5675983)` → `5675.983` (no unit, high value → Wh inferred)
  - `("", 5675983)` → `5675.983` (empty unit, high value → Wh inferred)
  - `(None, 500.0)` → `500.0` (no unit, low value → kWh assumed)
  - `(None, 100000)` → `100000` (boundary: exactly at threshold → kWh assumed)
  - `(None, 100001)` → `100.001` (boundary: just above threshold → Wh inferred)
  - `("BTU", 500.0)` → `500.0` (unknown unit → kWh assumed)

## 7. Integration Test for Sanity Bound

File: `tests/backend/test_energy_normalization.py` (same file as task 6)

- [x] 7.1 Add an async test for the sanity bound in `get_load_profile_from_ha`. Mock the HA API (`httpx.AsyncClient.get`) to return history states that produce a daily average total exceeding 500 kWh. Verify the function returns a dummy profile (same result as `get_dummy_load_profile`). Use the existing test patterns from `tests/backend/test_ha_client_power_history.py` as reference for mocking the HA API.

## 8. Tests for Unit Propagation

File: `tests/backend/test_energy_normalization.py` (same file as tasks 6–7)

- [x] 8.1 Add an async test: mock HA API to return a history response where the first state has `attributes: {"unit_of_measurement": "Wh"}` and all subsequent states (at least 5) have `attributes: {}`. All states should have cumulative Wh values (e.g., `5675983`, `5675993`, `5676003`, ...). Verify the returned daily profile has a reasonable `total_daily` (well under 500 kWh) — NOT the millions-of-kWh result that would occur without propagation.
- [x] 8.2 Add an async test: mock HA API to return a history response where NO state entry has `unit_of_measurement` (all `attributes: {}`), and all values are large (> 100,000). Verify the magnitude heuristic fires as fallback and the daily profile total is reasonable.
- [x] 8.3 Add an async test: mock HA API where the first state has `unit_of_measurement: "Wh"`, middle states have empty attributes, and a later state introduces `unit_of_measurement: "kWh"` (sensor reconfigured). Verify the function does not error and produces a profile (exact values less important — just verify no crash and the profile has reasonable magnitude).

## 9. Lint

- [x] 9.1 Run `./scripts/lint.sh` and fix any failures introduced by the changes in tasks 5 and 8. Do NOT fix pre-existing lint issues in unrelated code.
