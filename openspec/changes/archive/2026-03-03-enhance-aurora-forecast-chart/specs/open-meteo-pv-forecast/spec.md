## ADDED Requirements

### Requirement: Open-Meteo PV Forecast Display

The Aurora Forecast Horizon chart SHALL display an Open-Meteo-derived PV production forecast line alongside the Aurora ML forecast, allowing users to compare the raw weather model output with Aurora's ML-enhanced predictions.

#### Scenario: Open-Meteo line visible in PV mode
- **WHEN** user views the Aurora Forecast Horizon chart in PV mode with probabilistic mode enabled
- **THEN** the chart SHALL display a solid amber line labeled "Open-Meteo" showing PV production estimates derived from Open-Meteo radiation data

#### Scenario: Open-Meteo line toggleable via legend
- **WHEN** user clicks the "Open-Meteo" label in the chart legend
- **THEN** the Open-Meteo line SHALL toggle visibility (hide if shown, show if hidden)

### Requirement: Per-Array Forecast Lines

The chart SHALL display individual dashed lines for each configured solar array's Open-Meteo forecast, enabling users to understand per-array contributions.

#### Scenario: Multiple arrays shown as dashed lines
- **WHEN** the system configuration contains multiple solar arrays
- **THEN** the chart SHALL display a dashed line for each array using the array's name as the label

#### Scenario: Single array shows one dashed line
- **WHEN** the system configuration contains a single solar array
- **THEN** the chart SHALL display one dashed line for that array

#### Scenario: Per-array lines toggleable via legend
- **WHEN** user clicks an array name label in the chart legend
- **THEN** that array's dashed line SHALL toggle visibility

### Requirement: Fixed 48-Hour Window

The Forecast Horizon chart SHALL use a fixed time window from 00:00 today to 00:00 the day after tomorrow (48 hours total), anchored to calendar days rather than the current time.

#### Scenario: Window anchored to calendar days
- **WHEN** user views the Forecast Horizon chart at any time during a day
- **THEN** the chart SHALL display data from 00:00 today to 00:00 the day after tomorrow

#### Scenario: Window resets at midnight
- **WHEN** the current time crosses midnight
- **THEN** the chart window SHALL shift to show the new "today" through "day after tomorrow"

### Requirement: Historical Actuals Visible

The chart SHALL display historical actual PV production data in the "Actual" line for past time slots within the fixed 48-hour window.

#### Scenario: Actual line shows past production
- **WHEN** historical PV production data exists for past slots within the 48-hour window
- **THEN** the chart SHALL display the "Actual" line with observed PV values for those slots

#### Scenario: Actual line gaps for missing data
- **WHEN** historical PV production data is missing for some past slots
- **THEN** the Actual line SHALL have gaps (null values) for those slots rather than showing zero

### Requirement: Open-Meteo PV Calculation

The backend SHALL calculate PV production estimates from Open-Meteo radiation data using the formula:

```
PV_kWh = (radiation_W_m2 / 1000) * capacity_kW * efficiency * 0.25h
```

Where:
- `radiation_W_m2` = shortwave radiation from Open-Meteo (W/m²)
- `capacity_kW` = sum of kwp from all solar_arrays in config
- `efficiency` = system efficiency (default 0.85)
- `0.25h` = 15-minute slot duration

#### Scenario: PV calculated from radiation
- **WHEN** Open-Meteo radiation data is available for a time slot
- **THEN** the system SHALL calculate PV estimate using the specified formula

#### Scenario: Per-array capacity used for individual lines
- **WHEN** calculating per-array PV estimates
- **THEN** the system SHALL use that array's `kwp` value instead of the total sum

#### Scenario: Null returned for missing radiation data
- **WHEN** Open-Meteo radiation data is unavailable for a time slot
- **THEN** the system SHALL return null for that slot's Open-Meteo PV estimate
