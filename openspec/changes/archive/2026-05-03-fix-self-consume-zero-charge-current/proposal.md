## Why

When no charge or export is planned and the battery is above target, the controller falls back to `self_consumption` mode but computes `charge_value = 0` (because `slot.charge_kw = 0`). The deye profile faithfully writes `max_charge_current = 0A` to the inverter, blocking all PV→battery charging. With no path into the battery, excess PV exports to grid — unintended and unplanned export.

## What Changes

- Controller: when in `self_consumption` mode and `charge_value` is zero (default fallback, nothing planned), use the user's configured max charge current instead of 0
- This ensures PV always charges the battery when no specific charge or export action is scheduled

## Capabilities

### New Capabilities
<!-- None needed — this is a behavior fix within existing capabilities -->

### Modified Capabilities
- `executor`: Controller's default self_consumption fallback now allows PV→battery charging by using max charge when no charge is planned

## Impact

- `executor/controller.py` — `_follow_plan()` method, after line 250 where `max_charge` is computed: override `charge_value` when mode is `self_consumption` and the computed value is ≤ 0, using the already-computed `max_charge` directly
- No profile changes, no config changes, no breaking changes
