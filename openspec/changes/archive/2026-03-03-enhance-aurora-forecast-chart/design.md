## Context

The Aurora Forecast Horizon chart displays PV production forecasts from the Aurora ML model (P10, P50, P90 confidence bands). However, users cannot compare these forecasts against:
1. The raw Open-Meteo weather model that Aurora uses as input
2. Historical actual PV production (the "Actual" line exists but data isn't populated)

The chart currently uses a rolling 24h±24h window from current time, which means:
- Past actuals become invisible as time progresses
- The window isn't anchored to calendar days

## Goals / Non-Goals

**Goals:**
- Display Open-Meteo-derived PV forecast as a comparison baseline
- Show per-array forecasts for systems with multiple solar arrays
- Make historical actuals visible in a fixed 48h window (00:00 today → 00:00 tomorrow)
- Preserve existing legend click-to-toggle behavior

**Non-Goals:**
- Changing the Aurora ML forecast algorithm
- Adding new configuration options
- Modifying other charts or dashboard cards

## Decisions

### D1: Fixed 48h Window Anchored to Calendar Days

**Decision:** Change from rolling window (`now ± 24h`) to fixed window (`00:00 today → 00:00 tomorrow`).

**Rationale:**
- Users expect to see "today and tomorrow" in a predictable format
- Historical actuals become visible and stay visible throughout the day
- Simpler mental model: "Show me the 48-hour forecast starting today"

**Implementation:**
```python
# Backend: aurora_dashboard()
tz = engine.timezone
now = datetime.now(tz)
start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
horizon_end = start_of_today + timedelta(days=2)  # 00:00 day after tomorrow
# Actually: we want 00:00 today to 00:00 tomorrow = 24h
# User said "48h view" but 00:00 today to 00:00 tomorrow is 24h
# Re-reading: "from 00:00 today to 00:00 tomorrow so we always have 48h view"
# This doesn't add up - 00:00 today to 00:00 tomorrow = 24h
# User likely means: 00:00 today to 00:00 day-after-tomorrow = 48h
horizon_start = start_of_today
horizon_end = start_of_today + timedelta(days=2)
```

### D2: Open-Meteo PV Calculation Formula

**Decision:** Use the standard PV estimation formula:

```python
PV_kWh = (radiation_W_m2 / 1000) * capacity_kW * efficiency * 0.25h
```

Where:
- `radiation_W_m2` = `shortwave_radiation` from Open-Meteo (W/m²)
- `capacity_kW` = sum of `kwp` from all `solar_arrays` in config
- `efficiency` = system efficiency factor (default 0.85, accounts for inverter, wiring, temperature losses)
- `0.25h` = 15-minute slot duration

**Rationale:**
- Simple, physics-based estimation
- Uses data already fetched by `get_weather_series()`
- No additional API calls needed

**Alternative Considered:** Use `global_tilted_irradiance` (GTI) with tilt/azimuth params
- **Rejected:** Adds complexity, requires per-array tilt/azimuth API params, not significantly more accurate for this comparison purpose

### D3: Per-Array Display as Dashed Lines

**Decision:** Show sum of all arrays as solid line, individual arrays as dashed lines.

**Rationale:**
- Sum line is the primary comparison point with Aurora forecast
- Per-array lines help identify which array contributes most
- Dashed style differentiates from the main line
- Users can toggle visibility via legend click

**Implementation:**
- Solid line: `open_meteo_kwh` (sum)
- Dashed lines: `open_meteo_arrays[{name: "Main Array", kwh: ...}, ...]`

### D4: Color Using Design System Variable

**Decision:** Use `--color-warn` (Amber `#F59E0B`) for Open-Meteo line.

**Rationale:**
- Distinct from existing green (PV) and orange (load) colors
- Warn/amber indicates "external data source" vs Aurora's "processed data"
- Uses design system variable instead of hardcoded hex

### D5: Backend Data Structure

**Decision:** Extend `AuroraHorizonSlot` type:

```typescript
interface AuroraHorizonSlot {
  // ... existing fields ...
  open_meteo_kwh: number | null  // Sum of all arrays
  open_meteo_arrays?: {
    name: string
    kwh: number
  }[]
}
```

Extend `AuroraHorizon` type:

```typescript
interface AuroraHorizon {
  // ... existing fields ...
  history_series?: {
    pv: {
      slot_start: string
      actual: number | null
      // Aurora forecasts already exist
    }[]
    load: { ... }
  }
}
```

**Rationale:**
- Minimal API surface change
- Frontend can render per-array lines from single data structure
- History series populated from `SlotObservation` table

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Open-Meteo radiation data gaps | Graceful fallback: show null for missing slots, line will have gaps |
| Performance impact of additional calculations | Reuse existing `get_weather_series()` call; PV calc is O(n) simple math |
| Multiple arrays with different tilt/azimuth | Document that sum uses simplified model; per-array shown for reference |
| Timezone edge cases (DST transitions) | Use timezone-aware datetime throughout; test with Europe/Stockholm |

## Migration Plan

1. **Backend changes first** - No breaking changes, just additional fields
2. **Frontend updates** - Consumes new fields, falls back gracefully if missing
3. **No database migration** - Using existing tables and data

**Rollback:** Frontend can check for null/missing `open_meteo_kwh` and omit the line.
