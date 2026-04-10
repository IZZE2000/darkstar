## 1. Preserve original slot before EV override

- [x] 1.1 In `engine.py` `_execute_tick`, save `original_slot = slot` before the EV source isolation block (line ~1222) that creates a new SlotPlan with `discharge_kw=0`
- [x] 1.2 Pass `original_slot` to `_create_execution_record` for the planned value fields, keep modified `slot` for `make_decision`
- [x] 1.3 Add test: when source isolation is active, `planned_discharge_kw` in the execution record matches the original schedule value (not 0)

## 2. Populate ev_charging_kw in execution record

- [x] 2.1 In `_create_execution_record`, add `ev_charging_kw=original_slot.ev_charging_kw` (the field already exists in `ExecutionRecord` and DB model)
- [x] 2.2 Add DB migration for `ev_charging_kw` column on `execution_log` table if not already present
- [x] 2.3 Add test: execution record includes correct `ev_charging_kw` value from the original slot

## 3. EV charge failure detection

- [x] 3.1 Add instance variables to executor: `_ev_zero_power_ticks: int = 0` and `_ev_failure_notified: bool = False`
- [x] 3.2 In the EV source isolation block, increment `_ev_zero_power_ticks` when `scheduled_ev > 0.1` and `actual_ev < 0.1`; reset to 0 when actual > 0.1
- [x] 3.3 When `_ev_zero_power_ticks >= 5` and not yet notified, call `dispatcher.notify_error()` with descriptive message, set `_ev_failure_notified = True`, and mark the tick result as failed
- [x] 3.4 Reset both `_ev_zero_power_ticks` and `_ev_failure_notified` to 0/False when `scheduled_ev <= 0.1` (EV slot ended)
- [x] 3.5 Add test: after 5 ticks of zero actual power, error notification is sent and execution record has `success=0`
- [x] 3.6 Add test: counter resets when EV slot ends, so next EV slot gets a fresh count
- [x] 3.7 Add test: error fires only once per EV charging period (not every tick after threshold)

## 4. EV isolation reason in execution record

- [x] 4.1 When source isolation is active and no real override is active, set `override_reason` on the execution record to a string like `"EV source isolation: {scheduled}kW scheduled, {actual}kW actual"`
- [x] 4.2 Add test: `override_reason` is populated when isolation is active and no override
- [x] 4.3 Add test: real override reason takes precedence when both are active
