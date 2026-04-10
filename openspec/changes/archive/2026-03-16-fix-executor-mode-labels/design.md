## Context

The Executor page shows execution history with summary badges and a "next slot" preview. Currently:

- The **next slot** preview checks `charge_kw`, `export_kw`, and `water_kw` to show badges, and falls back to a hardcoded `"Idle / Self-consumption"` string when all are zero — lumping two opposite modes together.
- The **history badges** check for the legacy Deye string `'Export First'` for export detection and use `commanded_charge_current_a > 0` for charge detection. Everything else shows `"— Idle"`. Self-consumption executions are mislabeled as idle.
- The `current_slot_plan` status API returns `charge_kw`, `export_kw`, `water_kw`, `soc_target`, `soc_projected` — but no mode intent.

The executor already stores `commanded_work_mode` as the mode intent string (`charge`, `self_consumption`, `idle`, `export`) in the execution log. The history records already have this data — the frontend just doesn't use it.

## Goals / Non-Goals

**Goals:**
- Every execution in the history shows the correct primary mode badge (one of four: Charge, Self-consumption, Idle, Export)
- Context badges (Water, EV) appear alongside the primary mode when those actions are active
- The next-slot preview shows the planned mode intent, not a guess from values
- Mode display is profile-agnostic — works for Fronius, Deye, Sungrow, and any future profile

**Non-Goals:**
- Changing how the controller decides modes (that's Issue 1 territory)
- Showing inverter-specific mode names (e.g. "Block Discharging", "Export First") in the UI — we use our four canonical intents
- Changing the expanded detail view of execution records (only the summary badges and next-slot preview)

## Decisions

### Decision: Use `commanded_work_mode` directly for history badges

The execution log already stores `commanded_work_mode` as the mode intent string. The frontend should switch from value-based heuristics to reading this field directly.

**Alternative considered**: Deriving mode from planned values in the frontend. Rejected because it duplicates controller logic and would break for future profiles with different mode mappings.

### Decision: Compute mode_intent server-side for next-slot preview

`get_status()` in `engine.py` already loads the current slot plan. It should additionally instantiate the Controller with current system state and run `decide()` to get the mode intent, then include `mode_intent` in the `current_slot_plan` response.

**Alternative considered**: Adding mode_intent to the schedule.json output from the planner. Rejected because the mode depends on real-time state (current SoC vs target), not just the plan values. The controller must evaluate it at display time.

**Trade-off**: This means `get_status()` needs access to the controller, system state, and profile — adding a lightweight dependency. But the executor already has all of these, so it's just wiring.

### Decision: Four fixed badge styles

| mode_intent | Emoji | Label | Color class |
|---|---|---|---|
| `charge` | ⚡ | Charge | `text-good bg-good/20` |
| `self_consumption` | 🔄 | Self-consumption | `text-blue-400 bg-blue-400/20` |
| `idle` | ⏸️ | Idle | `text-muted bg-surface2/50` |
| `export` | ↗️ | Export | `text-warn bg-warn/20` |

Context badges (shown alongside primary):

| Condition | Emoji | Label | Color class |
|---|---|---|---|
| `planned_water_kw > 0` | 💧 | Heating | `text-water bg-water/20` |
| EV charging active | 🔌 | EV | `text-purple-400 bg-purple-400/20` |

### Decision: Detect EV charging from `commanded_work_mode`

For history records, EV charging is already logged as separate records with `commanded_work_mode: "ev_charge_start"` / `"ev_charge_stop"`. For the regular tick records, we check `planned_discharge_kw == 0` combined with the mode being `idle` — but this is fragile. Instead, we should add `ev_charging_kw` to the execution record so the frontend can check `ev_charging_kw > 0` directly. This is already in `SlotPlan` but not logged.

For the next-slot preview, `ev_charging_kw` is already in the slot data from schedule.json and should be included in `current_slot_plan`.

## Risks / Trade-offs

- **[Risk] get_status() becomes heavier** → The controller `decide()` call is pure computation (no I/O), so overhead is negligible. If system state isn't available (HA offline), fall back to no mode_intent.
- **[Risk] Old execution records have no `commanded_work_mode`** → Records from before the mode_intent migration might have null/legacy values. The frontend should handle null gracefully by showing no primary badge (just like today's fallback, but without the misleading label).
