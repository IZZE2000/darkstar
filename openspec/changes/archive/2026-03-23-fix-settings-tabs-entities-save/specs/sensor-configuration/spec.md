## ADDED Requirements

### Requirement: Profile entity fields are displayed in category-appropriate tab
The Settings UI SHALL display profile entity fields only in the tab matching the entity's `category` field. Entities with `category: "system"` SHALL appear in the System tab. Entities with `category: "battery"` SHALL appear in the Battery tab. No entity SHALL appear in both tabs.

#### Scenario: System tab shows only system-category entities
- **WHEN** a user selects an inverter profile (e.g., Fronius, Deye, Sungrow, Generic)
- **AND** navigates to Settings > System > "Required HA Control Entities"
- **THEN** only entities with `category: "system"` from that profile SHALL be displayed
- **AND** entities with `category: "battery"` SHALL NOT be displayed

#### Scenario: Battery tab shows only battery-category entities
- **WHEN** a user selects an inverter profile
- **AND** navigates to Settings > Battery > "HA Control Entities"
- **THEN** only entities with `category: "battery"` from that profile SHALL be displayed
- **AND** entities with `category: "system"` SHALL NOT be displayed

### Requirement: Custom entity keys use consistent config paths
All dynamic entity field generation SHALL use the `standardInverterKeys` set to determine config key paths. Standard entity keys SHALL map to `executor.inverter.{key}`. Non-standard (custom) entity keys SHALL map to `executor.inverter.custom_entities.{key}`. This mapping MUST be consistent between the rendered field components and the form state management.

#### Scenario: Custom battery entity change is detected as dirty
- **WHEN** a user changes a non-standard battery entity field (e.g., Fronius `grid_discharge_power`)
- **THEN** the form SHALL detect the change as dirty
- **AND** the save mechanism SHALL be available

#### Scenario: Custom entity value is saved to correct config path
- **WHEN** a user sets a non-standard entity field to a value and saves
- **THEN** the value SHALL be persisted at `executor.inverter.custom_entities.{key}` in the config
- **AND** the value SHALL be loaded correctly when the page is revisited

### Requirement: All settings tabs have a dedicated save button
Every settings tab SHALL include an always-visible save button at the bottom of the tab content, in addition to the sticky `UnsavedChangesBanner`. The save button SHALL be present regardless of whether changes have been made.

#### Scenario: Battery tab has a save button
- **WHEN** a user navigates to Settings > Battery
- **THEN** a "Save Battery Settings" button SHALL be visible at the bottom of the tab

#### Scenario: Solar tab has a save button
- **WHEN** a user navigates to Settings > Solar
- **THEN** a "Save Solar Settings" button SHALL be visible at the bottom of the tab

#### Scenario: Water tab has a save button
- **WHEN** a user navigates to Settings > Water
- **THEN** a "Save Water Settings" button SHALL be visible at the bottom of the tab

#### Scenario: EV tab has a save button
- **WHEN** a user navigates to Settings > EV
- **THEN** a "Save EV Settings" button SHALL be visible at the bottom of the tab

#### Scenario: Parameters tab has a save button
- **WHEN** a user navigates to Settings > Parameters
- **THEN** a "Save Parameter Settings" button SHALL be visible at the bottom of the tab

#### Scenario: Save button shows saving state
- **WHEN** a user clicks the save button on any settings tab
- **THEN** the button text SHALL change to "Saving..." while the save is in progress
- **AND** the button SHALL be disabled during the save operation
