## Context

The executor module (`executor/config.py`) uses `import yaml` (PyYAML, YAML 1.1) to read `config.yaml`. The rest of the codebase (backend, config migration) uses `ruamel.yaml` (YAML 1.2). In YAML 1.1, unquoted `HH:MM` values are interpreted as base-60 (sexagesimal) integers: `16:00` → `960`, `17:00` → `1020`. This silently breaks the EV departure time feature — the planner's `calculate_ev_deadline()` fails to parse `"960"` as `HH:MM` and returns `None`, removing the deadline constraint entirely.

## Goals / Non-Goals

**Goals:**
- Eliminate the YAML 1.1 sexagesimal misparse of departure times in the executor
- Handle already-corrupted config values (integer `960` on disk) gracefully
- Add a defensive fallback in the planner so a numeric departure_time never silently becomes `None`
- Fix the placeholder UX in the frontend departure time field

**Non-Goals:**
- Migrating existing corrupted config files on disk (beta users will re-enter the value)
- Changing the deadline calculation logic (`calculate_ev_deadline`) — it is correct
- Date-specific or multi-day EV charging (backlog item)
- Long-term price forecasting for multi-day planning (backlog item)

## Decisions

### D1: Switch executor YAML loader from PyYAML to ruamel.yaml

**Choice:** Replace `import yaml` / `yaml.safe_load()` in `executor/config.py` with `from ruamel.yaml import YAML` using `YAML(typ='safe')`.

**Why:** ruamel.yaml is already a project dependency (used by backend, config_migration, reflex). Using `typ='safe'` returns plain Python dicts/lists (same as PyYAML's `safe_load`), so no code changes needed beyond the import and load call. YAML 1.2 does not have sexagesimal parsing, so `16:00` stays as the string `"16:00"`.

**Alternative considered:** Quoting the value on the write side. Rejected because it only fixes future writes — doesn't help if a user hand-edits config.yaml or if existing corrupted values need to be read.

### D2: Defensive integer-to-HH:MM converter

**Choice:** Add a `_parse_departure_time(value)` helper in `executor/config.py` that:
1. If value is `None` or empty → return `None`
2. If value is `int` → convert: `f"{value // 60:02d}:{value % 60:02d}"` (with range validation 0–1439)
3. If value is `str` → return as-is

Also add the same integer handling in `planner/pipeline.py`'s `calculate_ev_deadline()` as a belt-and-suspenders fallback: if `departure_time` is an `int`, convert it before parsing.

**Why:** Handles existing corrupted config files where `960` is already stored as an integer. Also defends against any future YAML parser inconsistency.

### D3: Frontend placeholder text

**Choice:** Change `placeholder="07:00"` to `placeholder="e.g. 07:00"` in `EntityArrayEditor.tsx`.

**Why:** Current placeholder looks like pre-filled data. Adding "e.g." makes it clearly an example.

## Risks / Trade-offs

- **[Risk] ruamel.yaml `typ='safe'` returns slightly different types for edge cases** → Mitigation: the executor config loader already uses explicit type coercion (`float()`, `bool()`, `str()`) on every field, so intermediate types don't matter.
- **[Risk] Integer conversion produces invalid times for out-of-range values (e.g., 9999)** → Mitigation: range check 0–1439 in the converter; return `None` for invalid values.
- **[Risk] executor/profiles.py also uses `import yaml`** → Mitigation: Out of scope for this change (profiles.py doesn't read departure_time). Can be addressed separately if needed.
