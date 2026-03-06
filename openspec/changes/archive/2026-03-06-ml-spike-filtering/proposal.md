## Why

The sensor-spike-protection change implemented spike filtering for backend analytical paths (Analyst, Reflex, Metrics) but missed the ML training and evaluation code paths. As a result, ML models are being trained on corrupted data containing impossible energy values (e.g., 2,373 kWh in a 15-minute slot), causing unrealistic forecasts that predict thousands of kWh when the physics model predicts ~22 kWh.

## What Changes

- Add spike filtering to `ml/train.py` `_load_slot_observations()` to exclude rows where `pv_kwh` or `load_kwh` exceeds the config-derived threshold
- Add spike filtering to `ml/corrector.py` `_load_training_frame()` and `_compute_hourly_bias_stats()` for error correction model training
- Add spike filtering to `ml/evaluate.py` `_compute_mae()` to ensure evaluation metrics exclude corrupted data

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `energy-recording`: Extends the "Analytical pipelines filter spike rows at read time" requirement to include ML training, correction, and evaluation paths. These paths now join Analyst, Reflex, and Metrics as read-time filtered consumers of `slot_observations`.

## Impact

- **ml/train.py**: Import `get_max_energy_per_slot()`, add WHERE clause to `_load_slot_observations()` query
- **ml/corrector.py**: Import `get_max_energy_per_slot()`, add WHERE clauses to `_load_training_frame()` and `_compute_hourly_bias_stats()` queries
- **ml/evaluate.py**: Import `get_max_energy_per_slot()`, add WHERE clause to `_compute_mae()` query
- **openspec/specs/energy-recording/spec.md**: Add three new scenarios for ML spike filtering
