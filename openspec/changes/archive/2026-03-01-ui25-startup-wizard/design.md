## Context

Currently, new Darkstar users without initial setup data fall back to a perfectly flat dummy load profile. This prevents the Kepler solver from functioning correctly. Users are dropped into a complex Settings page without guidance on how to configure their inverter, battery, or solar arrays. We need a mandatory, streamlined onboarding experience.

## Goals / Non-Goals

**Goals:**
- Intercept users on first load if `config.system.inverter_profile` is `null`.
- Provide a 3-step wizard to collect minimum required data: Equipment Profile, Hardware Specs, and Baseline Consumption.
- Generate a synthetic load profile if the user opts out of providing a Home Assistant historical sensor for baseline consumption.
- Save the configuration and trigger an executor reload.

**Non-Goals:**
- Configuring advanced features like EV chargers, water heaters, or pricing in this initial wizard.
- Modifying the core Kepler solver logic; this change focuses entirely on pre-requisite telemetry.

## Decisions

### Decision 1: Trigger Mechanism
We will use React Router or a high-level layout wrapper in `App.tsx` to check `config.system.inverter_profile`. If `null`, it renders the `StartupWizard` full-screen modal instead of `<Outlet />`. The default `config.default.yaml` will be updated to `inverter_profile: null`.

### Decision 2: Profile Setup
We will reuse and refactor the existing `ProfileSetupHelper` configuration injection logic to populate the default HA entities when a user selects a branded hardware profile (Deye, Fronius, etc.).

### Decision 3: Synthetic Profile Generation
When a user does not have a 7-day historical total load sensor to bind to, they will enter an "Estimated Daily kWh". The backend (`inputs.py`) will mathematically scale a predefined normalized "Synthetic Heat Pump Profile" curve so its integral matches the user's daily estimate, avoiding a flat line.

## Risks / Trade-offs
- **State Blocking:** If the API fails to save the config, the user remains permanently locked in the wizard. We must ensure robust error handling and API fallback.
- **Synthetic Accuracy:** The synthetic curve is an approximation. We trade perfect accuracy for a functioning solver engine right out of the box.
