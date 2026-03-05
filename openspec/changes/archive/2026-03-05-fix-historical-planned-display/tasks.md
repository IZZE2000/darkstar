## 1. Fix Charge/Discharge Display Logic

- [x] 1.1 Update `charge` array in ChartCard.tsx to always use `battery_charge_kw` (remove conditional actual check)
- [x] 1.2 Update `discharge` array in ChartCard.tsx to always use `battery_discharge_kw` (remove conditional actual check)
- [x] 1.3 Verify `actualCharge` and `actualDischarge` arrays remain unchanged (they already show actual values)

## 2. Fix PV/Load Display Logic

- [x] 2.1 Update `pv` array in ChartCard.tsx to always use `pv_forecast_kwh` (remove conditional actual check)
- [x] 2.2 Update `load` array in ChartCard.tsx to always use `load_forecast_kwh` (remove conditional actual check)
- [x] 2.3 Verify `actualPv` and `actualLoad` arrays remain unchanged

## 3. Fix Other Metrics Display Logic

- [x] 3.1 Update `water` array to always use `water_heating_kw` (remove conditional actual check)
- [x] 3.2 Update `evCharging` array to always use `ev_charging_kw` (remove conditional actual check)
- [x] 3.3 Update `exp` (export) array to always use `export_kwh` (remove conditional actual check)
- [x] 3.4 Verify all corresponding `actual*` arrays remain unchanged

## 4. Verification

- [x] 4.1 Build frontend and verify no TypeScript errors
- [x] 4.2 Verify chart displays planned values as solid lines/bars through entire 48h window
- [x] 4.3 Verify dotted overlay lines show actual values for historical slots only
- [x] 4.4 Run lint script (`./scripts/lint.sh`) and fix any issues
