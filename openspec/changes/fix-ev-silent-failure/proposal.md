## Why

EV charging energy silently leaks into "actual_load" bars because the recorder subtracts a power snapshot × 0.25h from a precise cumulative delta — any timing mismatch (charger finishes mid-slot, sensor latency, executor race) means the subtraction is 0 and 100% of EV energy contaminates house load training data. Additionally, the ChartCard dataset visibility indices are misaligned, causing the EV overlay to be toggled by the Export button and making the EV overlay button non-functional.

## What Changes

- **ChartCard.tsx**: Fix dataset visibility index mismatch — three wrong index assignments and one missing assignment (Actual Water) in the overlay visibility control block.
- **`config.default.yaml`**: Add optional `energy_sensor: ''` field to both `ev_chargers[]` and `water_heaters[]` default entries.
- **`backend/recorder.py`**: When `energy_sensor` is configured for an EV charger or water heater, compute energy delta from cumulative HA sensor readings (same approach as total load). Fall back to snapshot × 0.25h only when no energy sensor is configured. Add `ev_charging_kwh` to the "Recording observation" log line.
- **Health check**: Emit a WARNING if any enabled EV charger or water heater has `energy_sensor` empty — surfaced in the `/api/health` response and the UI yellow banner.
- **Settings UI**: Add "Energy sensor" field in the EV and Water tabs, positioned next to the existing "Power sensor" field. Update the Power sensor tooltip. Add "?" tooltip for Energy sensor.
- **Docs**: Update `docs/ARCHITECTURE.md` sections 5.5, 12.2, and 12.5 to reflect the new energy isolation approach.

## Capabilities

### New Capabilities

- `ev-water-energy-sensor`: Optional per-device `energy_sensor` field for EV chargers and water heaters — enables accurate cumulative energy isolation in the recorder, health check validation, and Settings UI configuration.

### Modified Capabilities

- `energy-recording`: EV and water heater energy isolation now uses cumulative sensor delta when `energy_sensor` is configured; snapshot fallback retained for unconfigured devices.
- `dashboard-ev-display`: Fix ChartCard dataset visibility index mismatch so EV and Export overlays toggle their correct datasets.
- `sensor-configuration`: Settings UI gains "Energy sensor" field for EV chargers and water heaters.

## Impact

- `frontend/src/components/ChartCard.tsx` — overlay visibility logic
- `config.default.yaml` — new optional fields
- `backend/recorder.py` — isolation path for ev_charging_kwh and water_kwh
- `backend/health.py` — new WARNING check
- `frontend/src/pages/settings/types.ts` — new field definitions
- `docs/ARCHITECTURE.md` — documentation updates
