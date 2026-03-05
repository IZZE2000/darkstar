## Context

The Settings page in `frontend/src/pages/settings/index.tsx` manages conditional tab visibility based on `systemFlags` state (has_solar, has_battery, has_ev_charger, has_water_heater). This state is loaded once on component mount via useEffect that fetches the config. The SystemTab uses `useSettingsForm` which already dispatches a `config-changed` event after successful save (line 291 in useSettingsForm.ts). The Settings component doesn't listen for this event, so it never updates its `systemFlags` state after save.

## Goals / Non-Goals

**Goals:**
- Make conditional tabs appear/disappear instantly when has_* toggles are saved
- Maintain clean separation of concerns
- Reuse existing event infrastructure

**Non-Goals:**
- Changing the save mechanism
- Adding new state management patterns
- Modifying tab filtering logic

## Decisions

**Decision: Use existing `config-changed` event**
- *Rationale*: The event is already dispatched by useSettingsForm.ts after save. Adding a listener in Settings component is the minimal change.
- *Alternative considered*: Lift state up via context or props - rejected as unnecessary complexity for this single synchronization need.

**Decision: Re-fetch config in event handler**
- *Rationale*: Guarantees consistency with server state
- *Alternative considered*: Derive from form state via props - rejected because Settings and SystemTab are siblings, would require significant restructuring

## Risks / Trade-offs

- [Extra API call on every save] → Acceptable trade-off for guaranteed consistency
- [Race condition if save + manual refresh happen simultaneously] → Mitigated by React state batching

## Migration Plan

No migration needed - this is a UX improvement, no breaking changes.
