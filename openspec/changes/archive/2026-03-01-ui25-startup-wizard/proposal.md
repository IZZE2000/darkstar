## Why

Currently, new users fall back to a perfectly flat dummy load profile in Darkstar, which ruins the Kepler solver's ability to plan for daily peaks. Additionally, they face a massive settings page and don't know where to start setting up their system.

## What Changes

* Change the default `config.default.yaml` entry for `system.inverter_profile` to `null` to serve as a trigger.
* Implement a full-screen Startup Wizard overlay in the React frontend.
* Add three mandatory setup steps: Hardware Profile selection, Equipment Specifications (Battery/PV), and Baseline Consumption (HA sensor or Synthetic).
* Add backend support to process and scale Synthetic Heat Pump profiles.

## Capabilities

### New Capabilities
- `startup-wizard`: Mandatory configuration overlay for new installations.
- `synthetic-profile-generation`: Backend logic to generate realistic load curves based on estimated daily usage.

### Modified Capabilities
- `configuration-validation`: Rejects dashboard access until minimal profile data is present.

## Impact

- `frontend/src/App.tsx`: Add router interception or layout wrapper for the wizard modal.
- `frontend/src/pages/settings/components/ProfileSetupHelper.tsx`: Refactor logic to be reusable in the wizard.
- `config.default.yaml`: Update default state.
- `inputs.py`: Add synthetic load profile generation logic.
