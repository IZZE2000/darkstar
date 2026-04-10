## Purpose

The AURORA corrector capability has been removed. The corrector layer (stats bias + ML error model) was architecturally coupled to the base model version, causing stale corrections after every base model retrain. The base model with recency weighting now replaces the corrector's purpose.

**Note**: This spec file is kept for historical reference. All corrector functionality has been migrated to the recency-weighted base model approach.

## Requirements

*No active requirements - the AURORA corrector has been removed.*

### Migration Notes

- Base model predictions are used directly as final values
- The `final.load_kwh` and `final.pv_kwh` fields in the forecast API remain but now equal the base model output without any correction applied
- Correction columns in the DB schema are preserved but unused
- Error correction and auto-tuning toggles have been removed from the UI
