## Why

Users cannot fully disable EV charging by toggling off `system.has_ev_charger`. The WebSocket listener in `ha_socket.py` checks this flag once at initialization but does not re-evaluate when config is reloaded. After toggling off and running new planning, the WebSocket monitor continues tracking EV charger entities based on stale state, causing the system to still control charging.

## What Changes

- Make `ha_socket.py` re-evaluate `system.has_ev_charger` on config reload, tearing down EV charger monitoring when the flag is set to false
- Ensure the system-level toggle acts as a proper master gate: when `has_ev_charger` is false, no EV entities are monitored regardless of per-charger `enabled` flags

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `ev-charging-replan`: Add requirement that WebSocket EV monitoring respects config reload of `system.has_ev_charger`

## Impact

- **Backend**: `backend/ha_socket.py` — config reload must tear down/rebuild EV monitoring
- **Executor**: No changes needed — already checks `has_ev_charger` at runtime correctly
- **Planner**: No changes needed — already checks `has_ev_charger` correctly
- **Frontend**: No changes needed
