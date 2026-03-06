## 1. ML Training Spike Filtering

- [x] 1.1 Import `get_max_energy_per_slot` from `backend.validation` in `ml/train.py`
- [x] 1.2 Modify `_load_slot_observations()` to calculate threshold from config
- [x] 1.3 Add `AND pv_kwh <= ? AND load_kwh <= ?` WHERE clause to query
- [x] 1.4 Add test for ML training spike filtering in `tests/ml/test_residual_training.py`

## 2. ML Correction Spike Filtering

- [x] 2.1 Import `get_max_energy_per_slot` from `backend.validation` in `ml/corrector.py`
- [x] 2.2 Modify `_load_training_frame()` to calculate threshold and add WHERE clause
- [x] 2.3 Modify `_compute_hourly_bias_stats()` to calculate threshold and add WHERE clause
- [x] 2.4 Add tests for corrector spike filtering in `tests/ml/test_corrector.py`

## 3. ML Evaluation Spike Filtering

- [x] 3.1 Import `get_max_energy_per_slot` from `backend.validation` in `ml/evaluate.py`
- [x] 3.2 Modify `_compute_mae()` to calculate threshold and add WHERE clause
- [x] 3.3 Add test for evaluation spike filtering in `tests/ml/test_evaluate.py`

## 4. Verification

- [x] 4.1 Run full test suite to ensure no regressions
- [x] 4.2 Run linting and type checking with `./scripts/lint.sh`
