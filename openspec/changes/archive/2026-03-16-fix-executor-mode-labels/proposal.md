## Why

The Executor page's Execution History displays misleading mode labels. The "next slot" preview shows a hardcoded "Idle / Self-consumption" fallback for any slot without charge/export/water — treating two opposite modes as the same thing. History badges check for legacy Deye-era strings (`'Export First'`) and fall through to "— Idle" for everything else, so self-consumption executions are mislabeled as idle. A Fronius beta tester reported confusion when the forecast showed planned discharge but the UI showed what appeared to be "Block Discharging." The actual inverter was correct — but the UI was wrong.

## What Changes

- **Next slot preview**: Compute and expose the controller's `mode_intent` for the upcoming slot so the frontend can display the actual planned mode instead of guessing from values.
- **History badges**: Replace the value-based badge logic with mode-intent-driven badges. Four primary mode badges (Charge, Self-consumption, Idle, Export) with emoji and color, shown for every execution. Additional context badges (Water heating, EV charging) shown alongside when active.
- **Remove legacy checks**: Remove the `'Export First'` string check and the catch-all "— Idle" fallback from the badge logic.
- **Status API**: Add `mode_intent` field to the `current_slot_plan` object returned by the executor status endpoint.

## Capabilities

### New Capabilities

- `executor-mode-display`: Frontend display of executor mode badges and next-slot mode preview in the Executor page.

### Modified Capabilities

- `executor`: The status API's `current_slot_plan` object gains a `mode_intent` field computed by running the controller decision for the upcoming slot.

## Impact

- **Backend**: `executor/engine.py` — `get_status()` method needs to run `Controller.decide()` for the current slot and include `mode_intent` in `current_slot_plan`.
- **Frontend**: `frontend/src/pages/Executor.tsx` — next-slot display and history badge rendering logic.
- **No breaking changes**: The `mode_intent` field is additive to the status API.
