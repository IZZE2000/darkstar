## 1. Trigger & Infrastructure

- [x] 1.1 Change the default `config.default.yaml` entry for `system.inverter_profile` to `null`
- [x] 1.2 Create the `StartupWizard` component wrapper
- [x] 1.3 Update React Router in `frontend/src/App.tsx` to intercept users before dashboard loading and show `StartupWizard` when profile is `null`

## 2. Wizard Components

- [x] 2.1 Build Step 1 (Hardware Profile): Refactor `ProfileSetupHelper.tsx` logic for use in wizard
- [x] 2.2 Build Step 2 (Equipment Specs): Forms for Battery Capacity (kWh) and Solar Array (kWp)
- [x] 2.3 Build Step 3 (Baseline Consumption): Toggle between HA sensor select and "Estimated Daily kWh" input

## 3. Backend Logic & Integration

- [x] 3.1 Implement API call from wizard to save minimal config
- [x] 3.2 Add backend support in `inputs.py` to process "Synthetic Heat Pump Profile" if estimated usage is requested, scaling to match user's kWh input
- [x] 3.3 Ensure the backend validation accepts the minimal setup and triggers an `ExecutorEngine` reload

## 4. Testing & Polish

- [x] 4.1 Verify wizard cannot be bypassed when `inverter_profile` is `null`
- [x] 4.2 Test Synthetic Profile generation math
- [x] 4.3 Add a "Relaunch Setup Wizard" button in Settings -> System
