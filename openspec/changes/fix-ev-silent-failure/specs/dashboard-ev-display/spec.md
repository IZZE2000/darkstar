## ADDED Requirements

### Requirement: ChartCard overlay visibility indices match dataset creation order
The ChartCard component SHALL assign overlay visibility to datasets using the correct dataset indices matching the actual creation order. The creation order is fixed as: `ds[0]`=Price, `ds[1]`=PV, `ds[2]`=Load, `ds[3]`=Charge, `ds[4]`=Discharge, `ds[5]`=Export, `ds[6]`=Water, `ds[7]`=EV, `ds[8-10]`=SoC lines, `ds[11]`=Actual PV, `ds[12]`=Actual Load, `ds[13]`=Actual Charge, `ds[14]`=Actual Discharge, `ds[15]`=Actual EV, `ds[16]`=Actual Export, `ds[17]`=Actual Water.

#### Scenario: Toggling the EV overlay button shows/hides Actual EV dataset
- **WHEN** the user clicks the "EV" overlay toggle button on the chart
- **THEN** `ds[15]` (Actual EV) SHALL toggle its `hidden` property
- **AND** no other dataset SHALL change visibility

#### Scenario: Toggling the Export overlay button shows/hides Actual Export dataset
- **WHEN** the user clicks the "Export" overlay toggle button on the chart
- **THEN** `ds[16]` (Actual Export) SHALL toggle its `hidden` property
- **AND** `ds[15]` (Actual EV) SHALL NOT change visibility

#### Scenario: Toggling the Water overlay button shows/hides Actual Water dataset
- **WHEN** the user clicks the "Water" overlay toggle button on the chart
- **THEN** `ds[17]` (Actual Water) SHALL toggle its `hidden` property

#### Scenario: Each overlay toggle is independent
- **WHEN** the user toggles the EV overlay on
- **AND** then toggles the Export overlay off
- **THEN** `ds[15]` (Actual EV) SHALL be visible
- **AND** `ds[16]` (Actual Export) SHALL be hidden
- **AND** `ds[17]` (Actual Water) SHALL remain in its prior state
