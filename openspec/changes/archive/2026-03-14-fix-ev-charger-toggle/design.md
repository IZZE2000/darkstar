## Context

`HAWebSocketClient._get_monitored_entities()` builds the entity→metric mapping. When `has_ev_charger` is true, it populates `self.ev_charger_configs` and `self.latest_values["ev_chargers"]`. When `has_ev_charger` is false, the `if` block is skipped — but there's no `else` branch to clear those fields.

`reload_monitored_entities()` exists and is called on config save. It rebuilds the entity mapping (correctly omitting EV sensors when `has_ev_charger` is false), but the stale `ev_charger_configs` and `latest_values["ev_chargers"]` persist, potentially confusing downstream consumers.

## Goals / Non-Goals

**Goals:**
- When `has_ev_charger` is toggled off and config is reloaded, all EV monitoring state is fully cleared
- When individual chargers are disabled and config is reloaded, only those chargers are removed from monitoring

**Non-Goals:**
- Changing the planner or executor EV logic (already correct)
- Adding a new config reload mechanism (one already exists)
- Changing the frontend settings UI

## Decisions

### Add else branch to clear EV state

**Decision:** Add an `else` branch to the `if system.get("has_ev_charger", False)` check in `_get_monitored_entities()` that clears `self.ev_charger_configs = []` and removes `ev_chargers` from `self.latest_values`.

**Why:** This is the minimal fix. The entity mapping is already rebuilt correctly (EV sensors excluded). The only gap is clearing the companion state fields. Since `_get_monitored_entities()` is called both at init and on reload, the fix works for both paths.

**Alternative considered:** Adding a separate `_teardown_ev_monitoring()` method called from `reload_monitored_entities()`. Rejected as over-engineered — the else branch is two lines and keeps the logic co-located.

## Risks / Trade-offs

[Minimal risk] → The change is additive (clearing state that should have been cleared). No existing behavior is altered when `has_ev_charger` is true.
